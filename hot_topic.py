from serpapi import GoogleSearch
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
# SerpApi API 키 (자신의 API 키로 대체)
API_KEY = '42f91da57272e7d18f80838dc2e83b9d20727f40d3f7bce5968bf709d1882be7'

query_arr = ["뉴스", "재테크", "육아"]
# 기간 설정 (예: 지난 7일)
date_range = "today 1-d"

# 결과를 저장할 리스트 초기화
all_output_lines = []

def search_keyword_trends(topic):
    keyword_arr = []
    # 관련 검색어(RELATED_QUERIES) 요청 파라미터 설정
    params_queries = {
        "engine": "google_trends",
        "hl": "ko",
        "geo": "KR",
        "q": topic,
        "date_range": date_range,
        "api_key": API_KEY,
        "data_type": "RELATED_QUERIES"
    }

    search = GoogleSearch(params_queries)
    results = search.get_dict()

    # 카테고리(검색어) 헤더 추가
    all_output_lines.append("======== 기본 검색어 '{}' ========".format(topic))

    # Top 관련 검색어 처리 (상위 5개 항목)
    all_output_lines.append(">> Top 관련 검색어:")
    if results.get('related_queries') and results['related_queries'].get("top"):
        for item in results['related_queries']["top"][:5]:
            all_output_lines.append("관련 검색어: {}".format(item.get("query", "")))
            keyword_arr.append(item.get("query", ""))
            all_output_lines.append("인기도 (값): {}".format(item.get("value", "")))
            all_output_lines.append("링크: {}".format(item.get("link", "")))
            all_output_lines.append("SerpApi 링크: {}".format(item.get("serpapi_link", "")))
            all_output_lines.append("---")
    else:
        all_output_lines.append("Top 관련 검색어 데이터가 없습니다.")

    # Rising 관련 검색어 처리 (상위 5개 항목)
    all_output_lines.append(">> Rising 관련 검색어:")
    if results.get('related_queries') and results['related_queries'].get("rising"):
        for item in results['related_queries']["rising"][:5]:
            all_output_lines.append("관련 검색어: {}".format(item.get("query", "")))
            all_output_lines.append("인기도 (값): {}".format(item.get("value", "")))
            all_output_lines.append("링크: {}".format(item.get("link", "")))
            all_output_lines.append("SerpApi 링크: {}".format(item.get("serpapi_link", "")))
            all_output_lines.append("---")
    else:
        all_output_lines.append("Rising 관련 검색어 데이터가 없습니다.")

    # 각 카테고리 끝에 빈 줄 추가
    all_output_lines.append("\n")

    # 현재 날짜를 포함한 파일명 생성 (예: related_queries_20250410_combined.txt)
    today_str = datetime.now().strftime('%Y%m%d')
    filename = "{}_{}_combined.txt".format(topic,today_str)

    # 파일로 결과 저장
    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(all_output_lines))

    print("모든 관련 검색어 데이터가 {}에 저장되었습니다.".format(filename))

    return keyword_arr