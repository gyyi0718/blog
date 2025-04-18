import pyautogui
import time
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import ctypes
import requests
import json
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
import ctypes
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

url = "https://api.openub.com/v2/coord"

headers = {
    "Origin": "https://www.openub.com",
    "Referer": "https://www.openub.com/",
    "User-Agent": "Mozilla/5.0",
    "Content-Type": "application/json"
}

# 지도 내 좌표 박스
payload = {
    "bbox": {
        "ne": {"lng": 126.8897083, "lat": 37.4898443},
        "sw": {"lng": 126.8754118, "lat": 37.4733469}
    }
}

res = requests.post(url, headers=headers, json=payload)
print("🔁 상태코드:", res.status_code)

if res.status_code == 200:
    try:
        data = res.json()
        if isinstance(data, list):
            print(f"🏢 건물 개수: {len(data)}")
            for b in data:
                print(f"{b['bldNm']} / {b['rdnu']} / {b['addr']}")
        else:
            print("📍 응답은 건물 리스트가 아님 (예: 주소만 반환)")
            print(json.dumps(data, indent=2, ensure_ascii=False))
    except Exception as e:
        print("❌ JSON 파싱 실패:", e)
else:
    print("❌ 요청 실패:", res.status_code)

time.sleep(3)

# 지도 로딩 후 바로 여러 위치 반복 클릭
map_area = driver.find_element(By.ID, "map")
actions = ActionChains(driver)

for dx in range(300, 601, 100):  # x축 반복
    for dy in range(250, 501, 100):  # y축 반복
        actions.move_to_element_with_offset(map_area, dx, dy).click().perform()
        time.sleep(2)

        # 추정 매출 텍스트 추출
        elements = driver.find_elements(By.XPATH, "//*[contains(text(), '억') or contains(text(), '원')]")
        print(f"🧭 클릭 위치: ({dx},{dy})")
        for e in elements:
            print("   💰", e.text)