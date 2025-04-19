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

# 2) 검색 아이콘 클릭 (좌표 예: x=100, y=60)
pyautogui.moveTo(150, 170, duration=0.2)
pyautogui.click()

# 2) 검색 아이콘 클릭 (좌표 예: x=100, y=60)
pyautogui.moveTo(150, 170, duration=0.2)
pyautogui.click()

# 2) 클립보드에 "강남역" 복사
pyperclip.copy("강남역")

# 3) Ctrl+V 로 붙여넣기
pyautogui.hotkey("ctrl", "v")
time.sleep(0.2)

# 4) Enter 로 검색 실행
pyautogui.press("enter")

# 5) 검색어 입력 직후 제안목록 뜰 때까지 잠시 대기
time.sleep(1)

# 6) 키보드로 첫 번째 항목 선택 → 엔터
pyautogui.press("down")
time.sleep(0.1)
pyautogui.press("enter")

# 7) 지도 이동 대기
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