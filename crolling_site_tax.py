# 구로구청 업무추진비 첨부파일 크롤링 및 파싱 리팩터링 코드
from urllib.parse import unquote
from pathlib import Path

import os
import time
import requests
import pandas as pd
import re
import shutil
from pathlib import Path
import zipfile
import pdfplumber
from io import BytesIO
from bs4 import BeautifulSoup
from collections import Counter
from urllib.parse import urljoin
import xml.etree.ElementTree as ET
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import urllib.parse
from urllib.parse import unquote

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# 설정
save_dir  = "temp"
os.makedirs(save_dir, exist_ok=True)
headers = {"User-Agent": "Mozilla/5.0"}
restaurant_list = []
restaurant_counter = Counter()

# Selenium 드라이버 설정
options = Options()
options.add_argument("--headless")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)


def clean_restaurant_name(name):
    # (주) 또는 ㈜ 제거
    name = re.sub(r"\(?㈜?\s?주식회사\)?", "", name)
    name = re.sub(r"\(?㈜?\)?", "", name)
    name = re.sub(r"\(?주\)?", "", name)

    # 괄호 안 텍스트 제거
    name = re.sub(r"\(.*?\)", "", name)

    # 앞뒤 공백 정리 및 중복 공백 제거
    name = re.sub(r"\s+", " ", name).strip()

    return name
# ------------------------ 첨부파일 처리 함수 ------------------------ #
def download_file(file_url, title):
    try:
        response = requests.get(file_url, stream=True)
        response.encoding = 'utf-8'  # 필요시 'euc-kr' 또는 'cp949'

        # Content-Disposition 헤더에서 파일명 추출
        if 'Content-Disposition' in response.headers:
            content_disposition = response.headers['Content-Disposition']
            fname_part = content_disposition.split("filename=")[-1].strip('"')
            try:
                # URL 인코딩된 파일명 디코딩 시도
                filename = unquote(fname_part.encode('latin1').decode('utf-8'))
            except:
                filename = unquote(fname_part)  # fallback

        else:
            filename = file_url.split("/")[-1]  # fallback

        # 파일 저장
        save_path = save_dir+"/"+ filename

        with open(save_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        print(f"✅ 다운로드 완료: {save_path}")
        return save_path

    except Exception as e:
        print(f"❌ 다운로드 실패: {file_url}, 에러: {e}")
        return None
def process_file(file_path):
    # 여기에 실제 처리 작업 (예: 텍스트 추출, 데이터 분석 등)
    print(f"📄 파일 처리 중... {file_path.name}")
    # 예시 작업: 이름 출력
    print(f"📂 파일 이름: {file_path.name}")


def clean_file(file_path):
    try:
        file_path.unlink()
        print(f"🧹 삭제 완료: {file_path}")
    except Exception as e:
        print(f"⚠️ 삭제 실패: {e}")
def extract_excel(file_path):
    try:
        df = pd.read_excel(file_path, engine='openpyxl' if file_path.endswith('xlsx') else None)
        for _, row in df.iterrows():
            values = row.dropna().astype(str).str.strip()
            for val in values:
                if 1 < len(val) < 50 and not any(k in val for k in ["사용처", "사용장소","장소"]):
                    val = val.replace('"', "")
                    val = val.replace("'", "")
                    restaurant_list.append(val)
        return df
    except Exception as e:
        print(f"❌ 엑셀 파싱 실패: {file_path}, 에러: {e}")
        return pd.DataFrame()

def extract_pdf(file_path):
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    df = pd.DataFrame(table)
                    df.columns = df.iloc[0]
                    df = df[1:]
                    for col in df.columns:
                        if any(keyword in col for keyword in ["사용처", "사용장소","장소"]):
                            for val in df[col].dropna():
                                val_clean = str(val).strip()
                                val_clean = val_clean.replace('"',"")
                                val_clean = val_clean.replace("'","")
                                if 1 < len(val_clean) < 50:
                                    restaurant_list.append(val_clean)
    except Exception as e:
        print(f"❌ PDF 파싱 실패: {file_path}, 에러: {e}")

def extract_hwpx(file_path):
    try:
        with zipfile.ZipFile(file_path) as zip_ref:
            zip_ref.extractall("temp_hwpx")
        tree = ET.parse("temp_hwpx/Contents/section0.xml")
        root = tree.getroot()
        for elem in root.iter():
            if elem.tag.endswith("t") and elem.text:
                text = elem.text.strip()
                if any(kw in text for kw in ["사용처", "사용장소","장소"]):
                    if 1 < len(text) < 50:
                        text = text.replace('"', "")
                        text = text.replace("'", "")
                        restaurant_list.append(text)
    except Exception as e:
        print(f"❌ HWPX 파일 처리 실패: {e}")

def extract_hwp(file_path):
    print(f"📄 HWP 파일 저장됨 (텍스트 추출 없음): {os.path.basename(file_path)}")
    restaurant_list.append({
        "파일": os.path.basename(file_path),
        "설명": "HWP 파일 (텍스트 추출 안됨)"
    })
# ------------------------ 게시글 수집 및 처리 ------------------------ #
def site1_pattern(base_list_url):
    for page in range(20, 100):  # 페이지 범위 조정
        driver.get(f"{base_list_url}&pageIndex={page}")
        time.sleep(1)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        rows = soup.select("table.p-table.simple tbody tr")

        for row in rows:
            a_tag = row.select_one("td.p-subject a")
            if not a_tag:
                continue

            title = a_tag.get_text(strip=True)
            href = a_tag.get("href")
            detail_url = urljoin("https://www.guro.go.kr/www/", href)

            print(f"🔎 게시글: {title} → {detail_url}")
            res = requests.get(detail_url, headers=headers)
            soup = BeautifulSoup(res.text, "html.parser")
            attach_links = soup.select("a.p-attach__link")
            file_urls = [urljoin("https://www.guro.go.kr/www/", tag["href"]) for tag in attach_links if tag.get("href")]

            for file_url in file_urls:
                file_path = download_file(file_url, title)
                if not file_path:
                    continue
                known_exts = [".xlsx", ".xls", ".pdf", ".hwpx", ".hwp"]
                ext = os.path.splitext(file_path)[1].lower()

                if ext == ".xlsx" or ext == ".xls":
                    extract_excel(file_path)
                elif ext == ".pdf":
                    extract_pdf(file_path)
                elif ext == ".hwpx":
                    extract_hwpx(file_path)
                elif ext == ".hwp":
                    extract_hwp(file_path)
                elif ext not in known_exts:
                    print(f"⚠️ 알 수 없는 파일 형식: {file_path}")


            else:
                    print(f"⚠️ 알 수 없는 파일 형식: {file_path}")
def delete_folder(folder_path):
    folder = Path(folder_path)
    if folder.exists() and folder.is_dir():
        shutil.rmtree(folder)
        print(f"🧹 폴더 전체 삭제 완료: {folder}")
    else:
        print(f"⚠️ 존재하지 않거나 폴더가 아닙니다: {folder}")
# ------------------------ 실행 및 결과 저장 ------------------------ #
if __name__ == "__main__":
    base_list_url = "https://www.guro.go.kr/www/selectBbsNttList.do?bbsNo=655&&pageUnit=10&key=1732"
    site1_pattern(base_list_url)

    cleaned_restaurants = [r for r in restaurant_list if isinstance(r, str) and len(r.strip()) >= 2]
    cleaned_restaurants = [clean_restaurant_name(name) for name in cleaned_restaurants]
    restaurant_counter = Counter(cleaned_restaurants)
    # 결과 저장
    final_df = pd.DataFrame(restaurant_counter.items(), columns=["사용장소", "횟수"])
    final_df = final_df.sort_values(by="횟수", ascending=False)
    final_df.to_csv("구로청_식당_사용빈도.csv", index=False, encoding="utf-8-sig")
    print("✅ 식당 사용 빈도 분석 결과 저장 완료")

    delete_folder(save_dir)