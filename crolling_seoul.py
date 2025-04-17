import requests
from bs4 import BeautifulSoup
from collections import Counter
import pandas as pd
import os
from collections import defaultdict
import re
# 서울시 25개 자치구 리스트
SEOUL_DISTRICTS = [
    '강남구', '강동구', '강북구', '강서구', '관악구', '광진구', '구로구',
    '금천구', '노원구', '도봉구', '동대문구', '동작구', '마포구', '서대문구',
    '서초구', '성동구', '성북구', '송파구', '양천구', '영등포구', '용산구',
    '은평구', '종로구', '중구', '중랑구'
]
def clean_place_name(name: str) -> str:
    """사용장소에서 불필요한 텍스트 제거"""
    name = str(name)
    name = name.replace('서울특별시', '')
    name = name.replace('서울 ', '')
    name = name.replace('서울', '')
    name = name.replace('  ', ' ')
    name = re.sub(r'\(.*?\)', '', name)
    name = name.strip()
    return name

def get_table_info(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    # 표 찾기 (class='table bordered centered')
    table = soup.find('table', class_='table bordered centered')

    places = []
    if table:
        # 헤더에서 '사용장소' 열 인덱스 찾기
        headers = [th.get_text(strip=True) for th in table.find('thead').find_all('th')]
        try:
            idx = headers.index('사용장소')
            # 각 행에서 해당 열 데이터 추출
            for row in table.find('tbody').find_all('tr'):
                cells = row.find_all('td')
                if len(cells) > idx:
                    name = clean_place_name(cells[idx].get_text(strip=True))
                    places.append(name)
        except ValueError:
            places = []

    # 결과 출력
    for place in places:
        print(place)
    return places

def get_post_urls(url, f_page, e_page):
    all_post_urls = []

    # 예시: 1~10페이지까지 수집 (원하는 범위로 수정)
    for page in range(f_page, e_page):
        resp = requests.get(url)
        soup = BeautifulSoup(resp.text, "html.parser")
        for a in soup.find_all('a', href=True):
            href = a['href']
            if href.startswith("/expense/") and href[9:].isdigit():
                full_url = "https://opengov.seoul.go.kr" + href
                all_post_urls.append(full_url)
        print(f"{page}페이지 완료, 누적 {len(all_post_urls)}개")

    print(f"\n총 {len(all_post_urls)}개의 게시글 URL을 수집했습니다.")
    for u in all_post_urls:
        print(u)
    return all_post_urls

def extract_table_data_from_post(url, month):
    places = []
    try :
        for i in range(1,100):
            post_urls =get_post_urls(url, i,i+1)
            for url in post_urls:
                places.extend(get_table_info(url))

        for place in places:
            print(place)
    except :
        print("error")
    restaurant_counter = Counter(places)
    final_df = pd.DataFrame(restaurant_counter.items(), columns=["사용장소", "횟수"])
    final_df = final_df.sort_values(by="횟수", ascending=False)
    final_df.to_csv("서울시공무원_식당_사용빈도_2024{:02d}.csv".format(month), index=False, encoding="utf-8-sig")
    print("✅ 식당 사용 빈도 분석 결과 저장 완료")


def recount_restaurant_usage_from_csvs(csv_dir, output_path="재집계_식당사용횟수.csv"):
    """
    주어진 디렉토리 내 모든 CSV 파일에서 '식당이름' 열을 추출하여 사용 횟수를 재카운팅합니다.

    Parameters:
        csv_dir (str): CSV 파일이 저장된 폴더 경로
        output_path (str): 결과를 저장할 CSV 파일 경로
    """
    restaurant_counter = Counter()
    restaurant_list = []
    csv_dir = os.getcwd()+"/"+csv_dir
    csv_dir = csv_dir.replace("\\","/")
    for filename in os.listdir(csv_dir):
        if filename.endswith(".csv"):
            filepath = csv_dir+"/"+filename
            try:
                df = pd.read_csv(filepath, encoding='utf-8-sig', sep=',', on_bad_lines='skip')
                # '사용장소'와 '횟수' 열이 모두 있는 경우에만 처리
                if '사용장소' in df.columns and '횟수' in df.columns:
                    for name, count in zip(df['사용장소'], df['횟수']):
                        try:
                            restaurant_counter[str(name).strip()] += int(count)
                        except:
                            continue
                else:
                    print(f"⚠️ '사용장소' 또는 '횟수' 열 없음: {filename}")
            except Exception as e:
                print(f"❌ 파일 읽기 실패: {filename} / {e}")

    # 사용 횟수 카운트
    restaurant_counter = Counter(restaurant_counter)

    if restaurant_counter:
        result_df = pd.DataFrame(restaurant_counter.items(), columns=["사용장소", "횟수"])
        result_df = result_df.sort_values(by="횟수", ascending=False)

        result_df.to_csv(output_path, index=False, encoding="utf-8-sig")
        print(f"✅ 재카운팅 결과 저장 완료: {output_path}")
        return result_df
    else:
        print("⚠️ 유효한 식당 데이터가 없습니다.")
        return pd.DataFrame()

def count_seoul_districts_and_save(csv_files, restaurant_column='사용장소', count_column='횟수'):
    summary = []
    district_data = defaultdict(list)

    for file in csv_files:
        try:
            df = pd.read_csv(file, encoding='utf-8', sep=',', on_bad_lines='skip')
        except UnicodeDecodeError:
            df = pd.read_csv(file, encoding='cp949', sep=',', on_bad_lines='skip')

        for _, row in df[[restaurant_column, count_column]].dropna().iterrows():
            name = str(row[restaurant_column])
            count = int(row[count_column])
            for district in SEOUL_DISTRICTS:
                if district in name:
                    district_data[district].append((name, count))
                    break


    for district, items in district_data.items():
        temp_df = pd.DataFrame(items, columns=[restaurant_column, count_column])
        grouped = temp_df.groupby(restaurant_column)[count_column].sum().reset_index()
        grouped = grouped.sort_values(by=count_column, ascending=False).reset_index(drop=True)
        filename = f"{district}_맛집랭킹.csv"
        grouped.to_csv(filename, index=False, encoding='utf-8-sig')
        total = grouped[count_column].sum()
        summary.append((district, total))

    summary_df = pd.DataFrame(summary, columns=['자치구', '총합'])
    summary_df = summary_df.sort_values(by='총합', ascending=False).reset_index(drop=True)
    summary_df.to_csv("자치구별_맛집랭킹_요약.csv", index=False, encoding="utf-8-sig")


if __name__ =="__main__":
    for i in range(1,13):
        url = "https://opengov.seoul.go.kr/expense/list?ym%5Byear%5D=2024&ym%5Bmonth%5D={}".format(i)
        #extract_table_data_from_post(url, i)
    # recount_restaurant_usage_from_csvs(csv_dir="dir")

    csv_dir = os.getcwd()+"/"+"dir/"
    csv_dir = csv_dir.replace("\\","/")
    csv_files = []
    for filename in os.listdir(csv_dir):
        if filename.endswith(".csv"):
            filepath = csv_dir+filename
            csv_files.append(filepath)

    count_seoul_districts_and_save(csv_files)
