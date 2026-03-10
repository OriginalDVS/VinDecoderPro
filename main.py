import streamlit as st
import threading
import time
import re
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

# Selenium imports
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# ================================================================
# PAGE CONFIG
# ================================================================
st.set_page_config(
    page_title="VIN Decoder Pro",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ================================================================
# LIGHT THEME CSS
# ================================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700;800&family=Inter:wght@300;400;500;600;700;800&display=swap');

#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

.stApp {
    background: #f5f6fa;
    font-family: 'Inter', sans-serif;
}

.main-title {
    font-family: 'JetBrains Mono', monospace;
    font-weight: 800;
    font-size: 28px;
    letter-spacing: 2px;
    color: #1a1d2e;
    text-align: center;
    margin-bottom: 2px;
}
.main-title span { color: #3b6cf5; }
.subtitle {
    text-align: center;
    color: #8c90a4;
    font-size: 13px;
    letter-spacing: 0.5px;
    margin-bottom: 16px;
}

.car-card {
    background: #ffffff;
    border: 1px solid #e2e4ec;
    border-radius: 10px;
    overflow: hidden;
    margin-bottom: 10px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}
.car-header {
    padding: 7px 12px;
    font-family: 'JetBrains Mono', monospace;
    font-weight: 800;
    font-size: 11px;
    letter-spacing: 2px;
    text-transform: uppercase;
}
.car-header.autodoc { background: #eef4ff; color: #3b6cf5; }
.car-header.exist   { background: #eefbf3; color: #1da355; }
.car-header.armtek  { background: #fef6ec; color: #d48210; }
.car-header.partkom { background: #f5eefa; color: #8b44c8; }

.car-body { padding: 12px 14px; }
.car-name { font-weight: 700; font-size: 14px; color: #1a1d2e; margin-bottom: 3px; }
.car-model { font-family: 'JetBrains Mono', monospace; font-size: 11px; color: #8c90a4; margin-bottom: 8px; }
.car-prop { display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 2px; }
.car-prop-label { color: #8c90a4; }
.car-prop-value { font-weight: 600; color: #1a1d2e; }

.engine-box {
    background: #f5f6fa;
    border: 1px solid #e2e4ec;
    border-radius: 8px;
    padding: 8px;
    text-align: center;
    font-family: 'JetBrains Mono', monospace;
    font-weight: 800;
    font-size: 20px;
    color: #c0c3d0;
    margin-top: 8px;
}
.engine-box.found {
    background: #fef2f1;
    border-color: #f5c6c2;
    color: #d63c2f;
}
.engine-box.error { color: #d63c2f; }
.engine-box.loading {
    color: #8c90a4;
    font-size: 13px;
    font-weight: 500;
}

.part-card {
    background: #ffffff;
    border: 1px solid #e2e4ec;
    border-radius: 10px;
    overflow: hidden;
    margin-bottom: 8px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.03);
}
.part-header {
    padding: 5px 12px;
    font-size: 11px;
    font-weight: 700;
    display: flex;
    justify-content: space-between;
}
.part-header.autodoc { background: #eef4ff; color: #3b6cf5; }
.part-header.elcats  { background: #eefbf3; color: #1da355; }
.part-header.armtek  { background: #fef6ec; color: #d48210; }

.part-body {
    padding: 10px 12px;
    display: flex;
    align-items: center;
    gap: 10px;
}
.part-code {
    font-family: 'JetBrains Mono', monospace;
    font-weight: 700;
    font-size: 14px;
    background: #f5f6fa;
    border: 1px solid #e2e4ec;
    padding: 5px 10px;
    border-radius: 6px;
    color: #1a1d2e;
    white-space: nowrap;
}
.part-desc { font-size: 12px; color: #8c90a4; line-height: 1.4; }

.section-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    letter-spacing: 2px;
    color: #8c90a4;
    text-transform: uppercase;
    margin: 18px 0 10px;
    border-bottom: 1px solid #e2e4ec;
    padding-bottom: 8px;
}

.status-line {
    font-size: 12px;
    color: #8c90a4;
    padding: 6px 0;
    display: flex;
    align-items: center;
    gap: 8px;
}
.status-dot {
    width: 7px; height: 7px;
    border-radius: 50%;
    background: #1da355;
    display: inline-block;
}
.status-dot.working {
    background: #d48210;
    animation: pulse 1s infinite;
}
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.3; }
}

.stTextInput > div > div > input {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 17px !important;
    font-weight: 700 !important;
    letter-spacing: 2px !important;
    text-transform: uppercase !important;
    background: #ffffff !important;
    border: 1px solid #d0d3e0 !important;
    color: #1a1d2e !important;
    border-radius: 8px !important;
}
.stTextInput > div > div > input:focus {
    border-color: #3b6cf5 !important;
    box-shadow: 0 0 0 3px rgba(59, 108, 245, 0.12) !important;
}
.stTextInput label { display: none !important; }

.stButton > button {
    background: #3b6cf5 !important;
    color: white !important;
    font-weight: 700 !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 10px 24px !important;
    font-size: 14px !important;
    width: 100% !important;
}
.stButton > button:hover {
    background: #2d5bd9 !important;
}

.empty-hint {
    text-align: center;
    color: #b0b3c4;
    padding: 30px 10px;
    font-size: 13px;
}

/* Loading banner */
.loading-banner {
    background: linear-gradient(135deg, #eef4ff 0%, #f0f1ff 100%);
    border: 1px solid #c8d6f5;
    border-radius: 10px;
    padding: 16px 20px;
    display: flex;
    align-items: center;
    gap: 14px;
    margin: 8px 0 14px;
    animation: bannerFadeIn 0.3s ease-out;
}
@keyframes bannerFadeIn {
    from { opacity: 0; transform: translateY(-6px); }
    to { opacity: 1; transform: translateY(0); }
}
.loading-spinner {
    width: 22px; height: 22px;
    border: 3px solid #d0d8f0;
    border-top-color: #3b6cf5;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    flex-shrink: 0;
}
@keyframes spin { to { transform: rotate(360deg); } }
.loading-banner-text {
    font-size: 15px;
    font-weight: 600;
    color: #2c4596;
}
.loading-banner-sub {
    font-size: 12px;
    color: #6b7cb0;
    margin-top: 2px;
}

.loading-banner.done {
    background: linear-gradient(135deg, #eefbf3 0%, #f0faf5 100%);
    border-color: #b0e0c8;
}
.loading-banner.done .loading-banner-text { color: #1a7d45; }
.loading-banner.done .loading-banner-sub { color: #5a9c76; }
</style>
""", unsafe_allow_html=True)


# ================================================================
# SELENIUM BROWSER HELPER
# ================================================================

def create_driver():
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--lang=ru-RU')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')
    options.binary_location = "/usr/bin/chromium"

    try:
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=options)
    except Exception:
        try:
            driver = webdriver.Chrome(options=options)
        except Exception:
            options.binary_location = "/usr/bin/chromium-browser"
            driver = webdriver.Chrome(options=options)

    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "delete Object.getPrototypeOf(navigator).webdriver; window.chrome = { runtime: {} };"
    })
    driver.set_page_load_timeout(30)
    driver.implicitly_wait(2)
    return driver


def safe_find_text(driver, css, default="-"):
    try:
        return driver.find_element(By.CSS_SELECTOR, css).text.strip()
    except:
        return default


# ================================================================
# VEHICLE SCRAPERS
# ================================================================

def get_autodoc_details(vin):
    data = {'car_name': None, 'model_code': None, 'date': None, 'engine': None, 'drive': None, 'error': False}
    driver = None
    try:
        driver = create_driver()
        driver.get("https://www.autodoc.ru/")
        sb = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='search'], input.search-input")))
        sb.clear(); sb.send_keys(vin)
        driver.find_element(By.CSS_SELECTOR, "button.search-button").click()
        try:
            h1 = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "h1.catalog-originals-heading")))
            raw = h1.text.replace("Запчасти для", "").strip()
            p = raw.split()
            data['car_name'] = " ".join(p[:-1]) if len(p) > 1 else raw
        except TimeoutException:
            data['error'] = True; return data
        try:
            driver.find_element(By.CSS_SELECTOR, 'tui-icon[title="Параметры автомобиля"]').click()
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, '.dialog-car-attributes__item')))
            for item in driver.find_elements(By.CSS_SELECTOR, '.dialog-car-attributes__item'):
                try:
                    nm = item.find_element(By.CSS_SELECTOR, '.dialog-car-attributes__item-name').text
                    vl = item.find_element(By.CSS_SELECTOR, '.dialog-car-attributes__item-value').text.strip()
                    if "Номер двигателя" in nm: data['engine'] = vl[:4].upper()
                    elif "Дата выпуска" in nm: data['date'] = vl
                    elif "Модель" in nm and "год" not in nm.lower(): data['model_code'] = vl
                    elif "Опции" in nm:
                        try:
                            b = item.find_element(By.CSS_SELECTOR, '.dialog-car-attributes__item_show-more')
                            if b.is_displayed(): b.click(); time.sleep(0.5)
                        except: pass
                        opt = item.find_element(By.CSS_SELECTOR, '.dialog-car-attributes__item-value').text.upper()
                        if "4WD" in opt: data['drive'] = "4WD (Полный)"
                        elif "2WD" in opt: data['drive'] = "2WD (Передний)"
                except: continue
        except: pass
    except: data['error'] = True
    finally:
        if driver: driver.quit()
    return data


def get_exist_details(vin):
    data = {'car_name': None, 'model_code': None, 'date': None, 'engine': None, 'drive': None, 'error': False}
    driver = None
    try:
        driver = create_driver()
        driver.get(f"https://exist.ru/Price/Empty.aspx?q={vin}")
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR, '.car-info')))
        data['car_name'] = safe_find_text(driver, '.car-info__car-name', None)
        data['date'] = safe_find_text(driver, '.car-info__car-years', None)
        if data['car_name']:
            nu = data['car_name'].upper()
            if "4WD" in nu or "AWD" in nu: data['drive'] = "4WD (Полный)"
            elif "2WD" in nu: data['drive'] = "2WD (Передний)"
            m = re.search(r'\(([A-Z0-9]{4,5})\)', data['car_name'])
            if m: data['engine'] = m.group(1)
        if not data['drive']:
            try:
                txt = driver.find_element(By.CSS_SELECTOR, '.car-info').text
                md = re.search(r'Transaxle:\s*([A-Z0-9\s-]+?)(?:\s*\||$)', txt)
                if md:
                    d = md.group(1).strip()
                    if "2WD" in d: data['drive'] = "2WD (Передний)"
                    elif "4WD" in d: data['drive'] = "4WD (Полный)"
                    else: data['drive'] = d
            except: pass
    except: data['error'] = True
    finally:
        if driver: driver.quit()
    return data


def get_armtek_details(vin):
    data = {'car_name': None, 'model_code': None, 'date': None, 'engine': None, 'drive': None, 'error': False}
    driver = None
    try:
        driver = create_driver()
        driver.get(f"https://armtek.ru/search?text={vin}")
        driver.execute_script("""
            const obs = new MutationObserver(() => {
                document.querySelectorAll('.cdk-overlay-container, project-ui-geo-dialog').forEach(e => e.remove());
            });
            obs.observe(document.body, {childList: true, subtree: true});
            document.querySelectorAll('.cdk-overlay-container, project-ui-geo-dialog').forEach(e => e.remove());
        """)
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.car__header")))
        try:
            hdr = driver.find_elements(By.CSS_SELECTOR, 'mat-expansion-panel-header')
            if hdr:
                cls = hdr[0].get_attribute('class') or ''
                if 'mat-expanded' not in cls and hdr[0].is_displayed():
                    hdr[0].click(); time.sleep(1)
        except: pass
        for item in driver.find_elements(By.CSS_SELECTOR, 'div.car__main-information-item'):
            try:
                t = item.find_element(By.CSS_SELECTOR, 'p.car__main-information-item-title').text.strip()
                v = item.find_element(By.CSS_SELECTOR, 'p.font__body2').text.strip()
                if "Модель" in t and "год" not in t.lower(): data['model_code'] = v
                elif "Дата выпуска" in t: data['date'] = v
                elif "Номер двигателя" in t: data['engine'] = v[:4].upper()
                elif "Опции" in t:
                    if "4WD" in v: data['drive'] = "4WD (Полный)"
                    elif "2WD" in v: data['drive'] = "2WD (Передний)"
            except: continue
        try:
            tel = driver.find_element(By.CSS_SELECTOR, 'div.car__header-info-title p')
            if tel.is_displayed(): data['car_name'] = tel.text.strip()
        except: pass
    except: data['error'] = True
    finally:
        if driver: driver.quit()
    return data


def get_partkom_details(vin):
    data = {'car_name': None, 'model_code': None, 'date': None, 'engine': None, 'drive': None, 'error': False}
    driver = None
    try:
        driver = create_driver()
        driver.get(f"https://part-kom.ru/catalog-vin?vin={vin}")
        iframe_elem = None; found = False
        for _ in range(100):
            try:
                driver.execute_script("document.querySelectorAll('button').forEach(b=>{if(b.innerText.includes('Да, верно')||b.ariaLabel==='закрыть')b.click();})")
            except: pass
            if not iframe_elem:
                try:
                    ifs = driver.find_elements(By.CSS_SELECTOR, 'iframe[src*="b2b.part-kom.ru"]')
                    if ifs: iframe_elem = ifs[0]; driver.switch_to.frame(iframe_elem)
                except: pass
            if iframe_elem:
                try:
                    try:
                        bs = driver.find_elements(By.XPATH, "//button[contains(text(),'Все параметры')]")
                        if bs and bs[0].is_displayed(): bs[0].click(); time.sleep(0.5)
                    except: pass
                    params = driver.find_elements(By.CSS_SELECTOR,
                        'div[class*="grouped-cars-list-group__parameter"],li[class*="cars-list-item-mobile__parameter"]')
                    if params:
                        try:
                            ts = driver.find_elements(By.CSS_SELECTOR,
                                'div[class*="grouped-cars-list-group__title"],div[class*="cars-list-item-mobile__brand"]')
                            if ts: data['car_name'] = ts[0].text.strip()
                        except: pass
                        for pi in params:
                            divs = pi.find_elements(By.TAG_NAME, 'div')
                            if len(divs) >= 2:
                                k, v = divs[0].text.strip(), divs[1].text.strip()
                                if "Год" in k: data['date'] = v
                                elif "Код двигателя" in k: data['engine'] = v[:4].upper() if len(v) > 4 else v
                                elif "Transaxle" in k:
                                    if "4WD" in v: data['drive'] = "4WD (Полный)"
                                    elif "2WD" in v: data['drive'] = "2WD (Передний)"
                        found = True; break
                except: pass
            time.sleep(0.15)
        if not found: data['error'] = True
    except: data['error'] = True
    finally:
        if driver:
            try: driver.switch_to.default_content()
            except: pass
            driver.quit()
    return data


# ================================================================
# PARTS SCRAPERS
# ================================================================

def get_elcats_parts(vin, mode, part_type, title):
    cfg = {
        'G4NA_intake':  {'gk': 'РАСПРЕДЕЛИТЕЛЬНЫЙ ВАЛ И КЛАПАН', 'nd': 'РАСПРЕДВАЛ В СБОРЕ-ВПУСКНОЙ'},
        'G4NA_exhaust': {'gk': 'РАСПРЕДЕЛИТЕЛЬНЫЙ ВАЛ И КЛАПАН', 'nd': 'РАСПРЕДЕЛИТЕЛЬНЫЙ ВАЛ В СБОРЕ-ВЫХЛОПНОЙ'},
    }
    for e in ['G4KE','G4KJ','G4KH']:
        cfg[f'{e}_cover']   = {'gk': 'КРЫШКА РЕМНЯ И МАСЛЯНЫЙ ПОДДОН', 'nd': 'КРЫШКА В СБОРЕ-ПРИВОДНАЯ ЦЕПЬ'}
        cfg[f'{e}_bracket'] = {'gk': 'КРЕПЛЕНИЯ ДВИГАТЕЛЯ И ТРАНСМИССИИ', 'nd': 'КРОНШТЕЙН В СБОРЕ-ОПОРА ДВИГАТЕЛЯ'}
    conf = cfg.get(f"{mode}_{part_type}")
    if not conf: return []
    gk, nd = conf['gk'], conf['nd']
    items = []; driver = None
    try:
        driver = create_driver()
        driver.get(f"https://www.elcats.ru/hyundai/default.aspx?carvin={vin}")
        time.sleep(3)
        if "default.aspx" in driver.current_url.lower():
            try: el = driver.find_element(By.ID, 'ctl00_cphMasterPage_txbVIN'); el.clear(); el.send_keys(vin)
            except: el = driver.find_element(By.CSS_SELECTOR, 'input[type=text]'); el.clear(); el.send_keys(vin)
            time.sleep(0.3)
            driver.find_element(By.ID, 'ctl00_cphMasterPage_btnFindByVIN').click()
            time.sleep(3)
        m = re.search(r'Model=([a-f0-9\-]{36})', driver.current_url, re.I)
        if not m: return items
        mu = m.group(1)
        gid = driver.execute_script(f"""var ls=document.querySelectorAll('a[href^="javascript:submit"]');
            for(var i=0;i<ls.length;i++){{if(ls[i].textContent.toUpperCase().indexOf("{gk.upper()}")!==-1)
            {{var m=ls[i].getAttribute('href').match(/submit\\('([^']+)'/);if(m)return m[1];}}}}return null;""")
        if not gid: return items
        driver.get(f"https://www.elcats.ru/hyundai/Unit.aspx?GroupId={gid}&Model={mu}&Title={urllib.parse.quote(gk)}")
        time.sleep(3)
        cids = driver.execute_script(f"""var ns=document.querySelectorAll('div.CNode');var r=[];
            ns.forEach(function(n){{var s=n.querySelector('span.descr-ru');
            if(s&&s.textContent.toUpperCase().indexOf("{nd.upper()}")!==-1)r.push(n.getAttribute('id'));}});return r;""")
        seen = set()
        for cid in cids:
            try:
                driver.find_element(By.ID, cid).click(); time.sleep(4)
                pd = driver.execute_script("""var r=[];document.querySelectorAll('table.OpelParts tr').forEach(function(row,i){
                    if(i===0)return;var tds=row.querySelectorAll('td');if(tds.length<2)return;
                    var a=tds[0].querySelector('a');var code=(a?a.textContent:tds[0].textContent).replace(/\\s+/g,' ').trim();
                    var sp=tds[1].querySelector('span.descr-ru');var descr=(sp?sp.textContent:tds[1].textContent).replace(/\\s+/g,' ').trim();
                    var period=tds.length>3?tds[3].textContent.replace(/\\s+/g,' ').trim():"";
                    var info=tds.length>4?tds[4].textContent.replace(/\\s+/g,' ').trim():"";
                    if(code.length>3)r.push({code:code,descr:descr,period:period,info:info});});return r;""")
                for pt in pd:
                    if pt['code'] not in seen:
                        seen.add(pt['code'])
                        fd = pt['descr']
                        if pt.get('period'): fd += f" [{pt['period']}]"
                        if pt.get('info'): fd += f" ({pt['info']})"
                        items.append({'source': 'ELCATS', 'title': title, 'desc': fd, 'code': pt['code']})
            except: continue
    except: pass
    finally:
        if driver: driver.quit()
    return items


def get_armtek_parts(vin, mode, part_type, title):
    cfg = {
        'G4NA_intake':  {'q': 'распредвал впускной',  'kw': 'впускной', 'ign': []},
        'G4NA_exhaust': {'q': 'распредвал выпускной', 'kw': 'выпускной','ign': []},
    }
    for e in ['G4KE','G4KJ','G4KH']:
        cfg[f'{e}_cover']   = {'q': 'КОЖУХ В СБОРЕ-ЦЕПЬ ГРМ', 'kw': 'кожух',     'ign': []}
        cfg[f'{e}_bracket'] = {'q': 'кронштейн двигателя',     'kw': 'кронштейн', 'ign': ['двигатель уст','опора','подвеска']}
    conf = cfg.get(f"{mode}_{part_type}")
    if not conf: return []
    items = []; driver = None
    try:
        driver = create_driver()
        driver.get(f"https://armtek.ru/search?text={vin}")
        driver.execute_script("""const obs=new MutationObserver(()=>{
            document.querySelectorAll('.cdk-overlay-container,project-ui-geo-dialog').forEach(e=>e.remove());});
            obs.observe(document.body,{childList:true,subtree:true});
            document.querySelectorAll('.cdk-overlay-container,project-ui-geo-dialog').forEach(e=>e.remove());""")
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.car__header")))
        inp = WebDriverWait(driver, 15).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, 'input[placeholder="Наименование запчасти"]')))
        inp.click(); inp.send_keys(Keys.CONTROL+"a"); inp.send_keys(Keys.DELETE)
        time.sleep(0.5); inp.send_keys(conf['q']); time.sleep(0.5); inp.send_keys(Keys.ENTER)
        time.sleep(3)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.part")))
        parts = driver.execute_script(f"""var r=[],s={{}};document.querySelectorAll('div.part').forEach(function(p){{
            var nm=p.querySelector('div.title-name'),oem=p.querySelector('div.oem');if(!nm||!oem)return;
            var name=nm.textContent.trim(),code=oem.textContent.trim();if(code.length<4||s[code])return;s[code]=true;
            r.push({{name:name,code:code,match:name.toLowerCase().includes("{conf['kw'].lower()}")}});}});return r;""")
        for pt in parts:
            if any(ig.lower() in pt['name'].lower() for ig in conf['ign']): continue
            if pt['match']: items.append({'source': 'ARMTEK', 'title': title, 'desc': pt['name'], 'code': pt['code']})
        if not items and parts:
            for pt in parts:
                if any(ig.lower() in pt['name'].lower() for ig in conf['ign']): continue
                items.append({'source': 'ARMTEK', 'title': title, 'desc': pt['name'], 'code': pt['code']}); break
    except: pass
    finally:
        if driver: driver.quit()
    return items


def get_autodoc_parts(vin, mode, part_type, title):
    cfg = {
        'G4NA_intake':  {'path': ['Двигатель','Механизм газораспределения'], 'pkw': ['распредвал','впуск'], 'cpfx': None},
        'G4NA_exhaust': {'path': ['Двигатель','Механизм газораспределения'], 'pkw': ['распредвал','выпуск'],'cpfx': None},
    }
    for e in ['G4KE','G4KJ','G4KH']:
        cfg[f'{e}_cover']   = {'path': ['Двигатель','Блок-картер'],        'pkw': None, 'cpfx': '21350'}
        cfg[f'{e}_bracket'] = {'path': ['Двигатель','Крепление двигателя'], 'pkw': None, 'cpfx': '21670'}
    conf = cfg.get(f"{mode}_{part_type}")
    if not conf: return []
    items = []; driver = None
    try:
        driver = create_driver()
        driver.get("https://www.autodoc.ru/")
        sb = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='search'],input.search-input")))
        sb.clear(); sb.send_keys(vin)
        driver.find_element(By.CSS_SELECTOR, "button.search-button").click()
        time.sleep(3)
        for step in conf['path']:
            try:
                for n in driver.find_elements(By.CSS_SELECTOR, "p.catalog-node__name"):
                    if step.lower() in n.text.lower(): n.click(); time.sleep(1); break
            except: pass
        time.sleep(2)
        for g in driver.find_elements(By.CSS_SELECTOR, '.goods__item'):
            try:
                txt = g.text.lower(); ok = False
                if conf['pkw'] and all(w in txt for w in conf['pkw']): ok = True
                if conf['cpfx'] and conf['cpfx'] in txt: ok = True
                if ok:
                    lnk = g.find_element(By.CSS_SELECTOR, 'a.goods__item-link')
                    driver.get(lnk.get_attribute('href'))
                    try:
                        WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, '.properties__description-text')))
                        desc = driver.find_element(By.CSS_SELECTOR, '.properties__description-text').text
                        cm = re.search(r'([A-Z0-9]{5,20})$', desc.strip())
                        items.append({'source': 'AUTODOC', 'title': title, 'desc': desc, 'code': cm.group(1) if cm else None})
                    except: pass
                    break
            except: continue
    except: pass
    finally:
        if driver: driver.quit()
    return items


# ================================================================
# RENDER HELPERS
# ================================================================

def render_car_card(key, title, data):
    if data is None:
        return f"""<div class="car-card"><div class="car-header {key}">{title}</div>
            <div class="car-body"><div class="car-name" style="color:#b0b3c4">Ожидание...</div><div class="car-model">&nbsp;</div>
            <div class="car-prop"><span class="car-prop-label">Дата:</span><span class="car-prop-value">-</span></div>
            <div class="car-prop"><span class="car-prop-label">Привод:</span><span class="car-prop-value">-</span></div>
            <div class="engine-box loading">⏳ загрузка...</div></div></div>"""
    if data.get('error'):
        return f"""<div class="car-card"><div class="car-header {key}">{title}</div>
            <div class="car-body"><div class="car-name" style="color:#d63c2f">НЕ НАЙДЕНО</div><div class="car-model">&nbsp;</div>
            <div class="car-prop"><span class="car-prop-label">Дата:</span><span class="car-prop-value">-</span></div>
            <div class="car-prop"><span class="car-prop-label">Привод:</span><span class="car-prop-value">-</span></div>
            <div class="engine-box error">---</div></div></div>"""
    eng = data.get('engine', '')
    ec = 'found' if eng else 'error'
    et = eng if eng else 'НЕТ ДАННЫХ'
    return f"""<div class="car-card"><div class="car-header {key}">{title}</div>
        <div class="car-body"><div class="car-name">{data.get('car_name') or 'Неизвестно'}</div>
        <div class="car-model">{data.get('model_code') or ''}</div>
        <div class="car-prop"><span class="car-prop-label">Дата:</span><span class="car-prop-value">{data.get('date') or '-'}</span></div>
        <div class="car-prop"><span class="car-prop-label">Привод:</span><span class="car-prop-value">{data.get('drive') or '-'}</span></div>
        <div class="engine-box {ec}">{et}</div></div></div>"""


def render_part_card(item):
    src = item.get('source', '').lower()
    ch = f'<span class="part-code">📋 {item["code"]}</span>' if item.get('code') else ''
    return f"""<div class="part-card"><div class="part-header {src}"><span>{item.get('title','')}</span><span>{item.get('source','')}</span></div>
        <div class="part-body">{ch}<span class="part-desc">{item.get('desc','')}</span></div></div>"""


# ================================================================
# SESSION STATE
# ================================================================
for k, v in [('results', {}), ('parts', []), ('engine_model', ''), ('vin', '')]:
    if k not in st.session_state:
        st.session_state[k] = v

# ================================================================
# LAYOUT
# ================================================================
st.markdown('<div class="main-title">VIN <span>DECODER</span> PRO</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Поиск по 4 источникам • Автоопределение двигателя • Поиск запчастей</div>', unsafe_allow_html=True)

col_input, col_btn = st.columns([3, 1])
with col_input:
    vin_input = st.text_input("VIN", value=st.session_state.vin, max_chars=17,
                               placeholder="Введите VIN (17 символов)", key="vin_field")
with col_btn:
    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
    search_clicked = st.button("🔍 ИСКАТЬ ДВС", use_container_width=True)

# Loading banner placeholder (right under the search bar, highly visible)
ph_loading_banner = st.empty()

# Placeholders for incremental updates
car_c1, car_c2 = st.columns(2)
with car_c1:
    ph_autodoc = st.empty()
    ph_armtek = st.empty()
with car_c2:
    ph_exist = st.empty()
    ph_partkom = st.empty()

ph_engine = st.empty()
st.markdown('<div class="section-title">НАЙДЕННЫЕ ЗАПЧАСТИ</div>', unsafe_allow_html=True)
ph_parts_status = st.empty()
ph_parts = st.empty()
ph_codes = st.empty()
ph_manual = st.empty()
ph_status = st.empty()


# ================================================================
# DISPLAY SAVED (no search happening)
# ================================================================
def display_saved():
    r = st.session_state.results
    ph_autodoc.markdown(render_car_card('autodoc', 'AUTODOC', r.get('autodoc')), unsafe_allow_html=True)
    ph_exist.markdown(render_car_card('exist', 'EXIST / ELCATS', r.get('exist')), unsafe_allow_html=True)
    ph_armtek.markdown(render_car_card('armtek', 'ARMTEK', r.get('armtek')), unsafe_allow_html=True)
    ph_partkom.markdown(render_car_card('partkom', 'PART-KOM', r.get('partkom')), unsafe_allow_html=True)

    if r:
        engs = [d['engine'] for d in r.values() if d and not d.get('error') and d.get('engine')]
        if engs:
            et = " / ".join(set(engs))
            if st.session_state.engine_model:
                ph_engine.success(f"🔧 Двигатель: **{et}** → запчасти для **{st.session_state.engine_model}**")
            else:
                ph_engine.info(f"🔧 Двигатель: **{et}**")

    pts = st.session_state.parts
    if pts:
        ph_parts.markdown("".join(render_part_card(p) for p in pts), unsafe_allow_html=True)
        codes = list(dict.fromkeys(p['code'] for p in pts if p.get('code')))
        if codes:
            md = "**📋 Коды для копирования:**\n\n"
            for c in codes:
                s = next((f"{p['source']} — {p['title']}" for p in pts if p.get('code') == c), '')
                md += f"`{c}` — {s}\n\n"
            ph_codes.markdown(md)
    elif r:
        ph_parts.markdown('<div class="empty-hint">Запчасти не найдены или двигатель не из списка G4NA/G4KE/G4KJ/G4KH</div>', unsafe_allow_html=True)
    else:
        ph_parts.markdown('<div class="empty-hint">Введите VIN и нажмите «ИСКАТЬ ДВС»</div>', unsafe_allow_html=True)

    if r and not st.session_state.engine_model:
        with ph_manual.container():
            st.markdown("---")
            st.markdown("**Ручной поиск запчастей:**")
            mm = st.selectbox("Двигатель", ["G4NA", "G4KE", "G4KJ", "G4KH"], key="manual_sel")
            if st.button(f"🔍 Искать запчасти для {mm}", key="manual_btn"):
                st.session_state.engine_model = mm
                st.rerun()

    ph_status.markdown(
        f'<div class="status-line"><span class="status-dot"></span> {"Поиск завершён" if r else "Ожидание ввода"}</div>',
        unsafe_allow_html=True)


# ================================================================
# INCREMENTAL SEARCH
# ================================================================
if search_clicked:
    vin = vin_input.strip().upper()
    if len(vin) != 17:
        st.error("⚠️ VIN должен быть ровно 17 символов!")
        display_saved()
    else:
        st.session_state.vin = vin
        st.session_state.results = {}
        st.session_state.parts = []
        st.session_state.engine_model = ''

        # Show loading banner at top
        ph_loading_banner.markdown("""
        <div class="loading-banner">
            <div class="loading-spinner"></div>
            <div>
                <div class="loading-banner-text">🔍 Идёт поиск...</div>
                <div class="loading-banner-sub">Опрашиваем 4 источника, это может занять до минуты</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Show loading cards
        ph_autodoc.markdown(render_car_card('autodoc', 'AUTODOC', None), unsafe_allow_html=True)
        ph_exist.markdown(render_car_card('exist', 'EXIST / ELCATS', None), unsafe_allow_html=True)
        ph_armtek.markdown(render_car_card('armtek', 'ARMTEK', None), unsafe_allow_html=True)
        ph_partkom.markdown(render_car_card('partkom', 'PART-KOM', None), unsafe_allow_html=True)
        ph_status.markdown('<div class="status-line"><span class="status-dot working"></span> Поиск информации об авто...</div>', unsafe_allow_html=True)
        ph_parts.markdown('<div class="empty-hint">⏳ Ожидание определения двигателя...</div>', unsafe_allow_html=True)

        results = {}
        engine_model = ''
        all_parts = []
        ph_map = {'autodoc': ph_autodoc, 'exist': ph_exist, 'armtek': ph_armtek, 'partkom': ph_partkom}
        titles = {'autodoc': 'AUTODOC', 'exist': 'EXIST / ELCATS', 'armtek': 'ARMTEK', 'partkom': 'PART-KOM'}
        funcs = {'autodoc': get_autodoc_details, 'exist': get_exist_details,
                 'armtek': get_armtek_details, 'partkom': get_partkom_details}
        fmap = {'autodoc': get_autodoc_parts, 'elcats': get_elcats_parts, 'armtek': get_armtek_parts}

        # One big pool: sites (4) + parts (up to 6) = 10 workers
        # Parts are submitted AS SOON as engine is detected from any site
        done_sites = 0
        parts_submitted = False
        parts_total = 0
        parts_done = 0

        # Track which future is which: 'site:autodoc' or 'part:elcats:Лобная крышка'
        fut_map = {}  # future -> ('site', site_key) or ('part', site_key, title)

        with ThreadPoolExecutor(max_workers=10) as pool:
            # Submit all 4 site lookups
            for site_key, fn in funcs.items():
                f = pool.submit(fn, vin)
                fut_map[f] = ('site', site_key)

            # Process results as they arrive
            pending = set(fut_map.keys())
            while pending:
                # Wait for next completed future
                done_batch = set()
                for f in list(pending):
                    if f.done():
                        done_batch.add(f)
                if not done_batch:
                    time.sleep(0.05)
                    continue

                for fut in done_batch:
                    pending.discard(fut)
                    info = fut_map[fut]

                    if info[0] == 'site':
                        # ---- Vehicle site result ----
                        site_key = info[1]
                        try: data = fut.result()
                        except: data = {'error': True}
                        results[site_key] = data
                        done_sites += 1

                        # Update card immediately
                        ph_map[site_key].markdown(
                            render_car_card(site_key, titles[site_key], data), unsafe_allow_html=True)

                        # Detect engine → immediately submit parts
                        if not engine_model and data and not data.get('error') and data.get('engine'):
                            eng = data['engine']
                            for m in ['G4NA', 'G4KE', 'G4KJ', 'G4KH']:
                                if m in eng:
                                    engine_model = m
                                    break

                        if engine_model and not parts_submitted:
                            parts_submitted = True
                            ph_engine.success(
                                f"🔧 Двигатель **{engine_model}** найден через {titles[site_key]} — запускаю поиск запчастей!")

                            # Build parts tasks
                            if engine_model == 'G4NA':
                                ptasks = [
                                    ('autodoc','G4NA','intake','Распредвал Впуск'),
                                    ('autodoc','G4NA','exhaust','Распредвал Выпуск'),
                                    ('elcats','G4NA','intake','Распредвал Впуск'),
                                    ('elcats','G4NA','exhaust','Распредвал Выпуск'),
                                    ('armtek','G4NA','intake','Распредвал Впуск'),
                                    ('armtek','G4NA','exhaust','Распредвал Выпуск'),
                                ]
                            else:
                                ptasks = [
                                    ('autodoc',engine_model,'cover','Лобная крышка'),
                                    ('autodoc',engine_model,'bracket','Кронштейн'),
                                    ('elcats',engine_model,'cover','Лобная крышка'),
                                    ('elcats',engine_model,'bracket','Кронштейн'),
                                    ('armtek',engine_model,'cover','Лобная крышка'),
                                    ('armtek',engine_model,'bracket','Кронштейн'),
                                ]
                            parts_total = len(ptasks)

                            # Submit all parts tasks into the SAME pool
                            for ps, pm, ppt, pttl in ptasks:
                                pf = pool.submit(fmap[ps], vin, pm, ppt, pttl)
                                fut_map[pf] = ('part', ps, pttl)
                                pending.add(pf)

                        # Update banner
                        banner_sub = f"Источник {titles[site_key]} {'✅' if data and not data.get('error') else '❌'}"
                        if parts_submitted:
                            banner_sub += f" • Запчасти {engine_model} уже ищутся"
                        ph_loading_banner.markdown(f"""
                        <div class="loading-banner">
                            <div class="loading-spinner"></div>
                            <div>
                                <div class="loading-banner-text">🔍 Идёт поиск — авто {done_sites}/4{f' + запчасти {parts_done}/{parts_total}' if parts_submitted else ''}</div>
                                <div class="loading-banner-sub">{banner_sub}</div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        ph_status.markdown(
                            f'<div class="status-line"><span class="status-dot working"></span> Авто: {done_sites}/4'
                            f'{f" • Запчасти: {parts_done}/{parts_total}" if parts_submitted else ""}</div>',
                            unsafe_allow_html=True)

                    elif info[0] == 'part':
                        # ---- Parts result ----
                        p_site, p_title = info[1], info[2]
                        parts_done += 1
                        try:
                            new_items = fut.result()
                            if new_items:
                                all_parts.extend(new_items)
                        except: pass

                        # Update parts display immediately
                        if all_parts:
                            ph_parts.markdown(
                                "".join(render_part_card(p) for p in all_parts), unsafe_allow_html=True)
                        elif parts_done == 1:
                            ph_parts.markdown(
                                '<div class="empty-hint">⏳ Поиск запчастей...</div>', unsafe_allow_html=True)

                        # Update banner
                        ph_loading_banner.markdown(f"""
                        <div class="loading-banner">
                            <div class="loading-spinner"></div>
                            <div>
                                <div class="loading-banner-text">{'🔍' if done_sites < 4 else '⚙️'} Авто {done_sites}/4 • Запчасти {parts_done}/{parts_total}</div>
                                <div class="loading-banner-sub">Найдено деталей: {len(all_parts)} • {p_title} ({p_site}) ✅</div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        ph_status.markdown(
                            f'<div class="status-line"><span class="status-dot working"></span>'
                            f' Авто: {done_sites}/4 • Запчасти: {parts_done}/{parts_total}</div>',
                            unsafe_allow_html=True)

        # ---- All done ----
        st.session_state.results = results
        st.session_state.engine_model = engine_model
        st.session_state.parts = all_parts

        # Final engine info (might have more engines from later sites)
        engs = [d['engine'] for d in results.values() if d and not d.get('error') and d.get('engine')]
        if engs:
            et = " / ".join(sorted(set(engs)))
            if engine_model:
                ph_engine.success(f"🔧 Двигатель: **{et}** → запчасти для **{engine_model}**")
            else:
                ph_engine.info(f"🔧 Двигатель: **{et}**")

        # Final parts codes
        if all_parts:
            ph_parts.markdown("".join(render_part_card(p) for p in all_parts), unsafe_allow_html=True)
            codes = list(dict.fromkeys(p['code'] for p in all_parts if p.get('code')))
            if codes:
                md = "**📋 Коды для копирования:**\n\n"
                for c in codes:
                    sr = next((f"{p['source']} — {p['title']}" for p in all_parts if p.get('code') == c), '')
                    md += f"`{c}` — {sr}\n\n"
                ph_codes.markdown(md)
        elif parts_submitted:
            ph_parts.markdown('<div class="empty-hint">Запчасти не найдены</div>', unsafe_allow_html=True)

        total_parts = len(all_parts)
        ph_status.markdown('<div class="status-line"><span class="status-dot"></span> ✅ Поиск завершён!</div>', unsafe_allow_html=True)
        ph_loading_banner.markdown(f"""
        <div class="loading-banner done">
            <div style="font-size:22px; flex-shrink:0;">✅</div>
            <div>
                <div class="loading-banner-text">Поиск завершён!</div>
                <div class="loading-banner-sub">Источников: 4 • Найдено запчастей: {total_parts}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

elif st.session_state.engine_model and not st.session_state.parts and st.session_state.results:
    # Manual engine selected via rerun
    vin = st.session_state.vin
    engine_model = st.session_state.engine_model
    display_saved()

    ph_status.markdown(
        f'<div class="status-line"><span class="status-dot working"></span> Поиск запчастей {engine_model}...</div>',
        unsafe_allow_html=True)

    if engine_model == 'G4NA':
        tasks = [
            ('autodoc','G4NA','intake','Распредвал Впуск'), ('autodoc','G4NA','exhaust','Распредвал Выпуск'),
            ('elcats','G4NA','intake','Распредвал Впуск'),  ('elcats','G4NA','exhaust','Распредвал Выпуск'),
            ('armtek','G4NA','intake','Распредвал Впуск'),  ('armtek','G4NA','exhaust','Распредвал Выпуск'),
        ]
    else:
        tasks = [
            ('autodoc',engine_model,'cover','Лобная крышка'), ('autodoc',engine_model,'bracket','Кронштейн'),
            ('elcats',engine_model,'cover','Лобная крышка'),  ('elcats',engine_model,'bracket','Кронштейн'),
            ('armtek',engine_model,'cover','Лобная крышка'),  ('armtek',engine_model,'bracket','Кронштейн'),
        ]

    fmap = {'autodoc': get_autodoc_parts, 'elcats': get_elcats_parts, 'armtek': get_armtek_parts}
    all_parts = []; total = len(tasks)

    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(fmap[s], vin, m, pt, ttl): (s, ttl) for s, m, pt, ttl in tasks}
        pdone = 0
        for fut in as_completed(futs):
            pdone += 1
            try:
                new = fut.result()
                if new: all_parts.extend(new)
            except: pass
            if all_parts:
                ph_parts.markdown("".join(render_part_card(p) for p in all_parts), unsafe_allow_html=True)
            ph_status.markdown(
                f'<div class="status-line"><span class="status-dot working"></span> Запчасти: {pdone}/{total}</div>',
                unsafe_allow_html=True)

    st.session_state.parts = all_parts
    if all_parts:
        codes = list(dict.fromkeys(p['code'] for p in all_parts if p.get('code')))
        if codes:
            md = "**📋 Коды:**\n\n"
            for c in codes:
                sr = next((f"{p['source']} — {p['title']}" for p in all_parts if p.get('code') == c), '')
                md += f"`{c}` — {sr}\n\n"
            ph_codes.markdown(md)
    ph_status.markdown('<div class="status-line"><span class="status-dot"></span> ✅ Поиск завершён!</div>', unsafe_allow_html=True)

else:
    display_saved()
