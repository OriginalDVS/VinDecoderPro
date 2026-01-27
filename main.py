import streamlit as st
import subprocess
import sys
import re
import time
import os

# --- УСТАНОВКА БРАУЗЕРОВ (ДЛЯ ОБЛАКА) ---
# Это нужно, чтобы в облаке установился Chromium
@st.cache_resource
def install_browsers():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright"])
    
    # Проверяем и устанавливаем браузер
    print("Установка браузеров Playwright...")
    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"])

install_browsers()

from playwright.sync_api import sync_playwright

# --- ФУНКЦИИ ЛОГИКИ (Те же самые, но без GUI колбэков) ---
def extract_code(text):
    if not text: return None
    match = re.search(r'([A-Z0-9]{5,20})$', text.strip())
    return match.group(1) if match else None

def find_part(page, base_url, path, node_kws, part_kws, code_prefix):
    page.goto(base_url); page.wait_for_load_state()
    for step in path:
        try:
            page.locator(f"p.catalog-node__name:has-text('{step}')").first.click()
            time.sleep(0.5)
        except: return None

    try: page.wait_for_selector('.goods__item, .node-item', timeout=5000)
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
        working_page.wait_for_selector('.goods__item', timeout=8000)
        box = working_page.locator('.box-goods')
        if box.count(): box.evaluate("el => el.scrollTop = el.scrollHeight")
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
            working_page.goto("https://www.autodoc.ru" + href)
            try:
                working_page.wait_for_selector('.properties__description-text', timeout=5000)
                desc = working_page.locator('.properties__description-text').inner_text()
                final = {'text': desc, 'code': extract_code(desc)}
            except: pass
    except: pass
    finally:
        if needs_close: working_page.close()
    return final

def run_search(vin, mode):
    status_text = st.empty() # Плейсхолдер для статуса
    results = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            status_text.info("Загрузка сайта...")
            page.goto("https://www.autodoc.ru/")
            page.get_by_role("searchbox").fill(vin)
            page.locator("button.search-button").click()
            
            try:
                page.locator('tui-icon[title="Параметры автомобиля"]').click()
                page.wait_for_selector('.dialog-car-attributes__item', timeout=10000)
            except:
                return "NOT_FOUND"

            # Определяем модель
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

            # Поиск деталей
            status_text.info(f"Двигатель {model}. Заход в каталог...")
            page.reload(); page.wait_for_load_state()
            try:
                page.locator("p.catalog-node__name:has-text('Двигатель')").first.click()
                time.sleep(1)
            except: pass
            base_url = page.url

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

# Если модель найдена, показываем инфу и кнопки
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