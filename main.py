import streamlit as st
import subprocess
import sys
import re
import time
import os
import streamlit.components.v1 as components

# --- УСТАНОВКА ЗАВИСИМОСТЕЙ ---
@st.cache_resource
def install_system_dependencies():
    # Проверяем наличие playwright, если нет - ставим
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright"])
    
    # Установка браузеров (делаем тихо, чтобы не засорять логи)
    try:
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=False)
        subprocess.run([sys.executable, "-m", "playwright", "install-deps"], check=False)
    except:
        pass

install_system_dependencies()

from playwright.sync_api import sync_playwright

# --- ФУНКЦИИ ЛОГИКИ ---
def extract_code(text):
    if not text: return None
    match = re.search(r'([A-Z0-9]{5,20})$', text.strip())
    return match.group(1) if match else None

def find_part(page, base_url, path, node_kws, part_kws, code_prefix):
    try:
        page.goto(base_url, timeout=60000)
        page.wait_for_load_state()
    except: return None

    for step in path:
        try:
            page.locator(f"p.catalog-node__name:has-text('{step}')").first.click()
            time.sleep(0.5)
        except: return None

    try: page.wait_for_selector('.goods__item, .node-item', timeout=8000)
    except: return None

    working_page = page
    needs_close = False

    if page.locator('.goods__item').count() == 0:
        nodes = page.locator('.node-item').all()
        target = None
        for n in nodes:
            if all(k in n.inner_text().lower() for k in node_kws):
                target = n; break
        if not target and 'any' in node_kws and nodes: target = nodes[0]

        if target:
            with page.context.expect_page() as new_p:
                target.locator("a:has-text('Показать все')").first.click()
            working_page = new_p.value
            working_page.wait_for_load_state()
            needs_close = True
        else: return None

    final = None
    try:
        working_page.wait_for_selector('.goods__item', timeout=15000)
        box = working_page.locator('.box-goods')
        if box.count(): 
            box.evaluate("el => el.scrollTop = el.scrollHeight")
            time.sleep(0.5)

        goods = working_page.locator('.goods__item').all()
        href = None
        for g in goods:
            txt = g.inner_text().lower()
            if part_kws and all(w in txt for w in part_kws):
                href = g.locator('a.goods__item-link').get_attribute('href'); break
            if code_prefix and code_prefix in txt:
                href = g.locator('a.goods__item-link').get_attribute('href'); break
        
        if href:
            working_page.goto("https://www.autodoc.ru" + href, timeout=60000)
            try:
                working_page.wait_for_selector('.properties__description-text', timeout=10000)
                desc = working_page.locator('.properties__description-text').inner_text()
                final = {'text': desc, 'code': extract_code(desc)}
            except: pass
    except: pass
    finally:
        if needs_close: working_page.close()
    
    return final

def run_search(vin, mode):
    status_box = st.empty()
    results = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu']
        )
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()
        
        try:
            status_box.info("Вход на сайт...")
            page.goto("https://www.autodoc.ru/", timeout=60000)
            page.get_by_role("searchbox").fill(vin)
            page.locator("button.search-button").click()
            
            # --- РЕЖИМ ПРОВЕРКИ АВТО ---
            if mode == "CHECK":
                data = {'car_name': 'Неизвестно', 'model_code': '', 'date': '-', 'engine': None, 'drive': '-'}
                
                try:
                    page.wait_for_selector("h1.catalog-originals-heading", timeout=10000)
                    raw_title = page.locator("h1.catalog-originals-heading").inner_text()
                    clean_title = raw_title.replace("Запчасти для", "").strip()
                    parts = clean_title.split()
                    if len(parts) > 1:
                        data['car_name'] = " ".join(parts[:-1])
                    else:
                        data['car_name'] = clean_title
                except: pass

                try:
                    page.locator('tui-icon[title="Параметры автомобиля"]').click()
                    page.wait_for_selector('.dialog-car-attributes__item', timeout=15000)
                    items = page.locator('.dialog-car-attributes__item').all()

                    for item in items:
                        name = item.locator('.dialog-car-attributes__item-name').inner_text()
                        val = item.locator('.dialog-car-attributes__item-value').inner_text().strip()

                        if "Номер двигателя" in name:
                            if len(val) > 3: data['engine'] = val[:4].upper()
                        elif "Дата выпуска" in name:
                            data['date'] = val
                        elif "Модель:" in name or ("Модель" in name and "год" not in name):
                            data['model_code'] = val
                        elif "Опции" in name:
                            try:
                                item.scroll_into_view_if_needed()
                                show_more = item.locator('.dialog-car-attributes__item_show-more')
                                if show_more.count() > 0 and show_more.is_visible():
                                    show_more.click()
                                    time.sleep(0.5)
                            except: pass
                            
                            opt_text = item.locator('.dialog-car-attributes__item-value').inner_text().upper()
                            if "4WD" in opt_text: data['drive'] = "4WD (Полный)"
                            elif "2WD" in opt_text: data['drive'] = "2WD (Передний)"
                except:
                    return "NOT_FOUND"

                status_box.empty()
                return data

            # --- РЕЖИМ ПОИСКА ЗАПЧАСТЕЙ ---
            status_box.info(f"Заход в каталог двигателя...")
            
            try:
                page.locator('tui-icon[title="Параметры автомобиля"]').click()
                page.wait_for_selector('.dialog-car-attributes__item')
            except: pass

            page.reload(); page.wait_for_load_state()
            try:
                page.locator("p.catalog-node__name:has-text('Двигатель')").first.click()
                time.sleep(1)
            except: pass
            base_url = page.url

            if mode == "G4NA":
                status_box.info("Ищу Впускной распредвал...")
                res = find_part(page, base_url, 
                    ["Механизм газораспределения", "Распредвал", "Шестерня распредвала"],
                    ['any'], ['распредвал', 'впуск'], None)
                results.append(("Распредвал Впуск", res))

                status_box.info("Ищу Выпускной распредвал...")
                res = find_part(page, base_url, 
                    ["Механизм газораспределения", "Распредвал", "Шестерня распредвала"],
                    ['any'], ['распредвал', 'выпуск'], None)
                results.append(("Распредвал Выпуск", res))

            elif mode == "G4KE":
                status_box.info("Ищу Лобную крышку...")
                res = find_part(page, base_url,
                    ["Блок-картер", "Блок-картер"], 
                    ["крышка", "ременного"], None, "21350")
                results.append(("Лобная крышка", res))

                status_box.info("Ищу Кронштейн...")
                res = find_part(page, base_url,
                    ["Крепление двигателя", "Кронштейн двигателя"], 
                    ["подвеска", "двигателя"], None, "21670")
                results.append(("Кронштейн", res))

            status_box.empty()
            return results

        finally:
            browser.close()

# --- ИНТЕРФЕЙС STREAMLIT ---
st.set_page_config(page_title="VIN Decoder", page_icon="⚙️", layout="wide")

st.title("VIN DECODER ULTIMATE")

if 'car_data' not in st.session_state:
    st.session_state['car_data'] = None

# --- КОМПОНЕНТ КНОПКИ ВСТАВКИ (JS) ---
# Этот скрипт создает HTML-кнопку, которая имеет доступ к буферу браузера
# и насильно вставляет текст в поле ввода Streamlit.
paste_component = """
<div style="display: flex; align-items: flex-end; height: 100%;">
    <button id="paste-btn" style="
        background-color: #FF4B4B; 
        color: white; 
        border: none; 
        padding: 0.5rem 1rem; 
        border-radius: 0.5rem; 
        cursor: pointer; 
        font-weight: bold;
        width: 100%;
        font-family: 'Source Sans Pro', sans-serif;">
        📋 Вставить из буфера
    </button>
</div>

<script>
    const btn = document.getElementById('paste-btn');
    btn.addEventListener('click', async () => {
        try {
            // Читаем текст из буфера обмена браузера
            const text = await navigator.clipboard.readText();
            
            // Находим поле ввода Streamlit (обычно это input type="text")
            const inputFrame = window.parent.document;
            const inputs = inputFrame.querySelectorAll('input[type="text"]');
            
            // Берем первое найденное поле (поле VIN)
            if (inputs.length > 0) {
                const input = inputs[0];
                
                // Устанавливаем значение
                // Оставляем только буквы и цифры
                const cleanText = text.replace(/[^a-zA-Z0-9]/g, '').toUpperCase().substring(0, 17);
                
                // Эмулируем ввод пользователя, чтобы React (Streamlit) увидел изменения
                const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
                nativeInputValueSetter.call(input, cleanText);
                
                input.dispatchEvent(new Event('input', { bubbles: true }));
                input.dispatchEvent(new Event('change', { bubbles: true }));
                input.focus();
            } else {
                console.error("Поле ввода не найдено");
            }
        } catch (err) {
            console.error('Ошибка чтения буфера:', err);
            alert('Пожалуйста, разрешите доступ к буферу обмена или используйте HTTPS.');
        }
    });
</script>
"""

# Разметка колонок: Поле ввода (широкое) и Кнопка (узкая)
col1, col2 = st.columns([4, 1], vertical_alignment="bottom")

with col1:
    vin = st.text_input("Введите VIN код:", max_chars=17, key="vin_field").upper().strip()

with col2:
    # Вставляем нашу JS-кнопку. Height=42 подгоняет высоту под поле ввода
    components.html(paste_component, height=42)

# Кнопка запуска поиска
if st.button("🔍 ПОЛУЧИТЬ ДАННЫЕ", type="primary", use_container_width=True):
    if len(vin) == 17:
        st.session_state['car_data'] = None 
        with st.spinner('Сбор информации об автомобиле...'):
            res = run_search(vin, "CHECK")
            if res == "NOT_FOUND":
                st.error("Автомобиль не найден или ошибка доступа")
            else:
                st.session_state['car_data'] = res
    else:
        st.warning("VIN должен содержать 17 символов")

# ОТОБРАЖЕНИЕ РЕЗУЛЬТАТОВ
if st.session_state['car_data']:
    data = st.session_state['car_data']
    
    st.header(data.get('car_name', 'Неизвестно'))
    
    if data.get('model_code'):
        st.caption(f"Код модели: {data['model_code']}")
    
    st.divider()

    col_info1, col_info2, col_info3 = st.columns(3)
    with col_info1:
        st.markdown(f"**📅 Дата выпуска:**\n{data.get('date', '-')}")
    with col_info2:
        st.markdown(f"**⚙️ Привод:**\n{data.get('drive', '-')}")
    with col_info3:
        st.markdown(f"**🚀 Двигатель:**\n{data.get('engine', '---')}")
    
    st.divider()

    engine = data.get('engine', '')
    
    if engine and "G4NA" in engine:
        if st.button("🔧 НАЙТИ РАСПРЕДВАЛЫ (G4NA)", type="primary", use_container_width=True):
            with st.spinner('Поиск деталей в каталоге...'):
                parts = run_search(vin, "G4NA")
                for title, item in parts:
                    with st.expander(title, expanded=True):
                        if item:
                            st.write(item['text'])
                            st.code(item['code'], language="text")
                        else:
                            st.error("Не найдено")

    elif engine and "G4KE" in engine:
        if st.button("🛠️ НАЙТИ КРЕПЛЕНИЕ (G4KE)", type="primary", use_container_width=True):
            with st.spinner('Поиск деталей в каталоге...'):
                parts = run_search(vin, "G4KE")
                for title, item in parts:
                    with st.expander(title, expanded=True):
                        if item:
                            st.write(item['text'])
                            st.code(item['code'], language="text")
                        else:
                            st.error("Не найдено")
    elif engine:
        st.info("Для этого двигателя нет автоматического поиска запчастей.")
