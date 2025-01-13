import json
import httpx
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import urllib.parse
import urllib.request
import time
from pathlib import Path


def get_data(self, existing_data=None):
    """
    네이버 블로그 데이터를 수집합니다.

    Args:
        existing_data (list, optional): 기존 수집된 데이터 리스트. None이면 빈 리스트로 시작.

    Returns:
        list: 업데이트된 전체 데이터 리스트
    """
    if existing_data is None:
        existing_data = []

    # 기존 링크들의 집합 생성
    existing_links = {post['링크'] for post in existing_data}

    # 키워드 생성 및 검색
    keywords = generate_keywords()
    print(f"총 {len(keywords)}개의 검색 키워드가 생성되었습니다.")

    # 검색 기간 설정
    end_date = datetime.now()
    start_date = end_date - timedelta(days=1)
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')

    new_posts = []
    update_count = 0
    add_count = 0

    for keyword in keywords:
        print(f"\n키워드 '{keyword}' 검색 중...")
        blog_posts = get_blog_posts(keyword, self.CLIENT_ID, self.CLIENT_SECRET, existing_links)

        if blog_posts:
            period_posts = []

            for post in blog_posts:
                if post['link'] in existing_links:
                    continue

                post_date = datetime.strptime(post['postdate'], '%Y%m%d').strftime('%Y-%m-%d')

                if check_date_in_range(post_date, start_date_str, end_date_str):
                    title, content = get_blog_content(post['link'])

                    if title is None:
                        title = post['title']
                    if '<' in title and '>' in title:
                        title = BeautifulSoup(title, 'html.parser').get_text()

                    post_data = {
                        '블로그 제목': title,
                        '링크': post['link'],
                        '작성일자': post_date,
                        '상세내용': content or post['description']
                    }

                    period_posts.append(post_data)
                    existing_links.add(post['link'])
                    print(f"처리 중: {len(period_posts)}/{len(blog_posts)} - {title}")
                    time.sleep(1)

            new_posts.extend(period_posts)
            print(f"키워드 '{keyword}' 검색 완료: {len(period_posts)}개의 포스트 수집")
        else:
            print(f"키워드 '{keyword}' 검색 결과를 가져오는데 실패했습니다.")

    # 데이터 병합 및 중복 제거
    if new_posts:
        # 링크를 키로 하는 딕셔너리 생성
        data_dict = {post['링크']: post for post in existing_data}

        # 새로운 데이터 처리
        for post in new_posts:
            if post['링크'] in data_dict:
                old_date = datetime.strptime(data_dict[post['링크']]['작성일자'], '%Y-%m-%d')
                new_date = datetime.strptime(post['작성일자'], '%Y-%m-%d')

                if new_date >= old_date:
                    data_dict[post['링크']] = post
                    update_count += 1
            else:
                data_dict[post['링크']] = post
                add_count += 1

        # 결과를 리스트로 변환
        updated_data = list(data_dict.values())

        # JSON 파일 저장 (outputs 폴더에)
        output_dir = Path('outputs')
        output_dir.mkdir(exist_ok=True)

        filename = output_dir / f'jeju_realestate_{start_date_str}_{end_date_str}.json'
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(new_posts, f, ensure_ascii=False, indent=2)

        print(f"\n검색 기간: {start_date_str} ~ {end_date_str}")
        print(f"새로 추가된 포스트: {add_count}개")
        print(f"업데이트된 포스트: {update_count}개")
        print(f"누적 데이터 건수: {len(updated_data)}개")
        print(f"새로운 데이터가 {filename}에 저장되었습니다.")

        return updated_data
    else:
        print("\n검색된 결과가 없습니다.")
        return existing_data


def generate_keywords():
    """검색 키워드 조합을 생성합니다."""
    locations = ["제주도", "서귀포", "제주시"]
    categories = ["부동산", "토지", "주택", "아파트", "단독주택", "타운하우스", "상가"]
    deal_types = ["매매", "급매", "전세", "월세", "연세", "초급매", "급급매"]

    keywords = []
    for location in locations:
        for category in categories:
            for deal_type in deal_types:
                if category == "부동산":
                    keywords.append(f"{location} {category} {deal_type}")
                else:
                    keywords.append(f"{location} {category} {deal_type}")
    return keywords


def get_blog_posts(keyword, CLIENT_ID, CLIENT_SECRET, existing_links):
    """네이버 블로그 검색 API를 통해 블로그 포스트를 검색합니다."""
    encText = urllib.parse.quote(keyword)
    all_items = []
    display = 100
    total_count = 1000

    for start in range(1, total_count + 1, display):
        url = f"https://openapi.naver.com/v1/search/blog?query={encText}&display={display}&start={start}&sort=sim&queryType=post"

        request = urllib.request.Request(url)
        request.add_header("X-Naver-Client-Id", CLIENT_ID)
        request.add_header("X-Naver-Client-Secret", CLIENT_SECRET)

        try:
            response = urllib.request.urlopen(request)

            if response.getcode() == 200:
                response_body = response.read()
                search_result = json.loads(response_body.decode('utf-8'))

                if search_result['total'] < start:
                    break

                keywords_split = keyword.split()
                for item in search_result['items']:
                    if item['link'] in existing_links:
                        continue

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
    """블로그의 제목과 내용을 가져옵니다."""
    try:
        if 'blog.naver.com' not in blog_url:
            return None, None

        if '/PostView.naver' not in blog_url:
            parts = blog_url.split('blog.naver.com/')[-1].split('/')
            if len(parts) >= 2:
                blog_id = parts[0]
                log_no = parts[1]
            else:
                return None, None
        else:
            params = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(blog_url).query))
            log_no = params.get('logNo')
            blog_id = params.get('blogId')
            if not log_no or not blog_id:
                return None, None

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

            if not (title and content):
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
                        content = content_element.get_text(strip=True)

            return title, content

    except Exception as e:
        print(f"Error fetching blog content: {str(e)}")
        return None, None


def check_date_in_range(post_date, start_date, end_date):
    """게시물 날짜가 검색 기간 내에 있는지 확인합니다."""
    post_date = datetime.strptime(post_date, '%Y-%m-%d')
    start_date = datetime.strptime(start_date, '%Y-%m-%d')
    end_date = datetime.strptime(end_date, '%Y-%m-%d')
    return start_date <= post_date <= end_date