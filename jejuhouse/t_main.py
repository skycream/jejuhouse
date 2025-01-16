from classes.auction import Auction
from classes.blog import NaverBlog
from classes.oiljang import OilJang
from classes.kyocharo import Kyocharo
from classes.youtube import Youtube
from classes.auction.get import update_property_data
from lib.t_telegram import TelegramSender
import json
import time
import os
from datetime import datetime, timedelta

# 설정
SENT_DATA_FILE = "sent_data.json"
LAST_AUCTION_CHECK_FILE = "last_auction_check.json"
LAST_YOUTUBE_CHECK_FILE = "last_youtube_check.json"


def get_last_check_time():
    """마지막 온비드 체크 시간을 가져오는 함수"""
    try:
        if os.path.exists(LAST_AUCTION_CHECK_FILE):
            with open(LAST_AUCTION_CHECK_FILE, 'r') as f:
                data = json.load(f)
                return datetime.strptime(data['last_check'], '%Y-%m-%d %H:%M:%S')
    except Exception as e:
        print(f"⚠️ 마지막 체크 시간 로드 중 오류: {str(e)}")
    return None


def save_last_check_time():
    """현재 시간을 마지막 체크 시간으로 저장"""
    try:
        with open(LAST_AUCTION_CHECK_FILE, 'w') as f:
            json.dump({'last_check': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}, f)
    except Exception as e:
        print(f"⚠️ 마지막 체크 시간 저장 중 오류: {str(e)}")


def should_check_auction():
    """온비드 데이터를 체크해야 하는지 확인하는 함수"""
    last_check = get_last_check_time()
    if last_check is None:
        return True

    time_diff = datetime.now() - last_check
    return time_diff >= timedelta(minutes=30)


def get_last_youtube_check_time():
    """마지막 유튜브 체크 시간을 가져오는 함수"""
    try:
        if os.path.exists(LAST_YOUTUBE_CHECK_FILE):
            with open(LAST_YOUTUBE_CHECK_FILE, 'r') as f:
                data = json.load(f)
                return datetime.strptime(data['last_check'], '%Y-%m-%d %H:%M:%S')
    except Exception as e:
        print(f"⚠️ 유튜브 마지막 체크 시간 로드 중 오류: {str(e)}")
    return None


def save_last_youtube_check_time():
    """현재 시간을 마지막 유튜브 체크 시간으로 저장"""
    try:
        with open(LAST_YOUTUBE_CHECK_FILE, 'w') as f:
            json.dump({'last_check': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}, f)
    except Exception as e:
        print(f"⚠️ 유튜브 마지막 체크 시간 저장 중 오류: {str(e)}")


def should_check_youtube():
    """유튜브 데이터를 체크해야 하는지 확인하는 함수"""
    if not is_operating_hours():
        return False

    last_check = get_last_youtube_check_time()
    if last_check is None:
        return True

    time_diff = datetime.now() - last_check
    return time_diff >= timedelta(hours=1)


def load_sent_data():
    """전송된 데이터 로드"""
    try:
        if os.path.exists(SENT_DATA_FILE):
            with open(SENT_DATA_FILE, 'r', encoding='utf-8') as f:
                return set(json.load(f))
        return set()
    except Exception as e:
        print(f"⚠️ 데이터 로드 중 오류: {str(e)}")
        return set()


def save_sent_data(sent_data):
    """전송된 데이터 저장"""
    try:
        with open(SENT_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(list(sent_data), f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠️ 데이터 저장 중 오류: {str(e)}")


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
            # process_auction_data에서 전송 요청 간 간격 조정
            for item in new_items:
                try:
                    message = telegram.format_auction_message(item)
                    response = telegram.send_message(message)

                    if response.get('ok'):
                        print(f"✅ 전송 성공: {item['물건번호']}")
                    else:
                        print(f"❌ 전송 실패: {response.get('description')}")

                    time.sleep(2)  # 기본 대기 시간 (2초)

                except Exception as e:
                    print(f"⚠️ 메시지 전송 중 오류: {str(e)}")

            save_sent_data(sent_data)
        else:
            print("📭 새로운 YouTube 급매 매물 없음")

        return sent_data

    except Exception as e:
        print(f"\n⚠️ YouTube 처리 중 오류 발생: {str(e)}")
        return sent_data


def is_operating_hours():
    current_hour = datetime.now().hour
    return not (2 <= current_hour < 9)


def process_auction_data(auction_data, telegram):
    """새로운 경매 데이터를 처리하고 텔레그램으로 전송하는 함수"""
    if not isinstance(auction_data, list):
        print("❌ 처리할 경매 데이터가 리스트 형식이 아닙니다.")
        return

    sent_items = set()  # 이미 전송된 물건번호 저장

    try:
        if os.path.exists("sent_auction_items.json"):
            with open("sent_auction_items.json", 'r', encoding='utf-8') as f:
                sent_items = set(json.load(f))
    except Exception as e:
        print(f"⚠️ 전송 기록 로드 중 오류: {str(e)}")

    new_items = [item for item in auction_data if item.get('물건번호') not in sent_items]

    if new_items:
        print(f"\n🆕 새로운 경매 물건 발견: {len(new_items)}개")
        for item in new_items:
            try:
                message = telegram.format_auction_message(item)
                response = telegram.send_message(message)

                if response.get('ok'):
                    print(f"✅ 전송 성공: {item['물건번호']}")
                else:
                    print(f"❌ 전송 실패: {item['물건번호']}")

                time.sleep(1)  # API 제한 방지
            except Exception as e:
                print(f"⚠️ 메시지 전송 중 오류: {str(e)}")

        # 전송된 물건번호 저장
        try:
            with open("sent_auction_items.json", 'w', encoding='utf-8') as f:
                json.dump(list(sent_items), f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ 전송 기록 저장 중 오류: {str(e)}")
    else:
        print("📭 새로운 경매 물건 없음")



# 메인 실행 부분
a = Auction()
o = OilJang()
k = Kyocharo()
youtube = Youtube()
telegram = TelegramSender()
sent_data = load_sent_data()

print(f"\n{'=' * 50}")
print(f"프로그램 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"{'=' * 50}\n")

while True:
    try:
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 오일장, 교차로 처리
        print("\n📊 오일장/교차로 데이터 수집 시작")
        o_data = o.get_data()
        k_data = k.get_data()
        if o_data or k_data:
            print(f"수집된 데이터: 오일장 {len(o_data)}개, 교차로 {len(k_data)}개")

        # YouTube 데이터 처리 (운영 시간에만, 1시간 간격)
        if should_check_youtube():
            print(f"\n📊 YouTube 데이터 수집 시작 ({current_time})")
            sent_data = process_youtube_data(Youtube, telegram, sent_data)
            save_last_youtube_check_time()
        else:
            if not is_operating_hours():
                print(f"\n⏰ YouTube 운영 시간이 아님 ({current_time})")
            else:
                print(f"\n⏰ YouTube 다음 체크 대기 중 ({current_time})")


        try:
            print(f"\n📊 온비드 데이터 수집 시작 ({current_time})")
            # 1. get_data 호출 및 반환값 확인
            result = a.get_data()

            # 2. 반환값이 리스트인지 검증 및 기본값 처리
            if not isinstance(result, list):
                print(f"⚠️ get_data() 반환값이 리스트가 아닙니다: {type(result)}. 빈 리스트로 초기화합니다.")
                result = []

            # 3. 기존 데이터 로드
            existing_data = []  # 기존 데이터 로드 로직 추가 필요

            # 4. 기존 데이터와 새로운 데이터 병합
            updated_data = update_property_data(existing_data, result)

            # 5. 병합 결과 처리
            if updated_data:
                process_auction_data(updated_data, telegram)  # 처리 함수 호출
                save_last_check_time()  # 체크 시간 저장
                print(f"✅ 온비드 데이터 처리 완료: 총 {len(updated_data)}개 항목")
            else:
                print("📭 유효한 경매 데이터가 없습니다")

        except Exception as e:
            print(f"⚠️ 메인 루프 실행 중 오류 발생: {str(e)}")
            import traceback

            print(traceback.format_exc())

        print(f"\n⏳ 다음 체크까지 대기 중... ({current_time})")
        time.sleep(60 * 3)  # 3분 대기

    except Exception as e:
        print(f"\n⚠️ 메인 루프 실행 중 오류 발생: {str(e)}")
        time.sleep(60)  # 오류 발생시 1분 대기 후 재시도
        continue