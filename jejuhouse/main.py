from classes.auction import Auction
from classes.blog import NaverBlog
from classes.oiljang import OilJang
from classes.kyocharo import Kyocharo
from classes.youtube import Youtube
from lib.telegram import TelegramSender
import json
import time
import os
from datetime import datetime

# 설정
SENT_DATA_FILE = "sent_data.json"
CHECK_INTERVAL = 3600  # 1시간(초 단위)


def format_data(o_data, k_data):
    sample_data = {
        '오일장': o_data[:1] if o_data else [],
        '교차로': k_data[:1] if k_data else []
    }
    formatted_json = json.dumps(sample_data, ensure_ascii=False, indent=2)
    print(formatted_json)


def filter_properties_by_keyword(data):
    urgent_sales = []
    for property in data:
        if '매물명' in property and '급매' in property['매물명'] and (
                '아파트' or '토지' or '임야' or '원룸' or '투룸' or '쓰리룸' or '오피스텔') not in property['매물종류']:
            urgent_sales.append(property)
    return urgent_sales


def send_urgent_properties_to_telegram(properties):
    telegram = TelegramSender()
    for property in properties:
        try:
            message = telegram.format_property_message(property)
            response = telegram.send_message(message)

            if response.get('ok'):
                print(f"성공적으로 전송됨: {property['매물명']}")
            else:
                print(f"전송 실패: {property['매물명']}, 에러: {response.get('description')}")
        except Exception as e:
            print(f"에러 발생: {str(e)}")


def load_sent_data():
    try:
        if os.path.exists(SENT_DATA_FILE):
            with open(SENT_DATA_FILE, 'r', encoding='utf-8') as f:
                return set(json.load(f))
        return set()
    except Exception as e:
        print(f"⚠️ 데이터 로드 중 오류: {str(e)}")
        return set()


def save_sent_data(sent_data):
    try:
        with open(SENT_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(list(sent_data), f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠️ 데이터 저장 중 오류: {str(e)}")


def is_operating_hours():
    current_hour = datetime.now().hour
    return not (2 <= current_hour < 9)


def process_youtube_data(youtube, telegram, sent_data):
    try:
        data = youtube.get_data()
        if not data:
            print("❌ YouTube 데이터 수집 실패")
            return sent_data

        print(f"✅ 수집된 YouTube 데이터: {len(data)}개")

        new_items = []
        for item in data:
            if not isinstance(item, dict):
                continue

            video_id = item.get('링크', '').split('=')[-1]
            if video_id and video_id not in sent_data and '급매' in item.get('제목', ''):
                new_items.append(item)
                sent_data.add(video_id)

        if new_items:
            print(f"\n🆕 새로운 YouTube 급매 발견: {len(new_items)}개")
            for item in new_items:
                try:
                    message = telegram.format_property_message(item)
                    response = telegram.send_message(message)

                    if response.get('ok'):
                        print(f"✅ YouTube 전송 성공: {item.get('제목')}")
                    else:
                        print(f"❌ YouTube 전송 실패: {response.get('description')}")

                    time.sleep(2)  # API 제한 방지
                except Exception as e:
                    print(f"⚠️ YouTube 메시지 전송 중 오류: {str(e)}")

            save_sent_data(sent_data)
        else:
            print("📭 새로운 YouTube 급매 매물 없음")

        return sent_data

    except Exception as e:
        print(f"\n⚠️ YouTube 처리 중 오류 발생: {str(e)}")
        return sent_data


# 메인 실행 부분
a = Auction()
o = OilJang()
k = Kyocharo()
youtube = Youtube()
sent_data = load_sent_data()

print(f"\n{'=' * 50}")
print(f"프로그램 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"{'=' * 50}\n")

while True:
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # 오일장, 교차로 데이터 처리
    o_data = o.get_data()
    k_data = k.get_data()
    data = k_data + o_data
    urgent_properties = filter_properties_by_keyword(data)
    send_urgent_properties_to_telegram(urgent_properties)
    print(f"급매 매물 수: {len(urgent_properties)}")
    if urgent_properties:
        print("\n급매 매물 목록:")
        for prop in urgent_properties:
            print(f"매물명: {prop['매물명']}")
            print('link:', prop['link'])
    else:
        print("\n급매 매물이 없습니다.")

    # YouTube 데이터 처리 (운영 시간에만)
    if is_operating_hours():
        print(f"\n📊 YouTube 데이터 수집 시작 ({current_time})")
        sent_data = process_youtube_data(youtube, TelegramSender(), sent_data)
    else:
        print(f"\n⏰ YouTube 운영 시간이 아님 ({current_time})")

    print(f"\n⏳ 다음 체크까지 대기 중... ({current_time})")
    time.sleep(60 * 3)  # 3분 대기
