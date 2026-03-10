import streamlit as st
import threading
import time
import re
import json
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Optional

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
# CONFIG
# ================================================================
st.set_page_config(
    page_title="VIN Decoder Pro",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ================================================================
# CUSTOM CSS
# ================================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700;800&family=Outfit:wght@300;400;600;700;800&display=swap');

/* Hide streamlit branding */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* Global */
.stApp {
    background: #0c0e14;
    font-family: 'Outfit', sans-serif;
}

/* Title */
.main-title {
    font-family: 'JetBrains Mono', monospace;
    font-weight: 800;
    font-size: 32px;
    letter-spacing: 3px;
    background: linear-gradient(135deg, #4f8cff, #a855f7);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    text-align: center;
    margin-bottom: 4px;
}
.subtitle {
    text-align: center;
    color: #6b7194;
    font-size: 13px;
    letter-spacing: 1px;
    margin-bottom: 20px;
}

/* Car cards */
.car-card {
    background: #141722;
    border: 1px solid #252a3a;
    border-radius: 12px;
    overflow: hidden;
    margin-bottom: 10px;
    transition: border-color 0.3s;
}
.car-card:hover { border-color: #6b7194; }

.car-header {
    padding: 8px 14px;
    font-family: 'JetBrains Mono', monospace;
    font-weight: 800;
    font-size: 11px;
    letter-spacing: 2px;
    text-transform: uppercase;
}
.car-header.autodoc { background: #0f1a2e; color: #4f8cff; }
.car-header.exist { background: #0f1e16; color: #2ecc71; }
.car-header.armtek { background: #1e170f; color: #f39c12; }
.car-header.partkom { background: #1a0f24; color: #a855f7; }

.car-body { padding: 14px; }
.car-name { font-weight: 700; font-size: 14px; color: #e4e7f1; margin-bottom: 4px; }
.car-model { font-family: 'JetBrains Mono', monospace; font-size: 11px; color: #6b7194; margin-bottom: 10px; }
.car-prop { display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 3px; }
.car-prop-label { color: #6b7194; }
.car-prop-value { font-weight: 600; color: #e4e7f1; }

.engine-box {
    background: #1a1e2e;
    border: 1px solid #252a3a;
    border-radius: 8px;
    padding: 10px;
    text-align: center;
    font-family: 'JetBrains Mono', monospace;
    font-weight: 800;
    font-size: 22px;
    color: #6b7194;
    margin-top: 10px;
}
.engine-box.found {
    background: rgba(231, 76, 60, 0.08);
    border-color: rgba(231, 76, 60, 0.3);
    color: #e74c3c;
    text-shadow: 0 0 20px rgba(231, 76, 60, 0.3);
}
.engine-box.error { color: #e74c3c; }
.engine-box.loading { color: #6b7194; font-size: 14px; font-weight: 400; }

/* Parts */
.part-card {
    background: #141722;
    border: 1px solid #252a3a;
    border-radius: 10px;
    overflow: hidden;
    margin-bottom: 8px;
}
.part-header {
    padding: 6px 14px;
    font-size: 11px;
    font-weight: 700;
    display: flex;
    justify-content: space-between;
}
.part-header.autodoc { background: #0f1a2e; color: #4f8cff; }
.part-header.elcats { background: #0f1e16; color: #2ecc71; }
.part-header.armtek { background: #1e170f; color: #f39c12; }

.part-body {
    padding: 12px 14px;
    display: flex;
    align-items: center;
    gap: 12px;
}
.part-code {
    font-family: 'JetBrains Mono', monospace;
    font-weight: 700;
    font-size: 15px;
    background: #1a1e2e;
    border: 1px solid #252a3a;
    padding: 6px 12px;
    border-radius: 6px;
    color: #e4e7f1;
    white-space: nowrap;
}
.part-desc { font-size: 12px; color: #6b7194; line-height: 1.4; }

/* Section title */
.section-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    letter-spacing: 2px;
    color: #6b7194;
    text-transform: uppercase;
    margin: 20px 0 14px;
}

/* Status */
.status-line {
    font-size: 12px;
    color: #6b7194;
    padding: 8px 0;
    display: flex;
    align-items: center;
    gap: 8px;
}
.status-dot {
    width: 6px; height: 6px;
    border-radius: 50%;
    background: #2ecc71;
    display: inline-block;
}
.status-dot.working { background: #f39c12; }

/* Input styling */
.stTextInput > div > div > input {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 18px !important;
    font-weight: 700 !important;
    letter-spacing: 2px !important;
    text-transform: uppercase !important;
    background: #141722 !important;
    border: 1px solid #252a3a !important;
    color: #e4e7f1 !important;
    border-radius: 10px !important;
}
.stTextInput > div > div > input:focus {
    border-color: #4f8cff !important;
    box-shadow: 0 0 0 3px rgba(79, 140, 255, 0.15) !important;
}

.stButton > button {
    background: linear-gradient(135deg, #4f8cff, #6366f1) !important;
    color: white !important;
    font-weight: 700 !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 10px 24px !important;
    font-size: 14px !important;
    width: 100% !important;
}
.stButton > button:hover {
    box-shadow: 0 6px 20px rgba(79, 140, 255, 0.4) !important;
}

/* Hide label for text input */
.stTextInput label { display: none !important; }
</style>
""", unsafe_allow_html=True)


# ================================================================
# SELENIUM BROWSER HELPER
# ================================================================

def create_driver():
    """Create a headless Chrome/Chromium driver for Streamlit Cloud."""
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--lang=ru-RU')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')
    
    # For Streamlit Cloud (Debian-based)
    options.binary_location = "/usr/bin/chromium"
    
    try:
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=options)
    except Exception:
        # Fallback — try system default
        try:
            driver = webdriver.Chrome(options=options)
        except Exception:
            # Last resort — try with chromium-browser
            options.binary_location = "/usr/bin/chromium-browser"
            driver = webdriver.Chrome(options=options)
    
    # Stealth
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "delete Object.getPrototypeOf(navigator).webdriver; window.chrome = { runtime: {} };"
    })
    
    driver.set_page_load_timeout(30)
    driver.implicitly_wait(2)
    return driver


def safe_find_text(driver, css, default="-"):
    """Safely find element text."""
    try:
        el = driver.find_element(By.CSS_SELECTOR, css)
        return el.text.strip()
    except:
        return default


def wait_and_find(driver, css, timeout=10):
    """Wait for element and return it."""
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, css))
    )


# ================================================================
# SITE SCRAPERS — VEHICLE INFO
# ================================================================

def get_autodoc_details(vin: str) -> dict:
    data = {'car_name': None, 'model_code': None, 'date': None, 'engine': None, 'drive': None, 'error': False}
    driver = None
    try:
        driver = create_driver()
        driver.get("https://www.autodoc.ru/")
        
        search_box = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='search'], input.search-input"))
        )
        search_box.clear()
        search_box.send_keys(vin)
        
        search_btn = driver.find_element(By.CSS_SELECTOR, "button.search-button")
        search_btn.click()
        
        try:
            h1 = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "h1.catalog-originals-heading"))
            )
            raw_title = h1.text.replace("Запчасти для", "").strip()
            parts = raw_title.split()
            data['car_name'] = " ".join(parts[:-1]) if len(parts) > 1 else raw_title
        except TimeoutException:
            data['error'] = True
            return data
        
        try:
            params_btn = driver.find_element(By.CSS_SELECTOR, 'tui-icon[title="Параметры автомобиля"]')
            params_btn.click()
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.dialog-car-attributes__item'))
            )
            
            items = driver.find_elements(By.CSS_SELECTOR, '.dialog-car-attributes__item')
            for item in items:
                try:
                    name = item.find_element(By.CSS_SELECTOR, '.dialog-car-attributes__item-name').text
                    val = item.find_element(By.CSS_SELECTOR, '.dialog-car-attributes__item-value').text.strip()
                    
                    if "Номер двигателя" in name:
                        data['engine'] = val[:4].upper()
                    elif "Дата выпуска" in name:
                        data['date'] = val
                    elif "Модель" in name and "год" not in name.lower():
                        data['model_code'] = val
                    elif "Опции" in name:
                        try:
                            show_more = item.find_element(By.CSS_SELECTOR, '.dialog-car-attributes__item_show-more')
                            if show_more.is_displayed():
                                show_more.click()
                                time.sleep(0.5)
                        except:
                            pass
                        opt = item.find_element(By.CSS_SELECTOR, '.dialog-car-attributes__item-value').text.upper()
                        if "4WD" in opt:
                            data['drive'] = "4WD (Полный)"
                        elif "2WD" in opt:
                            data['drive'] = "2WD (Передний)"
                except:
                    continue
        except:
            pass
    except Exception as e:
        data['error'] = True
    finally:
        if driver:
            driver.quit()
    return data


def get_exist_details(vin: str) -> dict:
    data = {'car_name': None, 'model_code': None, 'date': None, 'engine': None, 'drive': None, 'error': False}
    driver = None
    try:
        driver = create_driver()
        driver.get(f"https://exist.ru/Price/Empty.aspx?q={vin}")
        
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '.car-info'))
        )
        
        data['car_name'] = safe_find_text(driver, '.car-info__car-name', None)
        data['date'] = safe_find_text(driver, '.car-info__car-years', None)
        
        if data['car_name']:
            nu = data['car_name'].upper()
            if "4WD" in nu or "AWD" in nu:
                data['drive'] = "4WD (Полный)"
            elif "2WD" in nu:
                data['drive'] = "2WD (Передний)"
            
            m = re.search(r'\(([A-Z0-9]{4,5})\)', data['car_name'])
            if m:
                data['engine'] = m.group(1)
        
        if not data['drive']:
            try:
                txt = driver.find_element(By.CSS_SELECTOR, '.car-info').text
                md = re.search(r'Transaxle:\s*([A-Z0-9\s-]+?)(?:\s*\||$)', txt)
                if md:
                    d = md.group(1).strip()
                    if "2WD" in d:
                        data['drive'] = "2WD (Передний)"
                    elif "4WD" in d:
                        data['drive'] = "4WD (Полный)"
                    else:
                        data['drive'] = d
            except:
                pass
    except:
        data['error'] = True
    finally:
        if driver:
            driver.quit()
    return data


def get_armtek_details(vin: str) -> dict:
    data = {'car_name': None, 'model_code': None, 'date': None, 'engine': None, 'drive': None, 'error': False}
    driver = None
    try:
        driver = create_driver()
        driver.get(f"https://armtek.ru/search?text={vin}")
        
        # Kill banners via JS
        driver.execute_script("""
            const obs = new MutationObserver(() => {
                document.querySelectorAll('.cdk-overlay-container, project-ui-geo-dialog').forEach(e => e.remove());
            });
            obs.observe(document.body, {childList: true, subtree: true});
            document.querySelectorAll('.cdk-overlay-container, project-ui-geo-dialog').forEach(e => e.remove());
        """)
        
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.car__header"))
        )
        
        # Expand details
        try:
            headers = driver.find_elements(By.CSS_SELECTOR, 'mat-expansion-panel-header')
            if headers:
                h = headers[0]
                cls = h.get_attribute('class') or ''
                if 'mat-expanded' not in cls and h.is_displayed():
                    h.click()
                    time.sleep(1)
        except:
            pass
        
        info_items = driver.find_elements(By.CSS_SELECTOR, 'div.car__main-information-item')
        for item in info_items:
            try:
                t = item.find_element(By.CSS_SELECTOR, 'p.car__main-information-item-title').text.strip()
                v = item.find_element(By.CSS_SELECTOR, 'p.font__body2').text.strip()
                
                if "Модель" in t and "год" not in t.lower():
                    data['model_code'] = v
                elif "Дата выпуска" in t:
                    data['date'] = v
                elif "Номер двигателя" in t:
                    data['engine'] = v[:4].upper()
                elif "Опции" in t:
                    if "4WD" in v:
                        data['drive'] = "4WD (Полный)"
                    elif "2WD" in v:
                        data['drive'] = "2WD (Передний)"
            except:
                continue
        
        try:
            tel = driver.find_element(By.CSS_SELECTOR, 'div.car__header-info-title p')
            if tel.is_displayed():
                data['car_name'] = tel.text.strip()
        except:
            pass
    except:
        data['error'] = True
    finally:
        if driver:
            driver.quit()
    return data


def get_partkom_details(vin: str) -> dict:
    data = {'car_name': None, 'model_code': None, 'date': None, 'engine': None, 'drive': None, 'error': False}
    driver = None
    try:
        driver = create_driver()
        driver.get(f"https://part-kom.ru/catalog-vin?vin={vin}")
        
        iframe_elem = None
        found = False
        
        for _ in range(100):
            # Close popups
            try:
                driver.execute_script("""
                    document.querySelectorAll('button').forEach(b => { 
                        if(b.innerText.includes('Да, верно') || b.ariaLabel==='закрыть') b.click(); 
                    })
                """)
            except:
                pass
            
            if not iframe_elem:
                try:
                    iframes = driver.find_elements(By.CSS_SELECTOR, 'iframe[src*="b2b.part-kom.ru"]')
                    if iframes:
                        iframe_elem = iframes[0]
                        driver.switch_to.frame(iframe_elem)
                except:
                    pass
            
            if iframe_elem:
                try:
                    # Try to expand
                    try:
                        expand_btns = driver.find_elements(By.XPATH, "//button[contains(text(), 'Все параметры')]")
                        if expand_btns and expand_btns[0].is_displayed():
                            expand_btns[0].click()
                            time.sleep(0.5)
                    except:
                        pass
                    
                    params = driver.find_elements(By.CSS_SELECTOR, 
                        'div[class*="grouped-cars-list-group__parameter"], li[class*="cars-list-item-mobile__parameter"]')
                    
                    if params:
                        try:
                            titles = driver.find_elements(By.CSS_SELECTOR, 
                                'div[class*="grouped-cars-list-group__title"], div[class*="cars-list-item-mobile__brand"]')
                            if titles:
                                data['car_name'] = titles[0].text.strip()
                        except:
                            pass
                        
                        for p_item in params:
                            divs = p_item.find_elements(By.TAG_NAME, 'div')
                            if len(divs) >= 2:
                                k = divs[0].text.strip()
                                v = divs[1].text.strip()
                                if "Год" in k:
                                    data['date'] = v
                                elif "Код двигателя" in k:
                                    data['engine'] = v[:4].upper() if len(v) > 4 else v
                                elif "Transaxle" in k:
                                    if "4WD" in v:
                                        data['drive'] = "4WD (Полный)"
                                    elif "2WD" in v:
                                        data['drive'] = "2WD (Передний)"
                        found = True
                        break
                except:
                    pass
            
            time.sleep(0.15)
        
        if not found:
            data['error'] = True
    except:
        data['error'] = True
    finally:
        if driver:
            try:
                driver.switch_to.default_content()
            except:
                pass
            driver.quit()
    return data


# ================================================================
# PARTS SCRAPERS
# ================================================================

def get_elcats_parts(vin: str, mode: str, part_type: str, title: str) -> list:
    """Scrape parts from Elcats."""
    # Config
    cfg = {
        'G4NA_intake':    {'group_kw': 'РАСПРЕДЕЛИТЕЛЬНЫЙ ВАЛ И КЛАПАН', 'node_descr': 'РАСПРЕДВАЛ В СБОРЕ-ВПУСКНОЙ'},
        'G4NA_exhaust':   {'group_kw': 'РАСПРЕДЕЛИТЕЛЬНЫЙ ВАЛ И КЛАПАН', 'node_descr': 'РАСПРЕДЕЛИТЕЛЬНЫЙ ВАЛ В СБОРЕ-ВЫХЛОПНОЙ'},
        'G4KE_cover':     {'group_kw': 'КРЫШКА РЕМНЯ И МАСЛЯНЫЙ ПОДДОН', 'node_descr': 'КРЫШКА В СБОРЕ-ПРИВОДНАЯ ЦЕПЬ'},
        'G4KE_bracket':   {'group_kw': 'КРЕПЛЕНИЯ ДВИГАТЕЛЯ И ТРАНСМИССИИ', 'node_descr': 'КРОНШТЕЙН В СБОРЕ-ОПОРА ДВИГАТЕЛЯ'},
        'G4KJ_cover':     {'group_kw': 'КРЫШКА РЕМНЯ И МАСЛЯНЫЙ ПОДДОН', 'node_descr': 'КРЫШКА В СБОРЕ-ПРИВОДНАЯ ЦЕПЬ'},
        'G4KJ_bracket':   {'group_kw': 'КРЕПЛЕНИЯ ДВИГАТЕЛЯ И ТРАНСМИССИИ', 'node_descr': 'КРОНШТЕЙН В СБОРЕ-ОПОРА ДВИГАТЕЛЯ'},
        'G4KH_cover':     {'group_kw': 'КРЫШКА РЕМНЯ И МАСЛЯНЫЙ ПОДДОН', 'node_descr': 'КРЫШКА В СБОРЕ-ПРИВОДНАЯ ЦЕПЬ'},
        'G4KH_bracket':   {'group_kw': 'КРЕПЛЕНИЯ ДВИГАТЕЛЯ И ТРАНСМИССИИ', 'node_descr': 'КРОНШТЕЙН В СБОРЕ-ОПОРА ДВИГАТЕЛЯ'},
    }
    
    key = f"{mode}_{part_type}"
    conf = cfg.get(key)
    if not conf:
        return []
    
    group_kw = conf['group_kw']
    node_descr = conf['node_descr']
    items = []
    driver = None
    
    try:
        driver = create_driver()
        driver.get(f"https://www.elcats.ru/hyundai/default.aspx?carvin={vin}")
        time.sleep(3)
        
        if "default.aspx" in driver.current_url.lower():
            try:
                vin_input = driver.find_element(By.ID, 'ctl00_cphMasterPage_txbVIN')
                vin_input.clear()
                vin_input.send_keys(vin)
            except:
                vin_input = driver.find_element(By.CSS_SELECTOR, 'input[type=text]')
                vin_input.clear()
                vin_input.send_keys(vin)
            
            time.sleep(0.3)
            driver.find_element(By.ID, 'ctl00_cphMasterPage_btnFindByVIN').click()
            time.sleep(3)
        
        m = re.search(r'Model=([a-f0-9\-]{36})', driver.current_url, re.I)
        if not m:
            return items
        
        model_uuid = m.group(1)
        
        # Find group ID
        group_id = driver.execute_script(f"""
            var links = document.querySelectorAll('a[href^="javascript:submit"]');
            for (var i = 0; i < links.length; i++) {{
                if (links[i].textContent.toUpperCase().indexOf("{group_kw.upper()}") !== -1) {{
                    var match = links[i].getAttribute('href').match(/submit\\('([^']+)'/);
                    if (match) return match[1];
                }}
            }}
            return null;
        """)
        
        if not group_id:
            return items
        
        encoded_title = urllib.parse.quote(group_kw)
        driver.get(f"https://www.elcats.ru/hyundai/Unit.aspx?GroupId={group_id}&Model={model_uuid}&Title={encoded_title}")
        time.sleep(3)
        
        # Find CNode
        cnode_ids = driver.execute_script(f"""
            var nodes = document.querySelectorAll('div.CNode');
            var res = [];
            nodes.forEach(function(n) {{
                var s = n.querySelector('span.descr-ru');
                if(s && s.textContent.toUpperCase().indexOf("{node_descr.upper()}") !== -1)
                    res.push(n.getAttribute('id'));
            }});
            return res;
        """)
        
        seen = set()
        for cid in cnode_ids:
            try:
                driver.find_element(By.ID, cid).click()
                time.sleep(4)
                
                parts_data = driver.execute_script("""
                    var res = [];
                    document.querySelectorAll('table.OpelParts tr').forEach(function(row, i) {
                        if(i === 0) return;
                        var tds = row.querySelectorAll('td');
                        if(tds.length < 2) return;
                        var a = tds[0].querySelector('a');
                        var code = (a ? a.textContent : tds[0].textContent).replace(/\\s+/g, ' ').trim();
                        var span = tds[1].querySelector('span.descr-ru');
                        var descr = (span ? span.textContent : tds[1].textContent).replace(/\\s+/g, ' ').trim();
                        var period = tds.length > 3 ? tds[3].textContent.replace(/\\s+/g, ' ').trim() : "";
                        var info = tds.length > 4 ? tds[4].textContent.replace(/\\s+/g, ' ').trim() : "";
                        if(code.length > 3) res.push({code: code, descr: descr, period: period, info: info});
                    });
                    return res;
                """)
                
                for pt in parts_data:
                    if pt['code'] not in seen:
                        seen.add(pt['code'])
                        fdesc = pt['descr']
                        if pt.get('period'):
                            fdesc += f" [{pt['period']}]"
                        if pt.get('info'):
                            fdesc += f" ({pt['info']})"
                        items.append({'source': 'ELCATS', 'title': title, 'desc': fdesc, 'code': pt['code']})
            except:
                continue
    except:
        pass
    finally:
        if driver:
            driver.quit()
    
    return items


def get_armtek_parts(vin: str, mode: str, part_type: str, title: str) -> list:
    """Scrape parts from Armtek."""
    cfg = {
        'G4NA_intake':    {'q': 'распредвал впускной',       'kw': 'впускной',   'ignore': []},
        'G4NA_exhaust':   {'q': 'распредвал выпускной',      'kw': 'выпускной',  'ignore': []},
        'G4KE_cover':     {'q': 'КОЖУХ В СБОРЕ-ЦЕПЬ ГРМ',   'kw': 'кожух',      'ignore': []},
        'G4KE_bracket':   {'q': 'кронштейн двигателя',       'kw': 'кронштейн',  'ignore': ['двигатель уст', 'опора', 'подвеска']},
        'G4KJ_cover':     {'q': 'КОЖУХ В СБОРЕ-ЦЕПЬ ГРМ',   'kw': 'кожух',      'ignore': []},
        'G4KJ_bracket':   {'q': 'кронштейн двигателя',       'kw': 'кронштейн',  'ignore': ['двигатель уст', 'опора', 'подвеска']},
        'G4KH_cover':     {'q': 'КОЖУХ В СБОРЕ-ЦЕПЬ ГРМ',   'kw': 'кожух',      'ignore': []},
        'G4KH_bracket':   {'q': 'кронштейн двигателя',       'kw': 'кронштейн',  'ignore': ['двигатель уст', 'опора', 'подвеска']},
    }
    
    key = f"{mode}_{part_type}"
    conf = cfg.get(key)
    if not conf:
        return []
    
    items = []
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
        
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.car__header"))
        )
        
        inp = WebDriverWait(driver, 15).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, 'input[placeholder="Наименование запчасти"]'))
        )
        
        inp.click()
        inp.send_keys(Keys.CONTROL + "a")
        inp.send_keys(Keys.DELETE)
        time.sleep(0.5)
        inp.send_keys(conf['q'])
        time.sleep(0.5)
        inp.send_keys(Keys.ENTER)
        time.sleep(3)
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.part"))
        )
        
        parts = driver.execute_script(f"""
            var res = []; var seen = {{}};
            document.querySelectorAll('div.part').forEach(function(p) {{
                var nm = p.querySelector('div.title-name');
                var oem = p.querySelector('div.oem');
                if (!nm || !oem) return;
                var name = nm.textContent.trim(); var code = oem.textContent.trim();
                if (code.length < 4 || seen[code]) return;
                seen[code] = true;
                res.push({{name: name, code: code, match: name.toLowerCase().includes("{conf['kw'].lower()}")}});
            }});
            return res;
        """)
        
        for pt in parts:
            if any(ign.lower() in pt['name'].lower() for ign in conf['ignore']):
                continue
            if pt['match']:
                items.append({'source': 'ARMTEK', 'title': title, 'desc': pt['name'], 'code': pt['code']})
        
        if not items and parts:
            for pt in parts:
                if any(ign.lower() in pt['name'].lower() for ign in conf['ignore']):
                    continue
                items.append({'source': 'ARMTEK', 'title': title, 'desc': pt['name'], 'code': pt['code']})
                break
    except:
        pass
    finally:
        if driver:
            driver.quit()
    
    return items


def get_autodoc_parts(vin: str, mode: str, part_type: str, title: str) -> list:
    """Scrape parts from Autodoc."""
    cfg = {
        'G4NA_intake':  {'path': ['Двигатель', 'Механизм газораспределения'], 'part_kws': ['распредвал', 'впуск'], 'code_prefix': None},
        'G4NA_exhaust': {'path': ['Двигатель', 'Механизм газораспределения'], 'part_kws': ['распредвал', 'выпуск'], 'code_prefix': None},
        'G4KE_cover':   {'path': ['Двигатель', 'Блок-картер'],               'part_kws': None, 'code_prefix': '21350'},
        'G4KE_bracket': {'path': ['Двигатель', 'Крепление двигателя'],        'part_kws': None, 'code_prefix': '21670'},
        'G4KJ_cover':   {'path': ['Двигатель', 'Блок-картер'],               'part_kws': None, 'code_prefix': '21350'},
        'G4KJ_bracket': {'path': ['Двигатель', 'Крепление двигателя'],        'part_kws': None, 'code_prefix': '21670'},
        'G4KH_cover':   {'path': ['Двигатель', 'Блок-картер'],               'part_kws': None, 'code_prefix': '21350'},
        'G4KH_bracket': {'path': ['Двигатель', 'Крепление двигателя'],        'part_kws': None, 'code_prefix': '21670'},
    }
    
    key = f"{mode}_{part_type}"
    conf = cfg.get(key)
    if not conf:
        return []
    
    items = []
    driver = None
    
    try:
        driver = create_driver()
        driver.get("https://www.autodoc.ru/")
        
        search_box = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='search'], input.search-input"))
        )
        search_box.clear()
        search_box.send_keys(vin)
        driver.find_element(By.CSS_SELECTOR, "button.search-button").click()
        time.sleep(3)
        
        # Navigate catalog
        for step in conf['path']:
            try:
                nodes = driver.find_elements(By.CSS_SELECTOR, "p.catalog-node__name")
                for n in nodes:
                    if step.lower() in n.text.lower():
                        n.click()
                        time.sleep(1)
                        break
            except:
                pass
        
        time.sleep(2)
        
        # Find goods
        goods = driver.find_elements(By.CSS_SELECTOR, '.goods__item')
        for g in goods:
            try:
                txt = g.text.lower()
                match = False
                if conf['part_kws'] and all(w in txt for w in conf['part_kws']):
                    match = True
                if conf['code_prefix'] and conf['code_prefix'] in txt:
                    match = True
                
                if match:
                    link = g.find_element(By.CSS_SELECTOR, 'a.goods__item-link')
                    href = link.get_attribute('href')
                    driver.get(href)
                    
                    try:
                        WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, '.properties__description-text'))
                        )
                        desc = driver.find_element(By.CSS_SELECTOR, '.properties__description-text').text
                        code_match = re.search(r'([A-Z0-9]{5,20})$', desc.strip())
                        items.append({
                            'source': 'AUTODOC',
                            'title': title,
                            'desc': desc,
                            'code': code_match.group(1) if code_match else None
                        })
                    except:
                        pass
                    break
            except:
                continue
    except:
        pass
    finally:
        if driver:
            driver.quit()
    
    return items


# ================================================================
# RENDER HELPERS
# ================================================================

def render_car_card(site_key: str, site_title: str, data: dict):
    """Render a car card as HTML."""
    if data is None:
        # Loading state
        return f"""
        <div class="car-card">
            <div class="car-header {site_key}">{site_title}</div>
            <div class="car-body">
                <div class="car-name" style="color: #6b7194;">Ожидание...</div>
                <div class="car-model">&nbsp;</div>
                <div class="car-prop"><span class="car-prop-label">Дата:</span><span class="car-prop-value">-</span></div>
                <div class="car-prop"><span class="car-prop-label">Привод:</span><span class="car-prop-value">-</span></div>
                <div class="engine-box">---</div>
            </div>
        </div>
        """
    
    if data.get('error'):
        return f"""
        <div class="car-card">
            <div class="car-header {site_key}">{site_title}</div>
            <div class="car-body">
                <div class="car-name" style="color: #e74c3c;">НЕ НАЙДЕНО</div>
                <div class="car-model">&nbsp;</div>
                <div class="car-prop"><span class="car-prop-label">Дата:</span><span class="car-prop-value">-</span></div>
                <div class="car-prop"><span class="car-prop-label">Привод:</span><span class="car-prop-value">-</span></div>
                <div class="engine-box error">---</div>
            </div>
        </div>
        """
    
    engine = data.get('engine', '')
    engine_class = 'found' if engine else 'error'
    engine_text = engine if engine else 'НЕТ ДАННЫХ'
    
    return f"""
    <div class="car-card">
        <div class="car-header {site_key}">{site_title}</div>
        <div class="car-body">
            <div class="car-name">{data.get('car_name') or 'Неизвестно'}</div>
            <div class="car-model">{data.get('model_code') or ''}</div>
            <div class="car-prop"><span class="car-prop-label">Дата:</span><span class="car-prop-value">{data.get('date') or '-'}</span></div>
            <div class="car-prop"><span class="car-prop-label">Привод:</span><span class="car-prop-value">{data.get('drive') or '-'}</span></div>
            <div class="engine-box {engine_class}">{engine_text}</div>
        </div>
    </div>
    """


def render_part_card(item: dict) -> str:
    source = item.get('source', '').lower()
    src_class = source if source in ('autodoc', 'elcats', 'armtek') else ''
    
    code_html = ""
    if item.get('code'):
        code_html = f'<span class="part-code">📋 {item["code"]}</span>'
    
    return f"""
    <div class="part-card">
        <div class="part-header {src_class}">
            <span>{item.get('title', '')}</span>
            <span>{item.get('source', '')}</span>
        </div>
        <div class="part-body">
            {code_html}
            <span class="part-desc">{item.get('desc', '')}</span>
        </div>
    </div>
    """


# ================================================================
# MAIN APP
# ================================================================

# Session state init
if 'results' not in st.session_state:
    st.session_state.results = {}
if 'parts' not in st.session_state:
    st.session_state.parts = []
if 'engine_model' not in st.session_state:
    st.session_state.engine_model = ''
if 'searching' not in st.session_state:
    st.session_state.searching = False
if 'parts_searching' not in st.session_state:
    st.session_state.parts_searching = False
if 'vin' not in st.session_state:
    st.session_state.vin = ''

# Title
st.markdown('<div class="main-title">VIN DECODER PRO</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Поиск по 4 источникам • Автоопределение двигателя • Поиск запчастей</div>', unsafe_allow_html=True)

# Search bar
col_input, col_btn = st.columns([3, 1])
with col_input:
    vin_input = st.text_input("VIN", value=st.session_state.vin, max_chars=17, 
                               placeholder="Введите VIN (17 символов)",
                               key="vin_field")
with col_btn:
    st.markdown("<div style='height: 28px'></div>", unsafe_allow_html=True)  # spacer
    search_clicked = st.button("🔍 ИСКАТЬ ДВС", disabled=st.session_state.searching, use_container_width=True)


# ================================================================
# SEARCH LOGIC
# ================================================================

def run_vehicle_search(vin: str):
    """Run parallel vehicle info scraping."""
    results = {}
    
    site_funcs = {
        'autodoc': get_autodoc_details,
        'exist': get_exist_details,
        'armtek': get_armtek_details,
        'partkom': get_partkom_details,
    }
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {}
        for site, func in site_funcs.items():
            futures[executor.submit(func, vin)] = site
        
        for future in as_completed(futures):
            site = futures[future]
            try:
                results[site] = future.result()
            except:
                results[site] = {'error': True}
    
    return results


def run_parts_search(vin: str, mode: str):
    """Run parallel parts search."""
    all_parts = []
    
    if mode == 'G4NA':
        tasks = [
            ('autodoc', 'G4NA', 'intake', 'Распредвал Впуск'),
            ('autodoc', 'G4NA', 'exhaust', 'Распредвал Выпуск'),
            ('elcats', 'G4NA', 'intake', 'Распредвал Впуск'),
            ('elcats', 'G4NA', 'exhaust', 'Распредвал Выпуск'),
            ('armtek', 'G4NA', 'intake', 'Распредвал Впуск'),
            ('armtek', 'G4NA', 'exhaust', 'Распредвал Выпуск'),
        ]
    elif mode in ['G4KE', 'G4KJ', 'G4KH']:
        tasks = [
            ('autodoc', mode, 'cover', 'Лобная крышка'),
            ('autodoc', mode, 'bracket', 'Кронштейн'),
            ('elcats', mode, 'cover', 'Лобная крышка'),
            ('elcats', mode, 'bracket', 'Кронштейн'),
            ('armtek', mode, 'cover', 'Лобная крышка'),
            ('armtek', mode, 'bracket', 'Кронштейн'),
        ]
    else:
        return []
    
    site_func_map = {
        'autodoc': get_autodoc_parts,
        'elcats': get_elcats_parts,
        'armtek': get_armtek_parts,
    }
    
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = []
        for site, m, pt, title in tasks:
            func = site_func_map[site]
            futures.append(executor.submit(func, vin, m, pt, title))
        
        for future in as_completed(futures):
            try:
                result = future.result()
                if result:
                    all_parts.extend(result)
            except:
                pass
    
    return all_parts


if search_clicked:
    vin = vin_input.strip().upper()
    if len(vin) != 17:
        st.error("⚠️ VIN должен быть ровно 17 символов!")
    else:
        st.session_state.vin = vin
        st.session_state.searching = True
        st.session_state.results = {}
        st.session_state.parts = []
        st.session_state.engine_model = ''
        
        # Phase 1: Vehicle info
        with st.spinner("🔍 Поиск информации об авто в 4 источниках..."):
            results = run_vehicle_search(vin)
            st.session_state.results = results
        
        # Determine engine
        engine_model = ''
        for site_data in results.values():
            if site_data and not site_data.get('error'):
                eng = site_data.get('engine', '')
                if eng:
                    for m in ['G4NA', 'G4KE', 'G4KJ', 'G4KH']:
                        if m in eng:
                            engine_model = m
                            break
                if engine_model:
                    break
        
        st.session_state.engine_model = engine_model
        
        # Phase 2: Parts search
        if engine_model:
            with st.spinner(f"⚙️ Поиск запчастей для {engine_model}..."):
                parts = run_parts_search(vin, engine_model)
                st.session_state.parts = parts
                st.session_state.parts_searching = False
        
        st.session_state.searching = False
        st.rerun()


# ================================================================
# DISPLAY RESULTS
# ================================================================

results = st.session_state.results

# Car cards grid (2 columns)
col1, col2 = st.columns(2)

with col1:
    st.markdown(render_car_card('autodoc', 'AUTODOC', results.get('autodoc')), unsafe_allow_html=True)
    st.markdown(render_car_card('armtek', 'ARMTEK', results.get('armtek')), unsafe_allow_html=True)

with col2:
    st.markdown(render_car_card('exist', 'EXIST / ELCATS', results.get('exist')), unsafe_allow_html=True)
    st.markdown(render_car_card('partkom', 'PART-KOM', results.get('partkom')), unsafe_allow_html=True)

# Engine summary
if results:
    engines_found = []
    for site_data in results.values():
        if site_data and not site_data.get('error') and site_data.get('engine'):
            engines_found.append(site_data['engine'])
    
    if engines_found:
        engine_text = " / ".join(set(engines_found))
        if st.session_state.engine_model:
            st.success(f"🔧 Определён двигатель: **{engine_text}** → Автопоиск запчастей для **{st.session_state.engine_model}**")
        else:
            st.info(f"🔧 Двигатель: **{engine_text}** (автопоиск запчастей не требуется)")

# Separator + parts
st.markdown('<div class="section-title">НАЙДЕННЫЕ ЗАПЧАСТИ</div>', unsafe_allow_html=True)

parts = st.session_state.parts
if parts:
    # Group by title
    for item in parts:
        st.markdown(render_part_card(item), unsafe_allow_html=True)
    
    # Copy buttons
    st.markdown("---")
    st.markdown("**📋 Коды для копирования:**")
    codes = [p['code'] for p in parts if p.get('code')]
    unique_codes = list(dict.fromkeys(codes))  # preserve order, remove dupes
    
    for code in unique_codes:
        source_info = next((f"{p['source']} — {p['title']}" for p in parts if p.get('code') == code), '')
        st.code(code, language=None)
        st.caption(source_info)
else:
    if results:
        st.markdown(
            '<div style="text-align:center; color:#6b7194; padding:30px; font-size:13px;">'
            'Запчасти не найдены или двигатель не из списка G4NA/G4KE/G4KJ/G4KH</div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            '<div style="text-align:center; color:#6b7194; padding:30px; font-size:13px;">'
            'Введите VIN и нажмите "ИСКАТЬ ДВС"</div>',
            unsafe_allow_html=True
        )

# Manual parts search button
if results and not st.session_state.engine_model:
    st.markdown("---")
    st.markdown("**Ручной поиск запчастей:**")
    manual_mode = st.selectbox("Выберите двигатель", ["G4NA", "G4KE", "G4KJ", "G4KH"])
    if st.button(f"🔍 Искать запчасти для {manual_mode}"):
        with st.spinner(f"⚙️ Поиск запчастей для {manual_mode}..."):
            parts = run_parts_search(st.session_state.vin, manual_mode)
            st.session_state.parts = parts
            st.session_state.engine_model = manual_mode
        st.rerun()

# Status bar
if st.session_state.searching:
    st.markdown('<div class="status-line"><span class="status-dot working"></span> Идёт поиск...</div>', unsafe_allow_html=True)
elif results:
    st.markdown('<div class="status-line"><span class="status-dot"></span> Поиск завершён</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="status-line"><span class="status-dot"></span> Ожидание ввода...</div>', unsafe_allow_html=True)
