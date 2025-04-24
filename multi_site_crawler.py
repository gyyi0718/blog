import os
import time
import shutil
import zipfile
import requests
import pandas as pd
import pdfplumber
import xml.etree.ElementTree as ET
import re
from typing import List, Tuple
from pathlib import Path
from collections import Counter
from urllib.parse import urljoin, unquote
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import csv


class SiteConfig:
    """
    Configuration for a single site to crawl.
    - list_url_template: URL with a {page} placeholder for pagination.
    - detail_base: Base URL to resolve relative detail links.
    - row_selector: CSS selector for rows on the list page.
    - title_selector: CSS selector within a row to get the title/link.
    - attach_selector: CSS selector on detail page for attachment links.
    - pages: iterable of page numbers to crawl.
    - output_csv: filename for final report.
    """
    def __init__(
        self,
        name: str,
        list_url_template: str,
        detail_base: str,
        row_selector: str,
        title_selector: str,
        attach_selector: str,
        pages=range(1, 6),
        output_csv="usage_report.csv"
    ):
        self.name = name
        self.list_url_template = list_url_template
        self.detail_base = detail_base
        self.row_selector = row_selector
        self.title_selector = title_selector
        self.attach_selector = attach_selector
        self.pages = pages
        self.output_csv = output_csv


class SiteParser:
    """
    Base parser: override methods for site-specific extraction rules.
    """
    def __init__(self, config: SiteConfig):
        self.config = config

    def extract_post_links(self, html: str):
        raise NotImplementedError

    def extract_attachment_links(self, html: str):
        raise NotImplementedError


class DefaultParser(SiteParser):
    """
    Default parser assumes similar structure across sites.
    """
    def extract_post_links(self, html: str):
        soup = BeautifulSoup(html, 'html.parser')
        rows = soup.select(self.config.row_selector)
        links = []
        for row in rows:
            a = row.select_one(self.config.title_selector)
            if a and a.get('href'):
                links.append(urljoin(self.config.detail_base, a['href']))
        return links

    def extract_attachment_links(self, html: str):
        soup = BeautifulSoup(html, 'html.parser')
        attachments = []
        for a in soup.select(self.config.attach_selector):
            href = a.get('href')
            name = a.get_text(strip=True) or Path(href).name
            if href:
                attachments.append((urljoin(self.config.detail_base, href), name))
        return attachments

class GeumcheonParser(SiteParser):
    row_selector = 'table.p-table.simple tbody tr'
    title_selector = 'td.p-subject a'
    attach_selector = 'a.p-attach__link'

    def extract_post_links(self, html: str) -> List[str]:
        soup = BeautifulSoup(html, "html.parser")
        rows = soup.select(self.row_selector)
        links = []
        for row in rows:
            a_tag = row.select_one(self.title_selector)
            if not (a_tag and a_tag.get('href')):
                continue
            # 선행 슬래시 제거
            href = a_tag['href']
            # 기본 detail_base: "https://www.geumcheon.go.kr"
            # href 가 "selectBbsNttView.do?..." 형태라면 portal/ 을 붙여서 절대경로 생성

            if href.startswith('/'):
                full_url = urljoin(self.config.detail_base, href)
            else:
                full_url = urljoin(self.config.detail_base + '/portal/', href.lstrip('/'))
            links.append(full_url)
        return links

    def extract_attachment_links(self, html: str) -> List[Tuple[str, str]]:
        soup = BeautifulSoup(html, "html.parser")
        files = []
        for a in soup.select(self.attach_selector):
            href = a.get('href')
            name = a.get_text(strip=True)
            if not href:
                continue
            href = href.lstrip('/')
            full_url = f"{self.config.detail_base}/{href}"
            files.append((full_url, name))
        return files

class Crawler:
    """
    Core crawler: fetch list pages, detail pages, download attachments, extract data.
    """
    def __init__(self, config: SiteConfig, parser: SiteParser, download_dir: str = 'temp'):
        self.config = config
        self.parser = parser
        self.download_dir = Path(download_dir) / config.name
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.counter = Counter()

        chrome_opts = Options()
        chrome_opts.add_argument('--headless')
        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_opts
        )

    def fetch_html(self, url: str) -> str:
        try:
            return requests.get(url, timeout=10).text
        except Exception as e:
            print(f"Failed to fetch {url}: {e}")
            return ''

    def download_file(self, url: str, name_hint: str) -> Path:
        try:
            resp = requests.get(url, stream=True, timeout=10)
            resp.raise_for_status()
            # determine filename
            cd = resp.headers.get('Content-Disposition','')
            if 'filename=' in cd:
                fname = unquote(cd.split('filename=')[-1].strip('"'))
            else:
                fname = Path(name_hint).name or Path(url).name
            safe_name = re.sub(r'[\\/:*?"<>|]', '_', fname)
            out_path = self.download_dir / safe_name
            with open(out_path, 'wb') as f:
                for chunk in resp.iter_content(8192): f.write(chunk)
            print(f"Downloaded: {out_path}")
            return out_path
        except Exception as e:
            print(f"Download error {url}: {e}")
            return None

    def clean_name(self, name: str) -> str:
        # (주), ㈜, 주식회사 제거
        name = re.sub(r"\(?㈜?\s*주식회사\)?", "", name)
        name = re.sub(r"\(?㈜?\)?", "", name)
        name = re.sub(r"\(?주\)?", "", name)
        # 괄호 안 전체 제거 (줄바꿈 포함)
        name = re.sub(r"\([^)]*\)", "", name)
        name = name.replace('"','')
        # 여러 공백·줄바꿈을 하나의 스페이스로 정리
        return re.sub(r"\s+", " ", name).strip()

    def extract_from_file(self, path: Path):
        ext = path.suffix.lower()
        try:
            if ext in ('.xls', '.xlsx'):
                df = pd.read_excel(path)
                cols = [c for c in df.columns if any(k in c for k in ['사용처','사용장소','장소'])]
                for col in cols:
                    for v in df[col].dropna().astype(str):
                        name = self.clean_name(name=v)
                        if 1 < len(name) < 50: self.counter[name] += 1
            elif ext == '.pdf':
                with pdfplumber.open(path) as pdf:
                    for pg in pdf.pages:
                        for tbl in pg.extract_tables() or []:
                            df = pd.DataFrame(tbl[1:], columns=tbl[0])
                            for col in df.columns:
                                if any(k in col for k in ['사용처','사용장소','장소']):
                                    for v in df[col].dropna().astype(str):
                                        name = self.clean_name(name=v)
                                        if 1 < len(name) < 50: self.counter[name] += 1
            elif ext == '.hwpx':
                tmp = self.download_dir / '_hwpx'
                with zipfile.ZipFile(path) as zp:
                    zp.extractall(tmp)
                xmlf = tmp / 'Contents' / 'section0.xml'
                tree = ET.parse(xmlf)
                for t in tree.iter():
                    if t.tag.endswith('}t') and t.text:
                        text = t.text.strip()
                        if any(k in text for k in ['사용처','사용장소','장소']):
                            name = self.clean_name(text)
                            if 1 < len(name) < 50: self.counter[name] += 1
                shutil.rmtree(tmp)
            else:
                print(f"Unsupported format: {path}")
        except Exception as e:
            print(f"Error parsing {path}: {e}")

    def run(self, max_pages: int = None):
        pages = self.config.pages if max_pages is None else range(1, max_pages+1)
        for p in pages:
            list_url = self.config.list_url_template.format(page=p)
            print(f"Crawling list page: {list_url}")
            html = self.fetch_html(list_url)
            if not html: continue

            links = self.parser.extract_post_links(html)
            for post in links:
                print(f"Visiting post: {post}")
                self.driver.get(post)
                time.sleep(1)
                page_html = self.driver.page_source
                attaches = self.parser.extract_attachment_links(page_html)
                for url, hint in attaches:
                    fpath = self.download_file(url, hint)
                    if fpath: self.extract_from_file(fpath)
        # save report
        df = pd.DataFrame(self.counter.most_common(), columns=['place','count'])
        df.to_csv(
            self.config.output_csv,
            index=False,
            encoding='utf-8-sig',
            quoting=csv.QUOTE_NONE,  # 따옴표 감싸기 없이
            escapechar='\\'  # 이스케이프 문자 지정
        )
        print(f"Report saved to {self.config.output_csv}")

    def cleanup(self):
        if self.download_dir.exists():
            shutil.rmtree(self.download_dir)
            print(f"Cleaned up download dir: {self.download_dir}")


if __name__ == '__main__':
    geumcheon_config = SiteConfig(
        name="금천구청",
        list_url_template=(
            "https://www.geumcheon.go.kr/portal/selectBbsNttList.do"
            "?bbsNo=86&key=269&id=&searchCtgry=&pageUnit=10"
            "&searchCnd=all&searchKrwd=&integrDeptCode="
            "&searchDeptCode=&pageIndex={page}"
        ),
        # '/portal'까지 꼭 포함
        detail_base="https://www.geumcheon.go.kr/portal/",
        row_selector="table.p-table.simple tbody tr",
        title_selector="td.p-subject a",
        attach_selector="a.p-attach__link",
        pages=range(18, 83),
        output_csv="금천구청_업무추진비.csv"
    )
    #18, 83 -> 2024.01~12 까지의 page 범위
    parser = DefaultParser(geumcheon_config)
    crawler = Crawler(geumcheon_config, parser)
    crawler.run(max_pages=None)
    crawler.cleanup()
