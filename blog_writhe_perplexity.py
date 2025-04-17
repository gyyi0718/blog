import os
import re
import openai
from datetime import datetime
import hot_topic as ht

# 환경 변수 또는 직접 API 키 입력
api_key ="my-key"  # 또는 "sk-your-perplexity-api-key"

client = openai.OpenAI(
    api_key=api_key,
    base_url="https://api.perplexity.ai"
)
query_arr = ["뉴스","재테크","육아","맛집"]


def make_prompt(topic, keywords):
    blog_sections_prompt = {
        "육아": (
            "최신 육아 트렌드, 인기 이슈, 부모들의 경험, 육아 팁 등을 포함합니다. "
            "각 섹션에서는 독자들이 실질적인 도움을 받을 수 있도록 구체적인 사례와 조언을 포함해 주세요."
            "Do not include any citation markers (such as [1], [2], etc.) in the body of the article. Instead, at the end of the article, provide a separate list of only the valid reference URLs you have used. If a reference does not have a valid URL, do not include any reference marker or content for it in the article. The article should be written clearly and naturally."

        ),
        "재테크": (
            "재테크 동향, 투자 방법, 금융 시장 분석, 전문가 의견 및 성공 사례를 구체적으로 소개합니다. "
            "데이터나 구체적 숫자를 포함해서 신뢰성 있는 정보를 제공해 주세요."
            "Do not include any citation markers (such as [1], [2], etc.) in the body of the article. Instead, at the end of the article, provide a separate list of only the valid reference URLs you have used. If a reference does not have a valid URL, do not include any reference marker or content for it in the article. The article should be written clearly and naturally."

        ),
        "인공지능": (
            "최신 인공지능 기술 발전, 주요 연구 성과, 산업 내 활용 사례와 AI가 사회에 미치는 영향 및 미래 전망을 분석합니다. "
            "전문 용어는 쉽게 풀어서 설명하고, 예시와 비유를 활용해 독자들이 이해하기 쉽게 작성해 주세요."
            "Do not include any citation markers (such as [1], [2], etc.) in the body of the article. Instead, at the end of the article, provide a separate list of only the valid reference URLs you have used. If a reference does not have a valid URL, do not include any reference marker or content for it in the article. The article should be written clearly and naturally."

        ),
        "뉴스": (
            "최신 뉴스 이슈를 간결하게 요약하고, 중요한 사건들의 배경과 영향을 평가합니다. "
            "정확하고 객관적인 분석과 함께 관련 링크나 참고 자료가 있다면 함께 언급해 주세요."
            "Do not include any citation markers (such as [1], [2], etc.) in the body of the article. Instead, at the end of the article, provide a separate list of only the valid reference URLs you have used. If a reference does not have a valid URL, do not include any reference marker or content for it in the article. The article should be written clearly and naturally."

        ),
        "맛집":(
            "이 프롬프트는 제목, 도입부, 본론(맛집 정보, 방송 소개 및 체험, 추천 포인트) 그리고 결론(요약 및 콜 투 액션)을 포함하도록 구성되어 있습니다."
            "한글로 작성되어 있으며, 글의 구조와 스토리텔링 방식도 명확하게 지시되어 있어 자동 생성된 글이 방문자들에게 매력적으로 다가갈 수 있도록 돕습니다."
            "Do not include any citation markers (such as [1], [2], etc.) in the body of the article. Instead, at the end of the article, provide a separate list of only the valid reference URLs you have used. If a reference does not have a valid URL, do not include any reference marker or content for it in the article. The article should be written clearly and naturally."

        )
    }

    prompt = blog_sections_prompt[i]
    messages =[{"role": "system", "content": "당신은 유능한 블로그 작성자이자 뉴스 요약 전문가입니다."},{"role": "user", "content": prompt}]
    return messages

def append_placeholder_links(content):
    # 본문에서 모든 참고 번호(예: [1], [2], ...)를 찾음
    refs = re.findall(r'\[(\d+)\]', content)
    unique_refs = sorted(set(refs), key=int)

    # 만약 참고 링크 블록이 있다면 이를 찾아봄 (예: 맨 아래 줄들)
    # 여기서는 단순하게 "[번호]"로 시작하는 줄을 참고 링크 목록으로 간주
    existing_links = re.findall(r'^\[(\d+)\].+', content, re.MULTILINE)

    # 누락된 번호를 찾음
    missing_refs = [ref for ref in unique_refs if ref not in existing_links]

    if missing_refs:
        placeholders = "\n\n" + "\n".join([f"[{ref}] Link not available." for ref in missing_refs])
        content += placeholders
    content+="\n\n"
    return content





if __name__ == "__main__":


    for i in query_arr:
        keyword_arr = ht.search_keyword_trends(i)
        print(keyword_arr)

        messages = make_prompt(i, keyword_arr)
        try:
            response = client.chat.completions.create(
                model="sonar-pro",  # Perplexity API 문서에 명시된 허용 모델 사용 (예: "sonar-pro")
                messages=messages,
                max_tokens=1024,
                temperature=0.7
            )

            # 응답에서 요약과 참고 링크가 모두 포함된 최종 내용 추출 (객체의 속성 방식)
            final_content = response.choices[0].message.content
            final_content = append_placeholder_links(final_content)

            # 날짜 기반 파일명 생성 (예: blog_post_20250410.txt)
            file_name = f"blog_post_{datetime.now().strftime('%Y%m%d')}.txt"
            with open(file_name, "a", encoding="utf-8") as f:
                f.write(final_content)
            print(f"✅ 저장 완료: {file_name}")

        except Exception as e:
            print(f"[오류 발생] {str(e)}")
        
