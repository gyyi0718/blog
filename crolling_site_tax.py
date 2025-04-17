import os
import requests
import pandas as pd
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from io import BytesIO
from collections import Counter
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
import pdfplumber
import time
from matplotlib.ticker import MaxNLocator
from matplotlib.ticker import MultipleLocator
import zipfile
import xml.etree.ElementTree as ET


# 저장 폴더 설정
SAVE_DIR = "광주시_업무추진비_식비"
os.makedirs(SAVE_DIR, exist_ok=True)

# 광주시청 게시판 목록 URL (업무추진비 게시판 기준)
#base_list_url = "https://www.gjcity.go.kr/portal/bbs/list.do?ptIdx=53&mId=0311000000&token=1744629207286"
#base_host = "https://www.gjcity.go.kr"


headers = {"User-Agent": "Mozilla/5.0"}

all_filtered_data = []
restaurant_counter = Counter()
options = Options()
options.add_argument("--headless")  # 창 없이 실행
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
restaurant_list = []

def normalize_excel_sheet(df):
    if isinstance(df, pd.Series):
        return pd.DataFrame([df])
    elif isinstance(df, pd.DataFrame):
        return df
    else:
        return None

def extract_from_excel(download_url):
    try:
        with requests.get(download_url, headers=headers, timeout=10, stream=True) as r:
            r.raise_for_status()

            # 스트리밍 데이터를 BytesIO로 안전하게 저장
            file_bytes = BytesIO()
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    file_bytes.write(chunk)

            file_bytes.seek(0)  # 파일 포인터를 처음으로 되돌림

            # 엑셀 파일 로딩
            xl = pd.read_excel(file_bytes, engine="openpyxl")  # .xlsx 기본
            print(xl.head())

            for sheet_name, df in xl.items():
                try:
                    df = normalize_excel_sheet(df)
                    df.columns = df.columns.astype(str)
                    df = df.dropna(how="all")  # 전체가 NaN인 행 제거

                    print("excel : ",df.head(5))
                    filtered_rows = []
                    for i, row in df.iterrows():
                        values = row.dropna().astype(str).str.strip()
                        if any("사용처" in val or "사용장소" in val for val in values):
                            filtered_rows.append(row)

                    if not filtered_rows:
                        continue

                    filtered = pd.DataFrame(filtered_rows)

                    for i, row in filtered.iterrows():
                        values = row.dropna().astype(str).str.strip()
                        for val in values:
                            val_clean = val.strip()
                            if (
                                    val_clean
                                    and len(val_clean) > 1
                                    and not any(k in val_clean for k in ["사용처", "사용장소"])
                            ):
                                restaurant_list.append(val_clean)
                                print(val_clean)
                except Exception as e:
                    print(f"⚠️ 시트 오류 - '{sheet_name}': {e}")

            file_bytes.close()

    except Exception as e:
        print(f"❌ 파일 다운로드 또는 처리 실패: {download_url}, {e}")

def extract_from_pdf(download_url):
    try:
        pdf_res = requests.get(download_url, headers=headers, stream=True, timeout=10)
        pdf_res.raise_for_status()
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
            for chunk in pdf_res.iter_content(8192):
                tmp_pdf.write(chunk)
            tmp_pdf_path = tmp_pdf.name
        try:
            with pdfplumber.open(tmp_pdf_path) as pdf_file:
                with pdfplumber.open(pdf_file) as pdf:
                    for page in pdf.pages:
                        try:
                            tables = page.extract_tables()
                            for table in tables:
                                df = pd.DataFrame(table)
                                df.columns = df.iloc[0]
                                df = df[1:]
                                df.columns = df.columns.astype(str)
                                for col in df.columns:
                                    if any(keyword in col for keyword in ["사용처", "사용장소"]):
                                        for val in df[col].dropna():
                                            val_clean = str(val).strip()
                                            if 1 < len(val_clean) < 50:
                                                restaurant_list.append(val_clean)
                                print("pdf : ",df.head(5))
                        except Exception as page_err:
                            print(f"⚠️ PDF 페이지 처리 실패: {page_err}")
        except Exception as pdf_err:
            print(f"❌ PDF 열기 실패: {pdf_err}")

    except Exception as e:
        print(f"❌ 파일 다운로드 또는 처리 실패: {download_url}, {e}")


def extract_hwp(download_url):
    temp_list = []
    try:
        res = requests.get(download_url, headers=headers)
        res.raise_for_status()
        with zipfile.ZipFile(BytesIO(res.content)) as zip_ref:
            zip_ref.extractall("temp_hwpx")

        tree = ET.parse("temp_hwpx/Contents/section0.xml")
        root = tree.getroot()

        for elem in root.iter():
            if elem.tag.endswith("t") and elem.text:
                text = elem.text.strip()
                if any(kw in text for kw in ["식당", "쭈꾸미", "추어탕", "국밥", "불고기"]):
                    if 1 < len(text) < 50:
                        temp_list.append(text)
    except Exception as e:
        print(f"❌ HWPX 파일 처리 실패: {e}")
    return temp_list


def test():
    url = "https://www.seongnam.go.kr/city/1000199/30218/bbsView.do?currentPage=1&searchSelect=&searchWord=&searchOrganDeptCd=&searchCategory=&subTabIdx=&idx=370220&post_size=10"
    headers = {"User-Agent": "Mozilla/5.0"}

    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    attachment_tags = soup.find_all("a", href=True)

    for a in attachment_tags:
        onclick = a.get("onclick", "")
        if "fileDownload" in onclick:
            print("📌 onclick =", onclick)
            match = re.search(r"fileDownload\('([^']+)',\s*'([^']+)'", onclick)
            if match:
                file_id, file_name = match.group(1), match.group(2)
                download_url = f"https://www.seongnam.go.kr/city/bbs/fileDownload.do?fileId={file_id}&fileSn={file_name}"
                print("✅ 다운로드 링크:", download_url)
            else:
                print("❌ 패턴 일치 실패:", onclick)

def get_url_path(detail_url):
    download_url = ""
    for page in range(1, 4):  # 전체 페이지 수 조정 가능
        print(f"📄 페이지 {page} 수집 중...")
        list_url = f"{detail_url}?currentPage={page}"
        driver.get(list_url)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        rows = soup.select("table tr")[1:]
        for row in rows:
            a_tag = row.select_one("td:nth-child(2) a")
            if not a_tag:
                continue
            detail_url = "https://www.seongnam.go.kr" + a_tag.get("href")
            driver.get(detail_url)
            time.sleep(1)
            detail_soup = BeautifulSoup(driver.page_source, "html.parser")

            attachment_tags = detail_soup.find_all("a", href=True)
            for a in attachment_tags:
                onclick = a.get("onclick", "")
                print("📌 onclick =", onclick)

                match = re.search(r"fileDownload\('([^']+)',\s*'([^']+)'", onclick)
                print("match={}".format(match))
                if match:
                    file_id, file_name = match.group(1), match.group(2)
                    download_url = f"https://www.seongnam.go.kr/city/bbs/fileDownload.do?fileId={file_id}&fileSn={file_name}"
                    print(f"✅ 다운로드 링크: {download_url}")

                    try:
                        res = requests.get(download_url, headers=headers)
                        res.raise_for_status()
                        with zipfile.ZipFile(BytesIO(res.content)) as zip_ref:
                            zip_ref.extractall("temp_hwpx")

                        tree = ET.parse("temp_hwpx/Contents/section0.xml")
                        root = tree.getroot()

                        texts = []
                        for elem in root.iter():
                            if elem.tag.endswith("t") and elem.text:
                                texts.append(elem.text.strip())

                        for t in texts:
                            if any(kw in t for kw in ["사용처", "사용장소"]):
                                name = t.strip()
                                if 1 < len(name) < 50:
                                    restaurant_counter[name] += 1

                    except Exception as e:
                        print(f"❌ 파일 처리 실패: {e}")
    return download_url


def seongnam_site(base_list_url):
    base_list_url = "https://www.seongnam.go.kr/city/1000199/30218/bbsView.do?currentPage=1&searchSelect=&searchWord=&searchOrganDeptCd=&searchCategory=&subTabIdx=&idx=370220&post_size=10"
    all_text_data = []
    for page in range(1, 73):
        print(f"📄 페이지 {page} 수집 중...")
        params = {"currentPage": page}
        res = requests.get(base_list_url, params=params, headers=headers)
        soup = BeautifulSoup(res.text, "html.parser")
        rows = soup.select("table tr")[1:]

        for row in rows:
            title_tag = row.select_one("td:nth-child(2) a")
            if not title_tag:
                continue

            title = title_tag.text.strip()
            date = row.select_one("td:nth-child(5)").text.strip()
            detail_url = urljoin("https://www.seongnam.go.kr", title_tag.get("href"))

            try:
                detail_res = requests.get(base_list_url, headers=headers)
                detail_soup = BeautifulSoup(detail_res.text, "html.parser")
                attachment_tags = detail_soup.find_all('a', href=True)

                for a in attachment_tags:
                    onclick = a.get("onclick", "")
                    match = re.search(r"fileDownload\('([^']+)',\s*'([^']+)'", onclick)
                    if match:
                        file_id = match.group(1)
                    download_url = f"https://www.seongnam.go.kr/city/bbs/download.do?fileNo={file_id}"
                    print(f"✅ 파일 다운로드 링크: {download_url}")

                    if download_url.endswith(".hwpx"):
                        hwpx_res = requests.get(download_url, headers=headers)
                    with zipfile.ZipFile(BytesIO(hwpx_res.content)) as zip_ref:
                        zip_ref.extractall("temp_hwpx")

                    tree = ET.parse("temp_hwpx/Contents/section0.xml")
                    root = tree.getroot()

                    texts = []
                    for elem in root.iter():
                        if elem.tag.endswith("t") and elem.text:
                            texts.append(elem.text.strip())

                            all_text_data.extend(texts)

                    # 간단한 식당 이름 추출 예시
                    for t in texts:
                        if any(kw in t for kw in ["사용처", "사용장소"]):
                            name = t.strip()
                    if 1 < len(name) < 50:
                        restaurant_counter[name] += 1

            except Exception as e:
                print(f"❌ 상세 페이지 또는 파일 처리 실패: {e}")


def gawngju_site():
    # 게시글 목록 순회
    base_list_url = "https://www.seongnam.go.kr/city/1000199/30218/bbsList.do#370220"
    base_host = "https://www.seongnam.go.kr/"
    for page in range(1, 73):  # 필요시 페이지 수 조정
        params = {"page": page}
        res = requests.get(base_list_url, params=params, headers=headers)
        soup = BeautifulSoup(res.text, "html.parser")
        rows = soup.select("table tr")[1:]

        for row in rows:
            title_tag = row.select_one("td:nth-child(2) a")
            if not title_tag:
                continue

            title = title_tag.text.strip()
            date = row.select_one("td:nth-child(5)").text.strip()

            # 게시글 ID 추출 (javascript:fn_view('123456'))
            onclick_text = title_tag.get("onclick")
            match = re.search(r"goTo\.view\('list','(\d+)', *'(\d+)', *'(\d+)'\)", onclick_text)

            if not match:
                print("❌ 게시글 ID 추출 실패:", onclick_text)
                continue

            post_id, ptIdx, mId = match.group(1), match.group(2), match.group(3)
            detail_url = f"https://www.gjcity.go.kr/portal/bbs/view.do?mId={mId}&bIdx={post_id}&ptIdx={ptIdx}"


            try:
                # 상세페이지 접근
                detail_res = requests.get(detail_url, headers=headers)
                detail_soup = BeautifulSoup(detail_res.text, "html.parser")

                # 첨부파일 추출 (.xls 또는 .xlsx만 필터링)
                attachment_tags = detail_soup.find_all('a', href=True)
                excel_links = []
                attachment_links = []
                file_type =""
                for a in attachment_tags:
                    if '다운로드' in str(a):
                        if ".pdf" in str(a):
                            file_type = ".pdf"
                        elif ".hwpx" in str(a):
                            file_type = ".hwpx"
                        else :
                            file_type = a
                        onclick = a.get("onclick")
                        if not onclick:
                            continue

                        match = re.search(r"yhLib\.file\.download\('([^']+)',\s*'([^']+)'\)", onclick)
                        if match:
                            file_id, file_sn = match.group(1), match.group(2)
                            download_url = f"https://www.gjcity.go.kr/common/file/download.do?atchFileId={file_id}&fileSn={file_sn}"
                            attachment_links.append(download_url)
                            print("✅ 첨부파일 다운로드 링크:", download_url)
                        else:
                            print("⚠️ 다운로드 패턴 아님:", onclick)

                print("🙏🙏 file type : ", file_type)

                if file_type == ".pdf":
                    print()
                    extract_from_pdf(download_url)
                elif file_type == ".hwpx":
                    extract_hwp(download_url)
                else:
                    extract_from_excel(download_url)

            except Exception as e:
                print("상세페이지 에러")
            # ✅ 식비 내역 저장

            restaurant_counter = Counter(restaurant_list)

            # 데이터프레임으로 저장
            final_df = pd.DataFrame(restaurant_counter.items(), columns=["식당이름", "사용횟수"])
            final_df = final_df.sort_values(by="사용횟수", ascending=False)

            final_df.to_csv("광주시_식당_사용빈도_정제본.csv", index=False, encoding="utf-8-sig")

            print("✅ 식당 사용 빈도 분석 결과 저장 완료")

    plt.rcParams['font.family'] = 'Malgun Gothic'
    plt.rcParams['axes.unicode_minus'] = False  # 마이너스 기호 깨짐 방지
    plt.figure(figsize=(10, 6))
    top_df = final_df.head(15)
    plt.barh(top_df["식당이름"], top_df["사용횟수"])
    plt.xlabel("사용횟수")
    plt.ylabel("식당이름")
    plt.title("광주시 업무추진비 식당 사용 빈도 (Top 15)")
    plt.gca().invert_yaxis()
    plt.gca().xaxis.set_major_locator(MultipleLocator(1))
    plt.tight_layout()
    plt.savefig("2024~ 2025.04 광주시_Top15_식당.png")
    #plt.show()

def get_attachment_urls(detail_url):
    driver.get(detail_url)
    time.sleep(1)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    attachment_tags = soup.select("div.bo_file a")
    download_links = []
    for a in attachment_tags:
        href = a.get("href")
        if href:
            full_link = urljoin("https://www.geumcheon.go.kr", href)
            download_links.append(full_link)
    return download_links
def get_detail_url_pattern(a_tag, base_url):
    detail_href = a_tag.get("href")
    detail_url = base_url + detail_href
    driver.get(detail_url)
    time.sleep(1)
    detail_soup = BeautifulSoup(driver.page_source, "html.parser")

    # 🔧 수정된 선택자
    attachment_tags = detail_soup.select(".bo_file a")
    print(f"📎 첨부파일 수: {len(attachment_tags)}")

    for a in attachment_tags:
        href = a.get("href")
        if not href:
            continue
        download_url = "https://www.geumcheon.go.kr" + href
        print(f"✅ 다운로드 링크: {download_url}")

        try:
            file_ext = os.path.splitext(download_url)[-1].lower()
            if file_ext == ".hwpx":
                extract_hwp(download_url)
            elif file_ext == ".pdf":
                 extract_from_pdf(download_url)
            elif file_ext == ".xlsx":
                 extract_from_excel(download_url)
        except Exception as e:
            print(f"❌ 파일 처리 실패: {e}")

def site1_pattern(base_list_url, base_url):
    for page in range(1, 3):  # 필요한 페이지 수 조정
        driver.get(f"{base_list_url}&page={page}")
        time.sleep(1)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        rows = soup.select("table.tbl01 tbody tr")

        for row in rows:
            a_tag = row.select_one("td.p-subject a")
            if not a_tag:
                continue
            title = a_tag.get_text(strip=True)
            href = a_tag.get("href")
            detail_url = urljoin("https://www.geumcheon.go.kr", href)

            print(f"🔎 게시글: {title} → {detail_url}")
            try:
                file_urls = get_attachment_urls(detail_url)
                for file_url in file_urls:
                    if file_url.endswith(".hwpx"):
                        extracted = extract_hwp(file_url)
                        restaurant_list.extend(extracted)
            except Exception as e:
                print(f"❌ 첨부파일 처리 실패: {e}")


if __name__ == "__main__":
    detail_url = "https://www.seongnam.go.kr/city/1000199/30218/bbsList.do#370220"
    detail_url2 = "https://www.seongnam.go.kr/city/1000199/30218/bbsView.do?currentPage=1&searchSelect=&searchWord=&searchOrganDeptCd=&searchCategory=&subTabIdx=&idx=370220&post_size=10"
    #get_url_path(detail_url)
    #test()
    base_list_url = "https://www.geumcheon.go.kr/portal/selectBbsNttList.do?bbsNo=86&key=269"
    base_url = "https://www.geumcheon.go.kr"

    response = requests.get(base_list_url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    site1_pattern(base_list_url, base_url)
    restaurant_counter = Counter(restaurant_list)
    final_df = pd.DataFrame(restaurant_counter.items(), columns=["사용장소", "횟수"])
    final_df = final_df.sort_values(by="횟수", ascending=False)
    final_df.to_csv("금천구청_식당_사용빈도.csv", index=False, encoding="utf-8-sig")
    print("✅ 식당 사용 빈도 분석 결과 저장 완료")
