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

import time
# 저장 폴더 설정
SAVE_DIR = "광주시_업무추진비_식비"
os.makedirs(SAVE_DIR, exist_ok=True)

# 광주시청 게시판 목록 URL (업무추진비 게시판 기준)
base_list_url = "https://www.gjcity.go.kr/portal/bbs/list.do?ptIdx=53&mId=0311000000&token=1744629207286"
base_host = "https://www.gjcity.go.kr"
headers = {"User-Agent": "Mozilla/5.0"}

all_filtered_data = []
restaurant_counter = Counter()
options = Options()
options.add_argument("--headless")  # 창 없이 실행
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def normalize_excel_sheet(df):
    if isinstance(df, pd.Series):
        return pd.DataFrame([df])
    elif isinstance(df, pd.DataFrame):
        return df
    else:
        return None

def normalize_excel_sheet(download_url):
    print()


if __name__ == "__main__":
    # 게시글 목록 순회
    restaurant_list = []
    for page in range(1, 2):  # 필요시 페이지 수 조정
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

                for a in attachment_tags:
                    if '다운로드' in str(a):
                        print(a)
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

                                print(df.head())

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

                except Exception as e:
                    print(f"❌ 파일 다운로드 또는 처리 실패: {download_url}, {e}")

            except e:
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
    plt.tight_layout()
    plt.show()
    plt.savefig("광주시_Top15_식당.png")


