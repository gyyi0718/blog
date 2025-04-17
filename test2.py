import requests
from bs4 import BeautifulSoup

all_post_urls = []

# 예시: 1~10페이지까지 수집 (원하는 범위로 수정)
for page in range(1, 11):
    url = f"https://opengov.seoul.go.kr/expense/list?page={page}"
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
