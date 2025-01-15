from googleapiclient.discovery import build
from datetime import datetime, timedelta
import pandas as pd
import json
import os
import time


def get_data():
    """YouTube 데이터 검색 및 JSON 변환 실행 함수"""
    try:
        # YouTube Data API 키 설정
        API_KEY = "AIzaSyCjiLLD24WJKiDp6czMcvpVeDMqsPErxcI"

        # 검색 키워드 정의
        search_queries = [
            "제주도 부동산",
            "제주도 부동산 매매",
            "제주도 부동산 경매",
            "제주도 부동산 급매"
        ]

        # 설정 로드
        config = load_config()

        # YouTube API 서비스 객체 생성
        youtube = build('youtube', 'v3', developerKey=API_KEY)

        # 검색 실행
        results = youtube_search(youtube, search_queries, config)

        # JSON 형식으로 변환
        json_results = convert_to_json(results)

        return json_results

    except Exception as e:
        print(f"\n실행 중 오류 발생: {str(e)}")
        return []

def load_config(config_file='search_config.json'):
    """설정 파일 로드"""
    if os.path.exists(config_file):
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
            config['processed_videos'] = set(config['processed_videos'])
            return config
    return {
        'last_search_time': '2025-01-15T00:00:00Z',
        'processed_videos': set(),
        'last_processed_index': 0
    }


def save_config(config, config_file='search_config.json'):
    """설정 파일 저장"""
    save_data = {
        'last_search_time': config['last_search_time'],
        'processed_videos': list(config['processed_videos']),
        'last_processed_index': config.get('last_processed_index', 0)
    }
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(save_data, f, ensure_ascii=False, indent=2)


def youtube_search(youtube, search_queries, config):
    """
    YouTube API를 사용하여 새로운 동영상 검색
    """
    results = []
    # 7일 전 시간으로 설정
    last_search_time = (datetime.utcnow() - timedelta(days=7)).isoformat() + 'Z'

    total_queries = len(search_queries)
    print(f"\n검색 시작: 총 {total_queries}개 중 0번째부터 시작")
    print("=" * 50)

    try:
        for idx, query in enumerate(search_queries):
            progress = (idx / total_queries) * 100
            print(f"\r진행률: {progress:.1f}% ({idx}/{total_queries}) - 현재 검색어: {query}", end="")

            try:
                print(f"\n검색 시도: {query}")
                print(f"검색 시작일: {last_search_time}")

                # 먼저 비디오 검색
                search_response = youtube.search().list(
                    q=query,
                    part='snippet',
                    type='video',
                    order='date',
                    maxResults=50,
                    publishedAfter=last_search_time
                ).execute()

                # 검색된 비디오들의 상세 정보 가져오기
                video_ids = [item['id']['videoId'] for item in search_response.get('items', [])]
                if video_ids:
                    videos_response = youtube.videos().list(
                        part='snippet',
                        id=','.join(video_ids)
                    ).execute()

                print(f"검색된 아이템 수: {len(search_response.get('items', []))}")

                # 비디오 ID를 키로 하는 상세 정보 딕셔너리 생성
                video_details = {}
                if video_ids:
                    for item in videos_response['items']:
                        video_details[item['id']] = item['snippet']

                for item in search_response.get('items', []):
                    video_id = item['id']['videoId']
                    if video_id not in config['processed_videos']:
                        config['processed_videos'].add(video_id)
                        # 상세 정보에서 전체 설명 가져오기
                        full_snippet = video_details.get(video_id, item['snippet'])
                        video_data = {
                            '검색어': query,
                            '제목': full_snippet['title'],
                            '설명': full_snippet['description'],
                            '게시일': pd.to_datetime(full_snippet['publishedAt']).strftime('%Y-%m-%d'),
                            '채널명': full_snippet['channelTitle'],
                            '비디오ID': video_id,
                            '링크': f"https://www.youtube.com/watch?v={video_id}"
                        }
                        results.append(video_data)

            except Exception as e:
                error_msg = f"검색 중 오류 발생 ({query}): {str(e)}"
                print(f"\n{error_msg}")

                if 'quotaExceeded' in str(e):
                    print("\n할당량 초과로 검색을 중단합니다.")
                    break

    finally:
        print("\n\n검색 완료!")
        print(f"총 {len(results)}개의 새로운 동영상을 찾았습니다.")

        if results:
            print("\n전체 검색 결과:")
            for video in results:  # 모든 결과 출력
                print("\n플랫폼: 유튜브")
                print(f"검색어: {video['검색어']}")
                print(f"제목: {video['제목']}")
                print(f"채널: {video['채널명']}")
                print(f"게시일: {video['게시일']}")
                print(f"링크: {video['링크']}")
                print(f"설명: {video['설명']}")

    return results


def convert_to_json(results):
    """검색 결과를 JSON 형식으로 변환"""
    json_results = []

    for video in results:
        json_item = {
            "플랫폼": "유튜브",
            "제목": video['제목'],
            "채널명": video['채널명'],
            "날짜": video['게시일'],
            "링크": video['링크'],
            "설명": video['설명']
        }
        json_results.append(json_item)

    return json_results