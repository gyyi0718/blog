import requests
from bs4 import BeautifulSoup

url = "https://opengov.seoul.go.kr/expense/33239277"
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
                places.append(cells[idx].get_text(strip=True))
    except ValueError:
        places = []

# 결과 출력
for place in places:
    print(place)
