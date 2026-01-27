import streamlit as st
import subprocess
import sys
import re
import os

# --- УСТАНОВКА БРАУЗЕРОВ (КЭШИРУЕМ, ЧТОБЫ НЕ КАЧАТЬ КАЖДЫЙ РАЗ) ---
@st.cache_resource
def install_browsers():
    print("Проверка установки Playwright...")
    try:
        # Пробуем импортировать, если нет - ставим
        from playwright.sync_api import sync_playwright
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright"])
    
    # Установка бинарников браузера
    print("Установка Chromium...")
    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"])
    # Установка зависимостей (на всякий случай, хотя packages.txt лучше)
    subprocess.run([sys.executable, "-m", "playwright", "install-deps"])

# Запускаем установку при старте
install_browsers()

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
        
        for step in path:
            page.locator(f"p.catalog-node__name:has-text('{step}')").first.click()
            time.sleep(0.5)

        try: 
            page.wait_for_selector('.goods__item, .node-item', timeout=10000)
        except: return None

        working_page = page
        needs_close = False

        # Если списка нет - ищем узел
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
    except Exception as e:
        print(f"Ошибка в find_part: {e}")
        return None

def run_search(vin, mode):
    status_text = st.empty()
    results = []
    
    with sync_playwright() as p:
        # !!! ВАЖНОЕ ИЗМЕНЕНИЕ ДЛЯ ОБЛАКА !!!
        # Добавляем аргументы --no-sandbox и --disable-dev-shm-usage
        browser = p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--no-first-run',
                '--no-zygote',
                '--single-process',
                '--disable-gpu'
            ]
        )
        
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()
        
        try:
            status_text.info("Загрузка сайта...")
            page.goto("https://www.autodoc.ru/", timeout=60000)
            
            page.get_by_role("searchbox").fill(vin)
            page.locator("button.search-button").click()
            
            try:
                page.locator('tui-icon[title="Параметры автомобиля"]').click()
                page.wait_for_selector('.dialog-car-attributes__item', timeout=15000)
            except:
                return "NOT_FOUND"

            model = "Unknown"
            items = page.locator('.dialog-car-attributes__item').all()
            full_model_name = ""
            for item in items:
                if "Номер двигателя" in item.inner_text():
                    val = item.locator('.dialog-car-attributes__item-value').inner_text().strip()
                    full_model_name = val
                    if len(val) > 3: model = val[:4].upper()
                    break
            
            if mode == "CHECK_MODEL":
                return full_model_name, model

            status_text.info(f"Двигатель {model}. Заход в каталог...")
            
            # Обход всплывающих окон при перезагрузке
            page.reload()
            page.wait_for_load_state()
            try:
                page.locator("p.catalog-node__name:has-text('Двигатель')").first.click()
                time.sleep(1)
            except: pass
            base_url = page.url

            import time # Импорт внутри для надежности
            
            if mode == "G4NA":
                status_text.info("Поиск: Впускной распредвал...")
                res = find_part(page, base_url, ["Механизм газораспределения", "Распредвал", "Шестерня распредвала"], ['any'], ['распредвал', 'впуск'], None)
                results.append(("Распредвал Впуск", res))
                
                status_text.info("Поиск: Выпускной распредвал...")
                res = find_part(page, base_url, ["Механизм газораспределения", "Распредвал", "Шестерня распредвала"], ['any'], ['распредвал', 'выпуск'], None)
                results.append(("Распредвал Выпуск", res))

            elif mode == "G4KE":
                status_text.info("Поиск: Лобная крышка...")
                res = find_part(page, base_url, ["Блок-картер", "Блок-картер"], ["крышка", "ременного"], None, "21350")
                results.append(("Лобная крышка", res))

                status_text.info("Поиск: Кронштейн...")
                res = find_part(page, base_url, ["Крепление двигателя", "Кронштейн двигателя"], ["подвеска", "двигателя"], None, "21670")
                results.append(("Кронштейн", res))

            status_text.success("Готово!")
            return results

        finally:
            browser.close()

# --- ИНТЕРФЕЙС STREAMLIT ---
st.set_page_config(page_title="VIN Decoder", page_icon="🚗")

st.title("🚗 Поиск запчастей по VIN")
st.markdown("Hyundai / Kia Engine Decoder")

if 'model_name' not in st.session_state:
    st.session_state['model_name'] = None
    st.session_state['engine_code'] = None

vin = st.text_input("Введите VIN код (17 символов):", max_chars=17).upper().strip()

if st.button("🔍 Найти автомобиль", type="primary"):
    if len(vin) == 17:
        with st.spinner('Подключаюсь к базе...'):
            res = run_search(vin, "CHECK_MODEL")
            if res == "NOT_FOUND":
                st.error("Автомобиль не найден")
            else:
                st.session_state['model_name'] = res[0]
                st.session_state['engine_code'] = res[1]
    else:
        st.warning("VIN должен быть 17 символов")

if st.session_state['model_name']:
    st.success(f"Автомобиль найден: **{st.session_state['model_name']}**")
    
    eng = st.session_state['engine_code']
    
    if "G4NA" in eng:
        if st.button("🔧 НАЙТИ РАСПРЕДВАЛЫ (G4NA)"):
            with st.spinner('Сканирование каталогов...'):
                data = run_search(vin, "G4NA")
                for title, item in data:
                    with st.expander(title, expanded=True):
                        if item:
                            st.write(item['text'])
                            st.code(item['code'], language="text")
                        else:
                            st.error("Не найдено")

    elif "G4KE" in eng:
        if st.button("🛠️ НАЙТИ КРЕПЛЕНИЕ (G4KE)"):
            with st.spinner('Сканирование каталогов...'):
                data = run_search(vin, "G4KE")
                for title, item in data:
                    with st.expander(title, expanded=True):
                        if item:
                            st.write(item['text'])
                            st.code(item['code'], language="text")
                        else:
                            st.error("Не найдено")
    else:
        st.info("Для этого двигателя пока нет сценария авто-поиска деталей.")