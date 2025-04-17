from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
# Selenium 웹드라이버 설정
options = Options()
options.add_argument("--headless")  # 브라우저 창을 띄우지 않음
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
wait = WebDriverWait(driver, 10)

try:

    options = webdriver.ChromeOptions()
    # options.add_argument("--headless")  # ← 이 줄을 주석처리
    options.add_argument("--window-size=1280,800")

    driver = webdriver.Chrome(options=options)

    # 오픈업 웹사이트 접속
    driver.get("https://www.openub.com")
    time.sleep(2)
    btn_exists = driver.execute_script("""
        return !!document.querySelector('button.close');
    """)

    print("✅ 닫기 버튼 있음" if btn_exists else "❌ 닫기 버튼 없음")
    driver.execute_script("""
        const btn = document.querySelector('button.close');
        if (btn) {
            btn.style.display = 'block';
            btn.style.visibility = 'visible';
            btn.style.pointerEvents = 'auto';
            btn.style.opacity = '1';
            btn.scrollIntoView({behavior: 'smooth', block: 'center'});
            setTimeout(() => btn.click(), 100);  // JS 이벤트로 클릭
        }
    """)
    time.sleep(1)
    # 검색창 로딩 대기 후 검색어 입력
    # ✅ 검색창 로딩 후 검색어 입력
    search_box = wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input#search-address-map-mobile"))
    )
    search_box.send_keys("서울 금천구 가산동")
    search_box.send_keys(Keys.ENTER)
    print("🔍 검색 실행")

    # 매장 목록 수집
    store_elements = driver.find_elements(By.CLASS_NAME, "store-item")  # 실제 클래스명은 웹사이트 구조에 따라 다를 수 있음
    for store in store_elements:
        name = store.find_element(By.CLASS_NAME, "store-name").text
        revenue = store.find_element(By.CLASS_NAME, "store-revenue").text
        print(f"{name}: {revenue}")

finally:
    driver.quit()
