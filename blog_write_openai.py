import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from datetime import datetime
import time
import hot_topic as ht



# ✅ OpenAI API 키 입력
client = OpenAI(api_key="my_key")



# ✅ 실제 기사 링크 수집
def get_articles(rss_url, max_count=5):
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(rss_url, headers=headers)
    soup = BeautifulSoup(res.content, "xml")

    items = soup.find_all("item")[:max_count]
    articles = []

    for item in items:
        title = item.title.text
        link_tag = item.find("link")
        source_tag = item.find("source")  # ✅ 원문 URL일 수 있음
        guid_tag = item.find("guid")

        # ✅ 1순위: <source url=""> 속성
        if source_tag and source_tag.has_attr("url"):
            real_url = source_tag["url"]
        # ✅ 2순위: <guid> 값이 실제 URL인 경우
        elif guid_tag and guid_tag.text.startswith("http"):
            real_url = guid_tag.text
        # ✅ 3순위: fallback - link 값
        else:
            real_url = link_tag.text

        articles.append({"title": title, "link": real_url})

    return articles

# ✅ 본문 추출
def get_article_text_bs4(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)
        res.encoding = res.apparent_encoding
        #res.encoding = "utf-8"
        soup = BeautifulSoup(res.text, 'html.parser')

        if "donga.com" in url:
            body = soup.select_one('.article_txt')
        elif "ohmynews.com" in url:
            wrapper = soup.select_one('div#article_view_content') or soup.select_one('div#oArticle')
            if wrapper:
                paragraphs = wrapper.find_all("p")
                text = " ".join(p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 30)
                return text if text else None
        elif "nate.com" in url:
            body = soup.select_one('#realArtcContents') or soup.select_one('.articleCont')
        elif "mk.co.kr" in url:
            body = soup.select_one('#article_body')
        elif "xportsnews.com" in url:
            body = soup.select_one('.articalContent') or soup.select_one('#articleBody')
        else:
            paragraphs = soup.find_all("p")
            text = " ".join(p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 30)
            return text if text else None

        return body.get_text(strip=True) if body else None
    except Exception as e:
        return None

# ✅ GPT 요약
def summarize_article(title, text):
    if not text or len(text) < 200:
        return "[❌ 본문이 부족하거나 추출 실패]"

    prompt = f"""제목: {title}
다음 기사를 블로그 형식으로 3문장 이내로 요약해줘:\n{text[:3000]}"""

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"[요약 실패] {str(e)}"

# ✅ 블로그 글 생성
def create_blog_post(topic_summaries):
    date = datetime.now().strftime("%Y년 %m월 %d일")
    content = f"# 오늘의 육아·재테크 트렌드 요약 - {date}\n\n"
    content += "육아 중에도 경제 감각과 자녀 교육 감각, 둘 다 챙겨보아요 😊\n\n"

    for category, title, summary in topic_summaries:
        content += f"## 📌 [{category}] {title}\n{summary}\n\n"

    content += "---\n오늘도 쌍둥이 낮잠 시간에 정리해봤어요. 내일도 함께 공부해요!"
    return content

# ✅ 전체 실행 함수
def generate_daily_post(rss_urls):
    topic_summaries = []
    for category, rss_url in rss_urls.items():
        articles = get_articles(rss_url, max_count=3)
        for article in articles:
            print(f"{category} - {article['title']}")
            text = get_article_text_bs4(article['link'])
            summary = summarize_article(article['title'], text)
            topic_summaries.append((category, article['title'], summary))
            time.sleep(2)

    post = create_blog_post(topic_summaries)
    file_name = f"blog_post_{datetime.now().strftime('%Y%m%d')}.txt"

    with open(file_name, "a", encoding="utf-8") as f:
        f.write(post)

    print(f"✅ 저장 완료: {file_name}")

# ▶ 실행
if __name__ == "__main__":
    # ✅ RSS 피드 (육아 / 재테크)]
    topic_arr = ["뉴스","육아","재테크"]

    for t in topic_arr:
        top_keyword = ht.search_keyword_trends(t)
        for top_key in top_keyword:
            rss_urls = {"{}": "https://news.google.com/rss/search?q={}&hl=ko&gl=KR&ceid=KR:ko".format(t,top_key)}

        generate_daily_post(rss_urls)
