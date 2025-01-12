import json
import httpx
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import urllib.parse
import urllib.request
import time


def get_blog_posts(self, keyword, total_count=1000):
    """네이버 블로그 검색 API를 통해 블로그 포스트를 검색합니다."""
    encText = urllib.parse.quote(keyword)
    all_items = []
    display = 100  # 한 번에 가져올 수 있는 최대 개수

    # total_count만큼 반복하여 결과 수집
    for start in range(1, total_count + 1, display):
        # 페이징 처리를 위한 start 파라미터 추가
        url = f"https://openapi.naver.com/v1/search/blog?query={encText}&display={display}&start={start}&sort=sim&queryType=post"

        request = urllib.request.Request(url)
        request.add_header("X-Naver-Client-Id", CLIENT_ID)
        request.add_header("X-Naver-Client-Secret", CLIENT_SECRET)

        try:
            response = urllib.request.urlopen(request)

            if response.getcode() == 200:
                response_body = response.read()
                search_result = json.loads(response_body.decode('utf-8'))

                # 검색된 전체 개수가 start보다 작으면 종료
                if search_result['total'] < start:
                    break

                # 검색어 포함 여부를 확인하여 필터링
                keywords = keyword.split()

                for item in search_result['items']:
                    # HTML 태그가 있는 경우에만 BeautifulSoup 사용
                    title = item['title']
                    description = item['description']

                    if '<' in title and '>' in title:
                        title = BeautifulSoup(title, 'html.parser').get_text()
                    if '<' in description and '>' in description:
                        description = BeautifulSoup(description, 'html.parser').get_text()

                    # 모든 키워드가 제목이나 설명에 포함되어 있는지 확인
                    all_keywords_present = all(
                        (kw.lower() in title.lower() or kw.lower() in description.lower())
                        for kw in keywords
                    )

                    if all_keywords_present:
                        all_items.append(item)

                print(f"검색 진행 중: {len(all_items)}개 수집 완료")

                # API 호출 제한을 위한 딜레이
                time.sleep(0.1)

            else:
                print(f"Error Code: {response.getcode()}")
                break

        except Exception as e:
            print(f"Error fetching results: {str(e)}")
            break

    return all_items


def get_blog_content(blog_url):
    """블로그의 제목과 내용을 가져옵니다."""
    try:
        # 네이버 블로그 URL에서 blog_id와 log_no 추출
        if 'blog.naver.com' not in blog_url:
            return None, None

        # blog.naver.com/{blog_id}/{log_no} 형식인 경우
        if '/PostView.naver' not in blog_url:
            parts = blog_url.split('blog.naver.com/')[-1].split('/')
            if len(parts) >= 2:
                blog_id = parts[0]
                log_no = parts[1]
            else:
                return None, None
        # PostView.naver 형식인 경우
        else:
            params = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(blog_url).query))
            log_no = params.get('logNo')
            blog_id = params.get('blogId')
            if not log_no or not blog_id:
                return None, None

        # 실제 블로그 글 URL 생성
        view_url = f"https://blog.naver.com/PostView.naver?blogId={blog_id}&logNo={log_no}"

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
        }

        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            response = client.get(view_url, headers=headers)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # 제목 추출
            title_selectors = [
                '.se-title-text',
                '.se_title .se_textView',
                '.itemSubjectBoldfont',
                'div.se-module-text h3',
                '.se-fs-',
                '.pcol1',
                '.se-title h3'
            ]

            title = None
            for selector in title_selectors:
                title_element = soup.select_one(selector)
                if title_element:
                    title = title_element.get_text(strip=True)
                    break

            # 본문 내용 추출
            content_selectors = [
                'div.se-main-container',
                'div#postViewArea',
                'div.se_component_wrap',
                'div.post-view',
                'div.post_content'
            ]

            content = None
            for selector in content_selectors:
                content_element = soup.select_one(selector)
                if content_element:
                    content = str(content_element)
                    break

            if title and content:
                return title, content

            # 모바일 버전 시도
            mobile_url = f"https://m.blog.naver.com/PostView.naver?blogId={blog_id}&logNo={log_no}"
            response = client.get(mobile_url, headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')

            if not title:
                title_element = soup.select_one('.se_title, .tit_h3, h2.se_textarea')
                if title_element:
                    title = title_element.get_text(strip=True)

            if not content:
                content_element = soup.select_one('.se_component_wrap, .post_ct')
                if content_element:
                    content = str(content_element)

            return title, content

    except Exception as e:
        print(f"Error fetching blog content: {str(e)}")
        return None, None


def get_date_range(period):
    """검색 기간의 시작일과 종료일을 계산합니다."""
    today = datetime.now()

    if period == '7일':
        start_date = today - timedelta(days=7)
    elif period == '1개월':
        start_date = today - timedelta(days=30)
    elif period == '3개월':
        start_date = today - timedelta(days=90)
    elif period == '6개월':
        start_date = today - timedelta(days=180)
    elif period == '1년':
        start_date = today - timedelta(days=365)
    else:  # 기본값: 오늘
        start_date = today

    return start_date.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d')


def check_date_in_range(post_date, start_date, end_date):
    """게시물 날짜가 검색 기간 내에 있는지 확인합니다."""
    post_date = datetime.strptime(post_date, '%Y-%m-%d')
    start_date = datetime.strptime(start_date, '%Y-%m-%d')
    end_date = datetime.strptime(end_date, '%Y-%m-%d')

    return start_date <= post_date <= end_date


def generate_keywords():
    """검색 키워드 조합을 생성합니다."""
    # 지역 키워드
    locations = ["제주도", "서귀포", "제주시"]

    # 부동산 종류
    categories = ["부동산", "토지", "주택", "아파트", "원룸", "단독주택", "타운하우스", "상가"]

    # 거래 유형
    deal_types = ["매매", "급매", "전세", "월세", "년세", "초급매", "급급매"]

    # 키워드 조합 생성
    keywords = []
    for location in locations:
        for category in categories:
            for deal_type in deal_types:
                if category == "부동산":
                    keywords.append(f"{location} {category} {deal_type}")
                else:
                    # 부동산이 아닌 경우 "부동산" 단어 생략
                    keywords.append(f"{location} {category} {deal_type}")

    return keywords


def main(period="오늘"):
    """
    네이버 블로그를 검색하고 결과를 저장합니다.

    Args:
        period (str): 검색 기간 ('오늘', '7일', '1개월', '3개월', '6개월', '1년')
    """
    # 키워드 생성
    keywords = generate_keywords()
    print(f"총 {len(keywords)}개의 검색 키워드가 생성되었습니다.")

    start_date, end_date = get_date_range(period)
    all_posts = []

    # 각 키워드별로 검색 수행
    for keyword in keywords:
        print(f"\n키워드 '{keyword}' 검색 중...")

        # 검색 결과 가져오기 (최대 1000개)
        blog_posts = get_blog_posts(keyword, total_count=1000)

        if blog_posts:
            # 해당 기간의 포스트만 필터링하고 상세 내용 수집
            period_posts = []

            for post in blog_posts:
                # 날짜 형식 변환
                post_date = datetime.strptime(post['postdate'], '%Y%m%d').strftime('%Y-%m-%d')

                if check_date_in_range(post_date, start_date, end_date):
                    # 블로그 제목과 내용 가져오기
                    title, content = get_blog_content(post['link'])

                    if title is None:  # 제목을 찾지 못한 경우 API에서 받은 제목 사용
                        title = post['title']
                    if '<' in title and '>' in title:  # HTML 태그 제거
                        title = BeautifulSoup(title, 'html.parser').get_text()

                    post_data = {
                        '검색어': keyword,
                        '블로그 제목': title,
                        '링크': post['link'],
                        '작성일자': post_date,
                        '상세내용': content or post['description']
                    }

                    period_posts.append(post_data)
                    print(f"처리 중: {len(period_posts)}/{len(blog_posts)} - {title}")

                    # API 호출 제한을 위한 딜레이
                    time.sleep(1)

            all_posts.extend(period_posts)
            print(f"키워드 '{keyword}' 검색 완료: {len(period_posts)}개의 포스트 수집")
        else:
            print(f"키워드 '{keyword}' 검색 결과를 가져오는데 실패했습니다.")

    if all_posts:
        # 결과를 JSON 파일로 저장
        filename = f'jeju_realestate_{start_date}_{period}.json'
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(all_posts, f, ensure_ascii=False, indent=2)

        print(f"\n검색 기간: {start_date} ~ {end_date}")
        print(f"총 {len(all_posts)}개의 포스트를 수집했습니다.")
        print(f"결과가 {filename}에 저장되었습니다.")
    else:
        print("\n검색된 결과가 없습니다.")


if __name__ == "__main__":
    main()