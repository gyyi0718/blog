import os
import requests
import pandas as pd
from urllib.parse import urljoin
import pdfplumber
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
SAVE_DIR = "guro_downloads"
os.makedirs(SAVE_DIR, exist_ok=True)
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import time

# ✅ Selenium으로 게시글 리스트 수집
def get_post_list_playwright(pages=1):
    post_list = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page(viewport={"width": 1280, "height": 1000})

        for i in range(1, pages + 1):
            url = f"https://www.guro.go.kr/www/selectBbsNttList.do?bbsNo=655&&pageUnit=10&key=1732&pageIndex={i}"
            print(f"▶ 접속 중: {url}")
            page.goto(url, timeout=30000)

            # 강제로 스크롤해서 lazy load 트리거
            page.mouse.wheel(0, 3000)
            page.wait_for_timeout(3000)  # 기다리기

            try:
                page.wait_for_selector("table.tblList tbody tr", timeout=5000)
            except:
                print(f"❗ 게시판 표 안뜸, HTML 저장")
                with open(f"fail_page_{i}.html", "w", encoding="utf-8") as f:
                    f.write(page.content())
                continue

            html = page.content()
            soup = BeautifulSoup(html, "html.parser")
            rows = soup.select("table.tblList tbody tr")
            print(f"✅ {i}페이지 게시글 {len(rows)}개 탐색")

            for row in rows:
                cols = row.find_all("td")
                if len(cols) < 4:
                    continue
                title = cols[1].get_text(strip=True)
                date = cols[3].get_text(strip=True)
                a_tag = cols[1].find("a")
                if not a_tag or "onclick" not in a_tag.attrs:
                    continue
                try:
                    onclick = a_tag["onclick"]
                    ntt_no = onclick.split("'")[1]
                except:
                    continue
                post_list.append({
                    "제목": title,
                    "등록일": date,
                    "게시글번호": ntt_no
                })
            time.sleep(0.5)

        browser.close()

    return post_list
def get_file_links(ntt_no):
    detail_url = "https://www.guro.go.kr/www/selectBbsNttInfo.do"
    params = {
        "bbsNo": 655,
        "key": 1732,
        "nttNo": ntt_no
    }
    res = requests.get(detail_url, params=params)
    soup = BeautifulSoup(res.text, "html.parser")
    links = soup.select("div.bbs_file a")
    return [urljoin("https://www.guro.go.kr", a["href"]) for a in links if a.get("href")]

# ✅ 파일 다운로드 및 저장
def download_file(file_url, title):
    try:
        ext = file_url.split('.')[-1].split('?')[0]
        filename = f"{title.replace(' ', '_')}.{ext}"
        path = os.path.join(SAVE_DIR, filename)
        r = requests.get(file_url)
        with open(path, "wb") as f:
            f.write(r.content)
        return path
    except Exception as e:
        print("❌ 다운로드 실패:", file_url, e)
        return None

# ✅ 엑셀 파일 파싱
def parse_excel(file_path):
    try:
        df = pd.read_excel(file_path, engine='openpyxl' if file_path.endswith('xlsx') else None)
        df["출처파일"] = os.path.basename(file_path)
        return df
    except Exception as e:
        print(f"❌ 엑셀 파싱 실패: {file_path}, {e}")
        return pd.DataFrame()

# ✅ PDF 텍스트 추출
def parse_pdf(file_path):
    try:
        with pdfplumber.open(file_path) as pdf:
            text = "\n".join([page.extract_text() or '' for page in pdf.pages])
        return {"파일": os.path.basename(file_path), "미리보기": text[:500]}
    except Exception as e:
        print(f"❌ PDF 파싱 실패: {file_path}, {e}")
        return None

# ✅ HWP 텍스트 추출 (기본은 이름만 기록)
def parse_hwp(file_path):
    # hwp 파일 텍스트 추출은 복잡해서 외부 도구 필요 (여기선 이름만 수집)
    return {"파일": os.path.basename(file_path), "미리보기": "※ HWP 파일 – 텍스트 추출 생략됨"}

# ✅ 전체 처리
def run_all(pages=3):
    posts = get_post_list_playwright(pages)
    excel_list = []
    pdf_previews = []
    hwp_infos = []

    for post in posts:
        print(f"📄 {post['제목']} 처리 중...")
        links = get_file_links(post['게시글번호'])
        for link in links:
            path = download_file(link, post["제목"])
            if not path:
                continue
            if path.endswith((".xls", ".xlsx")):
                df = parse_excel(path)
                if not df.empty:
                    excel_list.append(df)
            elif path.endswith(".pdf"):
                preview = parse_pdf(path)
                if preview:
                    pdf_previews.append(preview)
            elif path.endswith(".hwp"):
                hwp_infos.append(parse_hwp(path))
            time.sleep(0.3)

    # 결과 저장
    if excel_list:
        merged_df = pd.concat(excel_list, ignore_index=True)
        merged_df.to_excel("guro_업무추진비_통합.xlsx", index=False)
        print("✅ 엑셀 통합 완료: guro_업무추진비_통합.xlsx")

    if pdf_previews:
        pd.DataFrame(pdf_previews).to_excel("guro_pdf_미리보기.xlsx", index=False)
        print("✅ PDF 요약 저장 완료")

    if hwp_infos:
        pd.DataFrame(hwp_infos).to_excel("guro_hwp_파일목록.xlsx", index=False)
        print("✅ HWP 목록 저장 완료")

get_post_list_playwright(3)