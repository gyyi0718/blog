# --- 기존 imports 아래에 추가 ---
import multi_site_crawler as msc
from urllib.parse import urljoin
from bs4 import BeautifulSoup



class HaeundaeParser(msc.SiteParser):
    """
    해운대구청 게시판: list.do / view.do 구조
    """
    def extract_post_links(self, html: str) -> list:
        soup = BeautifulSoup(html, "html.parser")
        links = []
        # view.do?boardId=BBS_0000004 가 들어간 a 태그 모두
        for a in soup.select('a[href*="view.do?boardId=BBS_0000004"]'):
            href = a['href']
            full = urljoin(self.config.detail_base, href)
            links.append(full)
        # 중복 제거
        return list(dict.fromkeys(links))

    def extract_attachment_links(self, html: str) -> list:
        soup = BeautifulSoup(html, "html.parser")
        files = []
        # 다운로드 링크만 (download.do)
        for a in soup.select('ul.download_list li a[href*="download.do"]'):
            href = a['href']
            # 파일명은 '2025년3월…xlsx' 앞부분만
            name = a.get_text(strip=True).split()[0]
            full = urljoin(self.config.detail_base, href)
            files.append((full, name))
        return files

# SiteConfig 생성
haeundae_config = msc.SiteConfig(
    name='해운대구청',
    list_url_template=(
        "https://www.haeundae.go.kr/board/list.do?"
        "boardId=BBS_0000004&menuCd=DOM_000000104004003000"
        "&paging=ok&startPage=1&pageIndex={page}"
    ),
    detail_base='https://www.haeundae.go.kr',
    # row_selector, title_selector, attach_selector는 파서가 직접 처리하므로 더미
    row_selector='',
    title_selector='',
    attach_selector='',
    pages=range(1, 6),
    output_csv='해운대구청_업무추진비.csv'
)

class SuyeongParser(msc.SiteParser):
    def extract_post_links(self, html: str) -> list:
        soup = BeautifulSoup(html, "html.parser")
        links = []
        for a in soup.select('a[href*="view.do?boardId=BBS_0000019"]'):
            links.append(urljoin(self.config.detail_base, a['href']))
        return list(dict.fromkeys(links))

    def extract_attachment_links(self, html: str) -> list:
        soup = BeautifulSoup(html, "html.parser")
        files = []
        for a in soup.select('ul.download_list li a[href*="download.do"]'):
            name = a.get_text(strip=True).split()[0]
            files.append((urljoin(self.config.detail_base, a['href']), name))
        return files

suyeong_config = msc.SiteConfig(
    name='수영구청',
    list_url_template=(
        "https://www.suyeong.go.kr/board/list.do?"
        "boardId=BBS_0000019&menuCd=…&paging=ok&startPage=1&pageIndex={page}"
    ),
    detail_base='https://www.suyeong.go.kr',
    row_selector='', title_selector='', attach_selector='',
    pages=range(1, 6),
    output_csv='수영구청_업무추진비.csv'
)


if __name__ == "__main__":
    haeundae_parser = HaeundaeParser(haeundae_config)
    haeundae_crawler = msc.Crawler(haeundae_config, haeundae_parser, download_dir="temp/해운대구청")
    haeundae_crawler.run(max_pages=2)

    # 수영 크롤러
    #suyeong_parser = SuyeongParser(suyeong_config)
    #suyeong_crawler = msc.Crawler(suyeong_config, suyeong_parser, download_dir="temp/수영구청")
    #suyeong_crawler.run(max_pages=5)