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
    packages = ["playwright", "pyperclip"]
    for package in packages:
        try:
            __import__(package)
        except ImportError:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
    
    # Установка браузеров для Playwright
    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"])
    subprocess.run([sys.executable, "-m", "playwright", "install-deps"])

install_system_dependencies()

from playwright.sync_api import sync_playwright
import pyperclip

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

# --- JS СКРИПТ ДЛЯ ГОРЯЧИХ КЛАВИШ (RU/EN) ---
# Этот скрипт слушает нажатие Ctrl+V (код клавиши KeyV) глобально
# Если нажато - он находит поле ввода и ставит на него фокус
hotkey_script = """
<script>
const doc = window.parent.document;
doc.addEventListener('keydown', function(e) {
    // Проверяем нажатие Ctrl (или Cmd на Mac) + клавиша V (физическая, работает и для 'М' на русс)
    if ((e.ctrlKey || e.metaKey) && e.code === 'KeyV') {
        const input = doc.querySelector('input[type="text"]');
        if (input && input !== doc.activeElement) {
            input.focus();
            // Мы не делаем preventDefault, чтобы браузер выполнил вставку
        }
    }
});
</script>
"""
components.html(hotkey_script, height=0, width=0)

st.title("VIN DECODER ULTIMATE")

# Инициализация State
if 'car_data' not in st.session_state:
    st.session_state['car_data'] = None
if 'vin_input' not in st.session_state:
    st.session_state['vin_input'] = ""

# Функция вставки из буфера
def paste_vin_from_clipboard():
    try:
        text = pyperclip.paste()
        # Очистка: оставляем только буквы и цифры, в верхний регистр
        clean_text = re.sub(r'[^a-zA-Z0-9]', '', text).upper()
        if clean_text:
            st.session_state.vin_input = clean_text[:17]
        else:
            st.warning("Буфер обмена пуст или не содержит текста")
    except Exception as e:
        st.error(f"Ошибка доступа к буферу обмена: {e}")

# --- БЛОК ВВОДА ---
# Создаем колонки: широкая для ввода, узкая для кнопки вставки
col_input, col_paste = st.columns([5, 1], vertical_alignment="bottom")

with col_input:
    vin = st.text_input(
        "Введите VIN код:", 
        max_chars=17, 
        key="vin_input",
        help="Поддерживает вставку по Ctrl+V (En/Ru)"
    ).upper().strip()

with col_paste:
    st.button("📋 Вставить", on_click=paste_vin_from_clipboard, use_container_width=True)

# Кнопка запуска
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
    
    # 1. Заголовок
    st.header(data.get('car_name', 'Неизвестно'))
    
    # 2. Код модели
    if data.get('model_code'):
        st.caption(f"Код модели: {data['model_code']}")
    
    st.divider()

    # 3. ХАРАКТЕРИСТИКИ
    col_info1, col_info2, col_info3 = st.columns(3)
    with col_info1:
        st.markdown(f"**📅 Дата выпуска:**\n{data.get('date', '-')}")
    with col_info2:
        st.markdown(f"**⚙️ Привод:**\n{data.get('drive', '-')}")
    with col_info3:
        st.markdown(f"**🚀 Двигатель:**\n{data.get('engine', '---')}")
    
    st.divider()

    # 4. КНОПКИ ПОИСКА
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
