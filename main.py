import sys
import re
import time
import os
import random
import urllib.parse
import concurrent.futures
import streamlit as st

# === АВТОМАТИЧЕСКАЯ УСТАНОВКА БРАУЗЕРА ДЛЯ СЕРВЕРА ===
@st.cache_resource
def install_playwright():
    # Эта команда скачивает сам браузер Chromium внутри сервера
    os.system("playwright install chromium")
    os.system("playwright install-deps chromium")

install_playwright()
from playwright.sync_api import sync_playwright

# --- КОНФИГУРАЦИЯ ---
st.set_page_config(page_title="VIN Decoder Ultimate", layout="wide")

# ПРОКСИ (4 слота: Autodoc, Exist/Elcats, Armtek, Part-kom)
PROXY_LIST = [None, None, None, None]

# Определение платформы (для скрытия браузера на серверах Linux)
IS_SERVER = sys.platform.startswith('linux')

st.markdown("""
<style>
.car-card { border: 1px solid #dcdde1; border-radius: 8px; padding: 15px; background-color: #ffffff; box-shadow: 0 4px 6px rgba(0,0,0,0.05); height: 100%;}
.car-title { text-align: center; font-weight: 900; font-size: 16px; margin-bottom: 15px; padding: 5px; border-radius: 4px; }
.car-name { font-weight: bold; text-align: center; font-size: 18px; margin-bottom: 5px; }
.car-model { color: #7f8c8d; text-align: center; font-size: 14px; font-family: monospace; margin-bottom: 10px; }
.car-param { font-size: 14px; color: #7f8c8d; }
.car-val { font-size: 14px; color: #2c3e50; font-weight: bold; }
.engine-box { border: 2px solid; border-radius: 5px; padding: 10px; text-align: center; margin-top: 15px; }
.eng-label { font-size: 11px; font-weight: bold; margin-bottom: 3px; }
.eng-val { font-size: 24px; font-weight: bold; font-family: monospace; }
.part-card { border: 1px solid; border-radius: 8px; padding: 15px; margin-bottom: 10px; background-color: #ffffff;}
.part-title { font-weight: bold; font-size: 14px; color: #2c3e50; margin-bottom: 10px; }
.part-code { padding: 8px; border-radius: 4px; text-align: center; font-family: monospace; font-size: 18px; font-weight: bold; margin-bottom: 8px;}
.part-desc { font-size: 12px; color: #7f8c8d; line-height: 1.4;}
</style>
""", unsafe_allow_html=True)

# =====================================================================
# === ДВИЖОК БРАУЗЕРА ===
# =====================================================================
def create_stealth_browser_and_page(playwright_instance, proxy_url=None):
    args =[
        '--disable-blink-features=AutomationControlled',
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu'
    ]
    
    # На сервере СТРОГО headless=True
    launch_options = {
        'headless': True if IS_SERVER else False,
        'args': args,
        'ignore_default_args': ["--enable-automation"]
    }
    if proxy_url: launch_options['proxy'] = {"server": proxy_url}
    
    try: browser = playwright_instance.chromium.launch(channel="chrome", **launch_options)
    except: browser = playwright_instance.chromium.launch(**launch_options)
    
    context = browser.new_context(
        locale="ru-RU", timezone_id="Europe/Moscow", 
        viewport={'width': 1920, 'height': 1080},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    page = context.new_page()
    page.add_init_script("delete Object.getPrototypeOf(navigator).webdriver; window.chrome = { runtime: {} };")
    return browser, page

# =====================================================================
# === 1. ПАРСЕРЫ АВТОМОБИЛЕЙ ===
# =====================================================================
def get_autodoc_details(vin, proxy_url):
    data = {'car_name': None, 'model_code': None, 'date': None, 'engine': None, 'drive': None, 'error': False}
    with sync_playwright() as p:
        browser, page = create_stealth_browser_and_page(p, proxy_url)
        try:
            page.goto("https://www.autodoc.ru/")
            page.get_by_role("searchbox").fill(vin)
            page.locator("button.search-button").click()
            try:
                page.wait_for_selector("h1.catalog-originals-heading", timeout=10000)
                raw_title = page.locator("h1.catalog-originals-heading").inner_text()
                clean_title = raw_title.replace("Запчасти для", "").strip()
                parts = clean_title.split()
                data['car_name'] = " ".join(parts[:-1]) if len(parts) > 1 else clean_title
            except: 
                data['error'] = True; return data

            page.locator('tui-icon[title="Параметры автомобиля"]').click()
            page.wait_for_selector('.dialog-car-attributes__item', timeout=10000)
            
            for item in page.locator('.dialog-car-attributes__item').all():
                name = item.locator('.dialog-car-attributes__item-name').inner_text()
                val = item.locator('.dialog-car-attributes__item-value').inner_text().strip()
                if "Номер двигателя" in name: data['engine'] = val[:4].upper()
                elif "Дата выпуска" in name: data['date'] = val
                elif "Модель:" in name or ("Модель" in name and "год" not in name): data['model_code'] = val
                elif "Опции" in name:
                    try:
                        item.scroll_into_view_if_needed()
                        btn = item.locator('.dialog-car-attributes__item_show-more')
                        if btn.count() and btn.is_visible(): btn.click(); time.sleep(0.5)
                    except: pass
                    opt = item.locator('.dialog-car-attributes__item-value').inner_text().upper()
                    if "4WD" in opt: data['drive'] = "4WD (Полный)"
                    elif "2WD" in opt: data['drive'] = "2WD (Передний)"
        except: data['error'] = True
        finally: browser.close()
    return data

def get_exist_details(vin, proxy_url):
    data = {'car_name': None, 'model_code': None, 'date': None, 'engine': None, 'drive': None, 'error': False}
    with sync_playwright() as p:
        browser, page = create_stealth_browser_and_page(p, proxy_url)
        try:
            page.goto(f"https://exist.ru/Price/Empty.aspx?q={vin}", timeout=60000)
            page.wait_for_selector('.car-info', timeout=20000)
            data['car_name'] = page.locator('.car-info__car-name').first.text_content().strip()
            data['date'] = page.locator('.car-info__car-years').first.text_content().strip()
            
            nu = data['car_name'].upper()
            if "4WD" in nu or "AWD" in nu: data['drive'] = "4WD (Полный)"
            elif "2WD" in nu: data['drive'] = "2WD (Передний)"
            
            m = re.search(r'\(([A-Z0-9]{4,5})\)', data['car_name'])
            if m: data['engine'] = m.group(1)
            
            if not data['drive']:
                txt = page.locator('.car-info').first.text_content()
                md = re.search(r'Transaxle:\s*([A-Z0-9\s-]+?)(?:\s*\||$)', txt)
                if md:
                    d = md.group(1).strip()
                    if "2WD" in d: data['drive'] = "2WD (Передний)"
                    elif "4WD" in d: data['drive'] = "4WD (Полный)"
                    else: data['drive'] = d
        except: data['error'] = True
        finally: browser.close()
    return data

def get_armtek_details(vin, proxy_url):
    data = {'car_name': None, 'model_code': None, 'date': None, 'engine': None, 'drive': None, 'error': False}
    with sync_playwright() as p:
        browser, page = create_stealth_browser_and_page(p, proxy_url)
        try:
            page.goto(f"https://armtek.ru/search?text={vin}", timeout=60000)
            time.sleep(3); page.keyboard.press("Escape")
            page.wait_for_selector("div.car__header", timeout=15000)
            try:
                h = page.locator("mat-expansion-panel-header").first
                if h.is_visible() and "mat-expanded" not in h.get_attribute("class"):
                    h.click(); time.sleep(1)
            except: pass
            
            for item in page.locator("div.car__main-information-item").all():
                t = item.locator("p.car__main-information-item-title").text_content().strip()
                v = item.locator("p.font__body2").text_content().strip()
                if "Модель" in t and "год" not in t: data['model_code'] = v
                elif "Дата выпуска" in t: data['date'] = v
                elif "Номер двигателя" in t: data['engine'] = v[:4].upper()
                elif "Опции" in t:
                    if "4WD" in v: data['drive'] = "4WD (Полный)"
                    elif "2WD" in v: data['drive'] = "2WD (Передний)"
            
            tel = page.locator("div.car__header-info-title p").first
            if tel.is_visible(): data['car_name'] = tel.text_content().strip()
        except: data['error'] = True
        finally: browser.close()
    return data

def get_partkom_details(vin, proxy_url):
    data = {'car_name': None, 'model_code': None, 'date': None, 'engine': None, 'drive': None, 'error': False}
    with sync_playwright() as p:
        browser, page = create_stealth_browser_and_page(p, proxy_url)
        try:
            page.goto(f"https://part-kom.ru/catalog-vin?vin={vin}", timeout=60000)
            iframe_obj = None
            found = False
            for _ in range(150):
                try: page.evaluate("() => { document.querySelectorAll('button').forEach(b => { if(b.innerText.includes('Да, верно') || b.ariaLabel=='закрыть') b.click(); }) }")
                except: pass
                
                if not iframe_obj:
                     el = page.locator('iframe[src*="b2b.part-kom.ru"]').first
                     if el.count(): iframe_obj = el.content_frame

                if iframe_obj:
                    try:
                        b_exp = iframe_obj.locator("button:has-text('Все параметры')").first
                        if b_exp.is_visible(): b_exp.click(); time.sleep(0.5)

                        params = iframe_obj.locator('div[class*="grouped-cars-list-group__parameter"], li[class*="cars-list-item-mobile__parameter"]').all()
                        if params:
                            tel = iframe_obj.locator('div[class*="grouped-cars-list-group__title"], div[class*="cars-list-item-mobile__brand"]').first
                            if tel.count(): data['car_name'] = tel.text_content().strip()

                            for p_item in params:
                                divs = p_item.locator("div").all()
                                if len(divs) >= 2:
                                    k, v = divs[0].text_content().strip(), divs[1].text_content().strip()
                                    if "Год" in k: data['date'] = v
                                    elif "Код двигателя" in k: data['engine'] = v[:4].upper() if len(v)>4 else v
                                    elif "Transaxle" in k:
                                        if "4WD" in v: data['drive'] = "4WD (Полный)"
                                        elif "2WD" in v: data['drive'] = "2WD (Передний)"
                            found = True; break
                    except: pass
                time.sleep(0.1)
            if not found: data['error'] = True
        except: data['error'] = True
        finally: browser.close()
    return data


# =====================================================================
# === 2. ПАРСЕРЫ ЗАПЧАСТЕЙ ===
# =====================================================================
def run_autodoc_part(vin, node_path, node_kws, part_kws, code_prefix, title):
    time.sleep(random.uniform(0.1, 0.5))
    items =[]
    with sync_playwright() as p:
        browser, page = create_stealth_browser_and_page(p, PROXY_LIST[0])
        try:
            page.goto("https://www.autodoc.ru/")
            page.get_by_role("searchbox").fill(vin)
            page.locator("button.search-button").click()
            try: page.locator('tui-icon[title="Параметры автомобиля"]').click(); page.wait_for_selector('.dialog-car-attributes__item', timeout=5000)
            except: pass
            page.reload(); page.wait_for_load_state()
            try: page.locator("p.catalog-node__name:has-text('Двигатель')").first.click(); time.sleep(1)
            except: pass
            
            for step in node_path:
                try: page.locator(f"p.catalog-node__name:has-text('{step}')").first.click(); time.sleep(0.5)
                except: break
            try: page.wait_for_selector('.goods__item, .node-item', timeout=5000)
            except: pass
            
            working_page = page
            if page.locator('.goods__item').count() == 0:
                nodes = page.locator('.node-item').all()
                target = next((n for n in nodes if all(k in n.inner_text().lower() for k in node_kws)), None)
                if not target and 'any' in node_kws and nodes: target = nodes[0]
                if target:
                    with page.context.expect_page() as new_p: target.locator("a:has-text('Показать все')").first.click()
                    working_page = new_p.value
                    working_page.wait_for_load_state()
            
            try:
                working_page.wait_for_selector('.goods__item', timeout=8000)
                if working_page.locator('.box-goods').count(): working_page.evaluate("el => el.scrollTop = el.scrollHeight"); time.sleep(0.5)
                for g in working_page.locator('.goods__item').all():
                    txt = g.inner_text().lower()
                    if (part_kws and all(w in txt for w in part_kws)) or (code_prefix and code_prefix in txt):
                        href = g.locator('a.goods__item-link').get_attribute('href')
                        working_page.goto("https://www.autodoc.ru" + href)
                        working_page.wait_for_selector('.properties__description-text', timeout=5000)
                        desc = working_page.locator('.properties__description-text').inner_text()
                        m = re.search(r'([A-Z0-9]{5,20})$', desc.strip())
                        code = m.group(1) if m else None
                        items.append({'source': 'AUTODOC', 'title': title, 'desc': desc, 'code': code})
                        break
            except: pass
        except: pass
        finally: browser.close()
    if not items: items.append({'source': 'AUTODOC', 'title': title, 'desc': 'Не найдено', 'code': None})
    return items

def run_elcats_part(vin, mode, title):
    time.sleep(random.uniform(0.3, 0.8))
    items =[]
    if mode == 'G4NA_intake': group_kw = 'РАСПРЕДЕЛИТЕЛЬНЫЙ ВАЛ И КЛАПАН'; node_descr = 'РАСПРЕДВАЛ В СБОРЕ-ВПУСКНОЙ'
    elif mode == 'G4NA_exhaust': group_kw = 'РАСПРЕДЕЛИТЕЛЬНЫЙ ВАЛ И КЛАПАН'; node_descr = 'РАСПРЕДЕЛИТЕЛЬНЫЙ ВАЛ В СБОРЕ-ВЫХЛОПНОЙ'
    elif mode == 'G4KE_cover': group_kw = 'КРЫШКА РЕМНЯ И МАСЛЯНЫЙ ПОДДОН'; node_descr = 'КРЫШКА В СБОРЕ-ПРИВОДНАЯ ЦЕПЬ'
    elif mode == 'G4KE_bracket': group_kw = 'КРЕПЛЕНИЯ ДВИГАТЕЛЯ И ТРАНСМИССИИ'; node_descr = 'КРОНШТЕЙН В СБОРЕ-ОПОРА ДВИГАТЕЛЯ'
    else: return[]

    with sync_playwright() as p:
        browser, page = create_stealth_browser_and_page(p, PROXY_LIST[1])
        try:
            page.goto(f"https://www.elcats.ru/hyundai/default.aspx?carvin={vin}", timeout=60000, referer="https://www.exist.ru/", wait_until="domcontentloaded")
            time.sleep(2)
            if "default.aspx" in page.url.lower():
                try: page.locator('#ctl00_cphMasterPage_txbVIN').fill(vin)
                except: page.locator('input[type=text]').first.fill(vin)
                time.sleep(0.3)
                page.locator('#ctl00_cphMasterPage_btnFindByVIN').click()
                time.sleep(3)

            m = re.search(r'Model=([a-f0-9\-]{36})', page.url, re.I)
            if m:
                model_uuid = m.group(1)
                group_id = page.evaluate("""(hint) => {
                        var links = document.querySelectorAll('a[href^="javascript:submit"]');
                        for (var i = 0; i < links.length; i++) {
                            if (links[i].textContent.toUpperCase().indexOf(hint.toUpperCase()) !== -1) {
                                var match = links[i].getAttribute('href').match(/submit[(]'([^']+)'/);
                                if (match) return match[1];
                            }
                        } return null;
                    }""", group_kw)

                if group_id:
                    page.goto(f"https://www.elcats.ru/hyundai/Unit.aspx?GroupId={group_id}&Model={model_uuid}&Title={urllib.parse.quote(group_kw)}", wait_until="domcontentloaded")
                    time.sleep(2)
                    cnode_ids = page.evaluate(f"""(descr) => {{
                        var nodes = document.querySelectorAll('div.CNode');
                        var res =[];
                        nodes.forEach(n => {{
                            var s = n.querySelector('span.descr-ru');
                            if(s && s.textContent.toUpperCase().indexOf(descr.toUpperCase()) !== -1) res.push(n.getAttribute('id'));
                        }}); return res;
                    }}""", node_descr)

                    seen = set()
                    for cid in cnode_ids:
                        try:
                            page.locator(f"xpath=//div[@id='{cid}']").click()
                            time.sleep(4)
                            parts = page.evaluate("""() => {
                                var res =[];
                                document.querySelectorAll('table.OpelParts tr').forEach((row, i) => {
                                    if(i===0) return;
                                    var tds = row.querySelectorAll('td');
                                    if(tds.length < 2) return;
                                    var a = tds[0].querySelector('a');
                                    var code = (a ? a.textContent : tds[0].textContent).replace(/\\s+/g, ' ').trim();
                                    var span = tds[1].querySelector('span.descr-ru');
                                    var descr = (span ? span.textContent : tds[1].textContent).replace(/\\s+/g, ' ').trim();
                                    var period = tds.length > 3 ? tds[3].textContent.replace(/\\s+/g, ' ').trim() : "";
                                    var info = tds.length > 4 ? tds[4].textContent.replace(/\\s+/g, ' ').trim() : "";
                                    if(code.length > 3) res.push({code: code, descr: descr, period: period, info: info});
                                }); return res;
                            }""")
                            for pt in parts:
                                if pt['code'] not in seen:
                                    seen.add(pt['code'])
                                    fdesc = pt['descr']
                                    if pt['period']: fdesc += f"[{pt['period']}]"
                                    if pt['info']: fdesc += f" ({pt['info']})"
                                    items.append({'source': 'ELCATS', 'title': title, 'desc': fdesc, 'code': pt['code']})
                        except: pass
        except: pass
        finally: browser.close()
    if not items: items.append({'source': 'ELCATS', 'title': title, 'desc': 'Артикулы не найдены', 'code': None})
    return items

def run_armtek_part(vin, mode, title):
    time.sleep(random.uniform(0.5, 1.2))
    items =[]
    CFG = {
        'G4NA_intake':  {'q': 'распредвал впускной', 'kw': 'впускной', 'ignore':[]},
        'G4NA_exhaust': {'q': 'распредвал выпускной', 'kw': 'выпускной', 'ignore':[]},
        'G4KE_cover':   {'q': 'КОЖУХ В СБОРЕ-ЦЕПЬ ГРМ', 'kw': 'кожух', 'ignore':[]},
        'G4KE_bracket': {'q': 'кронштейн двигателя', 'kw': 'кронштейн', 'ignore':['двигатель уст', 'опора']},
    }
    conf = CFG.get(mode)
    if not conf: return[]

    with sync_playwright() as p:
        browser, page = create_stealth_browser_and_page(p, PROXY_LIST[2])
        try:
            page.goto(f"https://armtek.ru/search?text={vin}", wait_until="domcontentloaded")
            page.wait_for_selector("div.car__header", timeout=20000)
            try: page.keyboard.press("Escape")
            except: pass
            
            inp = page.locator('input[placeholder="Наименование запчасти"]').first
            inp.wait_for(state="visible", timeout=15000)
            inp.click(click_count=3)
            page.keyboard.press("Backspace")
            time.sleep(0.5)
            
            try: inp.press_sequentially(conf['q'], delay=30)
            except: inp.type(conf['q'], delay=30)
            time.sleep(0.5)
            page.keyboard.press("Enter")
            
            time.sleep(2)
            page.wait_for_selector("div.part", timeout=10000)

            parts = page.evaluate(f"""(kw) => {{
                var res =[]; var seen = {{}};
                document.querySelectorAll('div.part').forEach(p => {{
                    var nm = p.querySelector('div.title-name');
                    var oem = p.querySelector('div.oem');
                    if (!nm || !oem) return;
                    var name = nm.textContent.trim(); var code = oem.textContent.trim();
                    if (code.length < 4 || seen[code]) return;
                    seen[code] = true;
                    res.push({{name: name, code: code, match: name.toLowerCase().includes(kw.toLowerCase())}});
                }}); return res;
            }}""", conf['kw'])

            for pt in parts:
                if any(ign.lower() in pt['name'].lower() for ign in conf['ignore']): continue
                if pt['match']:
                    items.append({'source': 'ARMTEK', 'title': title, 'desc': pt['name'], 'code': pt['code']})
            
            if not items and parts: 
                 for pt in parts:
                     if any(ign.lower() in pt['name'].lower() for ign in conf['ignore']): continue
                     items.append({'source': 'ARMTEK', 'title': title, 'desc': pt['name'], 'code': pt['code']})
                     break
        except: pass
        finally: browser.close()
    if not items: items.append({'source': 'ARMTEK', 'title': title, 'desc': 'Не найдено', 'code': None})
    return items

# =====================================================================
# === STREAMLIT FRONTEND ===
# =====================================================================

st.title("VIN DECODER PRO 🌐")
st.info("💡 **Как вставить VIN:** Кликните мышкой в поле ниже и нажмите **Ctrl+V** на клавиатуре.")

vin_raw = st.text_input("Введите 17-значный VIN код:", max_chars=17)

# Очищаем VIN
vin = re.sub(r'[^A-Z0-9]', '', vin_raw.upper())

if vin_raw:
    if len(vin) == 17:
        st.caption(f"✅ Введено символов: 17 / 17")
    else:
        st.error(f"❌ Ошибка длины: Вы ввели {len(vin)} символов. Нужно ровно 17.")

def generate_car_html(title, data, bg_color, fg_color, border_col, eng_bg, eng_fg, eng_border):
    if not data or data.get('error'):
        return f"""
        <div class="car-card" style="border-color: {border_col};">
            <div class="car-title" style="background-color: {bg_color}; color: {fg_color};">{title}</div>
            <div class="car-name" style="color: #e74c3c;">НЕ НАЙДЕНО / ОШИБКА</div>
            <div class="engine-box" style="background-color: #fdf5f6; border-color: #fab1a0;">
                <div class="eng-label" style="color:#fab1a0;">МОДЕЛЬ ДВИГАТЕЛЯ</div>
                <div class="eng-val" style="color: #e74c3c;">---</div>
            </div>
        </div>
        """
    return f"""
    <div class="car-card" style="border-color: {border_col};">
        <div class="car-title" style="background-color: {bg_color}; color: {fg_color};">{title}</div>
        <div class="car-name" style="color: {fg_color};">{data.get('car_name', 'Неизвестно')}</div>
        <div class="car-model">{data.get('model_code', '')}</div>
        <hr style="margin: 10px 0;">
        <span class="car-param">Дата:</span> <span class="car-val">{data.get('date', '-')}</span><br>
        <span class="car-param">Привод:</span> <span class="car-val">{data.get('drive', '-')}</span>
        <div class="engine-box" style="background-color: {eng_bg}; border-color: {eng_border};">
            <div class="eng-label" style="color: {eng_border};">МОДЕЛЬ ДВИГАТЕЛЯ</div>
            <div class="eng-val" style="color: {eng_fg};">{data.get('engine', 'НЕТ ДАННЫХ')}</div>
        </div>
    </div>
    """

def generate_part_html(item):
    source = item['source']
    if source == 'AUTODOC': 
        card_border, code_class = "#90caf9", "background-color: #e3f2fd; color: #0d47a1;"
    elif source == 'ELCATS': 
        card_border, code_class = "#a5d6a7", "background-color: #e8f5e9; color: #1b5e20;"
    else: 
        card_border, code_class = "#ffcc80", "background-color: #fff3e0; color: #e65100;"
    
    if item['code']:
        return f"""
        <div class="part-card" style="border-color: {card_border};">
            <div class="part-title">{item['title']}</div>
            <div class="part-code" style="{code_class}">{item['code']}</div>
            <div class="part-desc">{item['desc']}</div>
        </div>
        """
    else:
        return f"""
        <div class="part-card" style="border-color: #fab1a0;">
            <div class="part-title">{item['title']}</div>
            <div class="part-desc" style="color:red; font-style:italic;">{item['desc']}</div>
        </div>
        """

if st.button("🔍 ИСКАТЬ АВТО И ЗАПЧАСТИ", type="primary"):
    if len(vin) != 17:
        st.warning(f"Остановите поиск. Длина VIN должна быть строго 17 символов.")
    else:
        st.markdown("### 🚘 Данные автомобиля")
        car_cols = st.columns(4)
        car_phs =[col.empty() for col in car_cols]
        for p in car_phs: p.info("Поиск...")

        st.markdown("### 🔧 Найденные запчасти (Автопоиск)")
        parts_status = st.empty()
        p_cols = st.columns(3)
        
        auto_ph = p_cols[0].empty()
        elcats_ph = p_cols[1].empty()
        armtek_ph = p_cols[2].empty()

        auto_html = "<h4 style='text-align:center; color:#0d47a1;'>AUTODOC</h4>"
        elcats_html = "<h4 style='text-align:center; color:#1b5e20;'>ELCATS (Exist)</h4>"
        armtek_html = "<h4 style='text-align:center; color:#e65100;'>ARMTEK</h4>"
        
        auto_ph.markdown(auto_html, unsafe_allow_html=True)
        elcats_ph.markdown(elcats_html, unsafe_allow_html=True)
        armtek_ph.markdown(armtek_html, unsafe_allow_html=True)
        
        parts_search_started = False
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            car_futs = {
                executor.submit(get_autodoc_details, vin, PROXY_LIST[0]): (0, "AUTODOC", "#EBF5FB", "#2980B9", "#D6EAF8", "#f4f6f9", "#2c3e50", "#dcdde1"),
                executor.submit(get_exist_details, vin, PROXY_LIST[1]):   (1, "EXIST", "#E9F7EF", "#27AE60", "#D5F5E3", "#f4f6f9", "#2c3e50", "#dcdde1"),
                executor.submit(get_armtek_details, vin, PROXY_LIST[2]):  (2, "ARMTEK", "#FEF5E7", "#D35400", "#FDEBD0", "#f4f6f9", "#2c3e50", "#dcdde1"),
                executor.submit(get_partkom_details, vin, PROXY_LIST[3]): (3, "PART-KOM", "#F4ECF7", "#8E44AD", "#EBDEF0", "#f4f6f9", "#2c3e50", "#dcdde1")
            }
            
            parts_futs =[]
            all_futs = list(car_futs.keys())
            
            while all_futs:
                done, not_done = concurrent.futures.wait(all_futs, return_when=concurrent.futures.FIRST_COMPLETED)
                for fut in done:
                    if fut in car_futs:
                        idx, title, bg, fg, border, ebg, efg, eborder = car_futs[fut]
                        try: res = fut.result()
                        except: res = {'error': True}
                        
                        eng = res.get('engine', '')
                        if eng:
                            ebg, efg, eborder = "#fff0f0", "#c0392b", "#ffcccc"
                            
                            if not parts_search_started and ("G4NA" in eng or "G4KE" in eng):
                                parts_search_started = True
                                target_eng = "G4NA" if "G4NA" in eng else "G4KE"
                                parts_status.success(f"🔥 Обнаружен {target_eng}! Фоновый поиск деталей запущен...")
                                
                                tasks =[]
                                if target_eng == "G4NA":
                                    tasks = [
                                        (run_autodoc_part, (vin,["Механизм газораспределения", "Распредвал", "Шестерня распредвала"],['any'],['распредвал', 'впуск'], None, "Распредвал Впуск")),
                                        (run_autodoc_part, (vin,["Механизм газораспределения", "Распредвал", "Шестерня распредвала"], ['any'],['распредвал', 'выпуск'], None, "Распредвал Выпуск")),
                                        (run_elcats_part, (vin, "G4NA_intake", "Распредвал Впуск")),
                                        (run_elcats_part, (vin, "G4NA_exhaust", "Распредвал Выпуск")),
                                        (run_armtek_part, (vin, "G4NA_intake", "Распредвал Впуск")),
                                        (run_armtek_part, (vin, "G4NA_exhaust", "Распредвал Выпуск"))
                                    ]
                                else:
                                    tasks =[
                                        (run_autodoc_part, (vin,["Блок-картер", "Блок-картер"],["крышка", "ременного"], None, "21350", "Лобная крышка")),
                                        (run_autodoc_part, (vin,["Крепление двигателя", "Кронштейн двигателя"],["подвеска", "двигателя"], None, "21670", "Кронштейн")),
                                        (run_elcats_part, (vin, "G4KE_cover", "Лобная крышка")),
                                        (run_elcats_part, (vin, "G4KE_bracket", "Кронштейн")),
                                        (run_armtek_part, (vin, "G4KE_cover", "Лобная крышка")),
                                        (run_armtek_part, (vin, "G4KE_bracket", "Кронштейн"))
                                    ]
                                
                                for fn, args in tasks:
                                    pf = executor.submit(fn, *args)
                                    parts_futs.append(pf)
                                    not_done.add(pf)

                        html = generate_car_html(title, res, bg, fg, border, ebg, efg, eborder)
                        car_phs[idx].markdown(html, unsafe_allow_html=True)
                        
                    elif fut in parts_futs:
                        try: items = fut.result()
                        except: items =[]
                        
                        for item in items:
                            new_card = generate_part_html(item)
                            if item['source'] == 'AUTODOC':
                                auto_html += new_card
                                auto_ph.markdown(auto_html, unsafe_allow_html=True)
                            elif item['source'] == 'ELCATS':
                                elcats_html += new_card
                                elcats_ph.markdown(elcats_html, unsafe_allow_html=True)
                            elif item['source'] == 'ARMTEK':
                                armtek_html += new_card
                                armtek_ph.markdown(armtek_html, unsafe_allow_html=True)

                all_futs = list(not_done)
                
        if parts_search_started:
            parts_status.success("✅ Весь поиск завершен!")
        else:
            parts_status.warning("⚠️ Двигатель G4NA или G4KE не обнаружен. Поиск запчастей отменен.")
