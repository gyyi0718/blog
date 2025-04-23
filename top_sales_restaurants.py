import pyautogui
import time
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import ctypes
import requests
import json
import pandas as pd
import pyperclip
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
import ctypes
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
# DPI 비율 보정
ctypes.windll.user32.SetProcessDPIAware()

click_x = 1100
click_y = 830
# 1) Selenium으로 브라우저 켜서 팝업 닫기
options = Options()
options.add_argument("--start-maximized")
driver = webdriver.Chrome(options=options)
driver.get("https://www.openub.com/")
time.sleep(5)

# 팝업 닫기 (pyautogui 좌표는 환경에 맞게 조정하세요)
pyautogui.moveTo(click_x, click_y, duration=0.2)
pyautogui.click()
time.sleep(1)

###########################################

# — 실제 개발자도구에서 복사한 헤더를 최대한 그대로 사용합니다.
HEADERS = {
    "accept": "*/*",
    "accept-language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "content-type": "application/json",
    "access-token": "70a75f44-2b2d-4cf0-b915-728c59969e3e",
    "origin": "https://www.openub.com",
    "referer": "https://www.openub.com/",
    "priority": "u=1, i",
    "sec-ch-ua": "\"Google Chrome\";v=\"135\", \"Not-A.Brand\";v=\"8\", \"Chromium\";v=\"135\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"Windows\"",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/135.0.7049.96 Safari/537.36"
}

def get_rdnu(x: float, y: float, zoom: int = 16, category: str = "A0:B0:C0:D0:E0:F0:G0"):
    url = "https://api.openub.com/v2/coord"
    payload = {
        "x": x,
        "y": y,
        "zoom": zoom,
        "category": category,
        "limit": 1
    }
    resp = requests.post(url, headers=HEADERS, json=payload)
    resp.raise_for_status()
    buildings = resp.json().get("buildings", [])
    if not buildings:
        raise RuntimeError("해당 좌표 근처에 건물을 찾을 수 없습니다.")
    return buildings[0]["rdnu"]

def get_sales(rdnu: str, category: str = "A0:B0:C0:D0:F0:G0", login: bool = True):
    url = "https://api.openub.com/v2/bd/sales"
    payload = {
        "rdnu": rdnu,
        "category": category,
        "login": login
    }
    resp = requests.post(url, headers=HEADERS, json=payload)
    if resp.status_code == 401:
        print("❌ 401 Unauthorized - 액세스 토큰이 만료되었거나 잘못되었습니다.")
        print("응답 본문:", resp.text)
        resp.raise_for_status()
    resp.raise_for_status()
    result = resp.json().get("result", {})
    return {
        "monthSales": result.get("monthSales"),
        "times":       result.get("times", [])
    }
# 2) 검색 아이콘 클릭 (좌표 예: x=100, y=60)
pyautogui.moveTo(150, 170, duration=0.2)
pyautogui.click()

# 2) 클립보드에 "강남역" 복사
pyperclip.copy("강남역")
# 3) Ctrl+V 로 붙여넣기
pyautogui.hotkey("ctrl", "v")
time.sleep(2)

# 2) 검색 아이콘 클릭 (좌표 예: x=100, y=60)
pyautogui.moveTo(150, 260, duration=0.2)
pyautogui.click()

# 5) 검색어 입력 직후 제안목록 뜰 때까지 잠시 대기
time.sleep(1)

# 6) 키보드로 첫 번째 항목 선택 → 엔터
pyautogui.press("down")
time.sleep(0.1)
pyautogui.press("enter")

# 7) 지도 이동 대기
time.sleep(3)
session = requests.Session()
for ck in driver.get_cookies():
    session.cookies.set(ck["name"], ck["value"])
session.headers.update({
    "Origin":      "https://www.openub.com",
    "Referer":     "https://www.openub.com/",
    "User-Agent":  "Mozilla/5.0",
    "Content-Type":"application/json",
})
# 지도 로딩 후 바로 여러 위치 반복 클릭
map_area = driver.find_element(By.ID, "map")
sales_url = "https://api.openup.com/v2/bd/sales"

actions = ActionChains(driver)
store_results = []
for dx in range(300, 601, 100):  # x축 반복
    for dy in range(250, 501, 100):  # y축 반복
        actions.move_to_element_with_offset(map_area, dx, dy).click().perform()
        time.sleep(2)

        # 추정 매출 텍스트 추출
        elements = driver.find_elements(By.XPATH, "//*[contains(text(), '억') or contains(text(), '원')]")
        print()
        print(f"🧭 클릭 위치: ({dx},{dy})")
        popupOuter = driver.find_element(By.CSS_SELECTOR, "div.z-1.hover\\:z-4")

        try:
            popup = driver.find_element(By.CSS_SELECTOR, "div.icon-total-popup")
            # 3) 매출 텍스트 (첫 번째 <p>)
            sales_txt = popup.find_element(By.CSS_SELECTOR, "p.font-14-14").text
            # 4) 점포 개수 (두 번째 <p>)
            store_count = popup.find_element(By.CSS_SELECTOR, "p.font-12-12").text

            print(f"🧭 클릭 위치 → 매출: {sales_txt}, 점포 수: {store_count}")

            test1 = driver.find_element(By.CSS_SELECTOR, "div.tab-market-list")

            test2 = driver.find_element(By.CSS_SELECTOR, "div.ol-overlaycontainer")
            test3 = driver.find_element(By.CSS_SELECTOR, "div.pos-rel")
            # 4) 점포 개수 (두 번째 <p>)
            test4 = driver.find_element(By.CSS_SELECTOR, "div.pos-abs")
            store_items = popupOuter.find_elements(By.CSS_SELECTOR, "div.store-item")

            first_store_marker = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".icon-total-popup"))
            )
            first_store_marker.click()
            # 패널 애니메이션 대기
            time.sleep(1)

            # 1) 엔드포인트
            rdnu = get_rdnu(127.0276	, 37.4979)
            print("🏢 rdnu:", rdnu)

            sales = get_sales(rdnu)



        except NoSuchElementException:
            print("⚠️ 팝업이 보이지 않거나, 구조가 변경되었습니다.")



