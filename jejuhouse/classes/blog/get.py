import json
import httpx
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import urllib.parse
import urllib.request
import time
from pathlib import Path


def get_data(self):
    """네이버 블로그 데이터를 수집합니다."""
    # 마지막 실행 데이터 로드
    last_run_time, collected_links, last_post_timestamp = load_last_run_data()

    # 검색 시작 시간 설정
    if last_post_timestamp:
        start_date = last_post_timestamp
        print(f"마지막 수집된 게시물 시간: {start_date.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        # 첫 실행이거나 타임스탬프가 없는 경우 현재 시간부터 5분 전까지 검색
        start_date = datetime.now() - timedelta(minutes=5)
        print("첫 실행 또는 마지막 타임스탬프 없음")

    end_date = datetime.now()
    print(f"검색 기간: {start_date.strftime('%Y-%m-%d %H:%M:%S')} ~ {end_date.strftime('%Y-%m-%d %H:%M:%S')}")

    # 키워드 생성 및 검색
    keywords = generate_keywords()
    print(f"총 {len(keywords)}개의 검색 키워드가 생성되었습니다.")

    new_posts = []
    latest_timestamp = last_post_timestamp  # 이번 실행에서 가장 최근 게시물의 타임스탬프

    for keyword in keywords:
        print(f"\n키워드 '{keyword}' 검색 중...")
        blog_posts = get_blog_posts(keyword, self)

        if blog_posts:
            for post in blog_posts:
                if post['link'] in collected_links:
                    continue

                # 블로그 내용과 타임스탬프 가져오기
                title, content, post_timestamp = get_blog_content(post['link'])

                # 타임스탬프를 얻지 못한 경우 API에서 제공하는 날짜 사용
                if post_timestamp is None:
                    post_timestamp = datetime.strptime(post['postdate'], '%Y%m%d')

                # 시간 기반 필터링
                if last_post_timestamp is None or post_timestamp > last_post_timestamp:
                    if title is None:
                        title = post['title']
                    if '<' in title and '>' in title:
                        title = BeautifulSoup(title, 'html.parser').get_text()

                    post_data = {
                        '플랫폼': '네이버블로그',
                        '블로그 제목': title,
                        'link': post['link'],
                        '작성일자': post_timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                        '상세내용': content or post['description']
                    }

                    new_posts.append(post_data)
                    collected_links.add(post['link'])
                    print(f"새로운 포스트 발견: {title} ({post_timestamp.strftime('%Y-%m-%d %H:%M:%S')})")

                    # 최신 타임스탬프 업데이트
                    if latest_timestamp is None or post_timestamp > latest_timestamp:
                        latest_timestamp = post_timestamp

                    time.sleep(0.1)

        else:
            print(f"키워드 '{keyword}' 검색 결과를 가져오는데 실패했습니다.")

    # 새로운 데이터 저장
    if new_posts:
        # 작성일자 기준으로 정렬
        new_posts.sort(key=lambda x: x['작성일자'])

        output_dir = Path('outputs')
        output_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = output_dir / f'jeju_realestate_{timestamp}.json'
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(new_posts, f, ensure_ascii=False, indent=2)

        print(f"\n새로 수집된 포스트: {len(new_posts)}개")
        print(f"새로운 데이터가 {filename}에 저장되었습니다.")
        if latest_timestamp:
            print(f"마지막 게시물 작성 시간: {latest_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print("\n새로 수집된 데이터가 없습니다.")

        # 마지막 실행 정보 업데이트 (최신 타임스탬프 포함)
    save_last_run_data(collected_links, latest_timestamp)

    return new_posts

def load_last_run_data():
    """마지막 실행 시간과 수집된 링크들, 마지막 게시물 타임스탬프를 로드합니다."""
    output_dir = Path('outputs')
    output_dir.mkdir(exist_ok=True)
    last_run_file = output_dir / 'last_run.json'

    if last_run_file.exists():
        with open(last_run_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            last_timestamp = None
            if data.get('last_post_timestamp'):
                try:
                    last_timestamp = datetime.strptime(
                        data['last_post_timestamp'],
                        '%Y-%m-%d %H:%M:%S'
                    )
                except ValueError:
                    last_timestamp = None
            return (
                data.get('last_run_time'),
                set(data.get('collected_links', [])),
                last_timestamp
            )
    return None, set(), None


def save_last_run_data(collected_links, last_timestamp):
    """현재 실행 시간과 수집된 링크들, 마지막 게시물 타임스탬프를 저장합니다."""
    output_dir = Path('outputs')
    last_run_file = output_dir / 'last_run.json'

    data = {
        'last_run_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'collected_links': list(collected_links),
        'last_post_timestamp': last_timestamp.strftime('%Y-%m-%d %H:%M:%S') if last_timestamp else None
    }
    with open(last_run_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def generate_keywords():
    """검색 키워드 조합을 생성합니다."""
    locations = ["제주도", "서귀포", "제주시", "제주"]
    categories = ["부동산", "토지", "주택", "아파트", "단독주택", "타운하우스", "상가", "빌딩", "건물",
                  "사무실", "공장", "창고", "과수원", "다가구", "전원주택", "농가주택", "점포", "임야", "재개발",
                  "모텔", "펜션", "숙박", "호텔", "원룸", "투룸", "쓰리룸", "빌라", "연립", "다세대"]
    deal_types = ["매매", "급매", "전세", "월세", "연세", "년세", "임대", "초급매", "급급매", "단기임대", "분양"]

    keywords = []
    for location in locations:
        for category in categories:
            for deal_type in deal_types:
                if category == "부동산":
                    keywords.append(f"{location} {category} {deal_type}")
                else:
                    keywords.append(f"{location} {category} {deal_type}")
    return keywords


def get_blog_posts(keyword, self):
    """네이버 블로그 검색 API를 통해 블로그 포스트를 검색합니다."""
    encText = urllib.parse.quote(keyword)
    all_items = []
    display = 100
    total_count = 1000

    for start in range(1, total_count + 1, display):
        url = f"https://openapi.naver.com/v1/search/blog?query={encText}&display={display}&start={start}&sort=sim&queryType=post"

        request = urllib.request.Request(url)
        request.add_header("X-Naver-Client-Id", self.CLIENT_ID)
        request.add_header("X-Naver-Client-Secret", self.CLIENT_SECRET)

        try:
            response = urllib.request.urlopen(request)

            if response.getcode() == 200:
                response_body = response.read()
                search_result = json.loads(response_body.decode('utf-8'))

                if search_result['total'] < start:
                    break

                keywords_split = keyword.split()
                for item in search_result['items']:
                    title = item['title']
                    description = item['description']

                    if '<' in title and '>' in title:
                        title = BeautifulSoup(title, 'html.parser').get_text()
                    if '<' in description and '>' in description:
                        description = BeautifulSoup(description, 'html.parser').get_text()

                    all_keywords_present = all(
                        (kw.lower() in title.lower() or kw.lower() in description.lower())
                        for kw in keywords_split
                    )

                    if all_keywords_present:
                        all_items.append(item)

                print(f"검색 진행 중: {len(all_items)}개 수집 완료")
                time.sleep(0.1)

            else:
                print(f"Error Code: {response.getcode()}")
                break

        except Exception as e:
            print(f"Error fetching results: {str(e)}")
            break

    return all_items


def get_blog_content(blog_url):
    """블로그의 제목과 내용, 작성시간을 가져옵니다."""
    try:
        if 'blog.naver.com' not in blog_url:
            return None, None, None

        if '/PostView.naver' not in blog_url:
            parts = blog_url.split('blog.naver.com/')[-1].split('/')
            if len(parts) >= 2:
                blog_id = parts[0]
                log_no = parts[1]
            else:
                return None, None, None
        else:
            params = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(blog_url).query))
            log_no = params.get('logNo')
            blog_id = params.get('blogId')
            if not log_no or not blog_id:
                return None, None, None

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

            # 작성 시간 추출 시도
            timestamp = None
            timestamp_selectors = [
                '.se_publishDate',  # SE-시리즈 에디터
                '.date',  # 구형 에디터
                '.blog_date',  # 모바일 버전
                '.write_date',  # 다른 버전
                '.se-date'  # 최신 에디터
            ]

            for selector in timestamp_selectors:
                time_element = soup.select_one(selector)
                if time_element:
                    timestamp_text = time_element.get_text(strip=True)
                    try:
                        # 다양한 형식의 날짜/시간 파싱 시도
                        if '.' in timestamp_text:
                            # '2024. 1. 13. 14:30' 형식
                            timestamp = datetime.strptime(timestamp_text.replace(' ', ''), '%Y.%m.%d.%H:%M')
                        elif ':' in timestamp_text:
                            # '2024-01-13 14:30' 형식
                            timestamp = datetime.strptime(timestamp_text, '%Y-%m-%d %H:%M')
                        break
                    except ValueError:
                        continue

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
                    content = content_element.get_text(strip=True)
                    break

            if not (title and content and timestamp):
                mobile_url = f"https://m.blog.naver.com/PostView.naver?blogId={blog_id}&logNo={log_no}"
                response = client.get(mobile_url, headers=headers)
                soup = BeautifulSoup(response.text, 'html.parser')

                if not timestamp:
                    time_element = soup.select_one('.blog_date, .date')
                    if time_element:
                        timestamp_text = time_element.get_text(strip=True)
                        try:
                            timestamp = datetime.strptime(timestamp_text, '%Y.%m.%d. %H:%M')
                        except ValueError:
                            pass

                if not title:
                    title_element = soup.select_one('.se_title, .tit_h3, h2.se_textarea')
                    if title_element:
                        title = title_element.get_text(strip=True)

                if not content:
                    content_element = soup.select_one('.se_component_wrap, .post_ct')
                    if content_element:
                        content = content_element.get_text(strip=True)

            return title, content, timestamp

    except Exception as e:
        print(f"Error fetching blog content: {str(e)}")
        return None, None, None