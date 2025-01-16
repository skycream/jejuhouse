import requests
import json
from datetime import datetime
import time


class TelegramSender:
    def __init__(self):
        self.bot_token = "7811421741:AAHFTL6Vj6U1WhuzsJ7P2VWvN67IGAkDH9s"
        self.chat_id = "-1002346439576"
        self.max_retries = 3
        self.retry_delay = 5

    def send_message(self, text):
        for attempt in range(self.max_retries):
            try:
                url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
                payload = {
                    "chat_id": self.chat_id,
                    "text": text,
                    "parse_mode": "HTML"
                }
                response = requests.post(url, json=payload, timeout=30)

                print(f"전송 시도 {attempt + 1}/{self.max_retries}")
                print(f"응답 코드: {response.status_code}")
                print(f"응답 내용: {response.text}")

                response_data = response.json()

                if response.status_code == 200 and response_data.get('ok'):
                    print("✅ 메시지 전송 성공")
                    return response_data

                print(f"⚠️ 전송 실패 (시도 {attempt + 1}/{self.max_retries})")
                print(f"에러 메시지: {response_data.get('description', '알 수 없는 에러')}")

                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)

            except requests.exceptions.RequestException as e:
                print(f"네트워크 에러 발생: {str(e)}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                continue

            except Exception as e:
                print(f"예상치 못한 에러 발생: {str(e)}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                continue

        return {"ok": False, "description": "최대 재시도 횟수 초과"}

    def format_property_message(self, property):
        try:
            # YouTube 데이터 형식 처리
            if '제목' in property:
                message = (
                    f"📺 <b>{property['제목']}</b>\n\n"
                    f"📅 등록일: {property.get('등록일', '정보 없음')}\n"
                    f"👤 채널: {property.get('채널명', '정보 없음')}\n\n"
                )

                if '설명' in property:
                    description = property['설명'][:500]
                    message += f"📝 설명:\n{description}\n\n"

                if 'link' in property:
                    message += f"🔗 링크:\n{property['link']}\n"
                elif '링크' in property:
                    message += f"🔗 링크:\n{property['링크']}\n"

                message += "--------------------------------------\n"
                return message

            # 부동산 매물 데이터 형식 처리
            else:
                message = f"🏠 <b>{property['매물명']}</b>\n"

                if '매매가격' in property:
                    message += f"💰 매매가: {property['매매가격']}\n"
                if '전세금' in property:
                    message += f"💰 전세금: {property['전세금']}\n"
                if '보증금' in property and '월세' in property:
                    message += f"💰 보증금/월세: {property['보증금']}/{property['월세']}\n"

                if '전용면적' in property:
                    message += f"📏 전용면적: {property['전용면적']}\n"
                if '소재지' in property:
                    message += f"📍 위치: {property['소재지']}\n"
                if 'link' in property:
                    message += f"🔗 Link: {property['link']}\n"

                message += "--------------------------------------\n"
                return message

        except Exception as e:
            print(f"메시지 포맷팅 중 오류 발생: {str(e)}")
            return f"⚠️ 메시지 포맷팅 오류: {str(e)}"

    def format_auction_message(self, item):
        """온비드 경매 물건 메시지 포맷팅"""
        try:
            message = (
                f"🏠 <b>새로운 경매 물건</b>\n\n"
                f"📑 물건번호: {item['물건번호']}\n"
                f"🏢 종류: {item['물건종류']}\n"
                f"📍 소재지: {item['소재지']}\n"
                f"💰 감정가: {item['감정가']}\n" 
                f"💰 최저입찰가: {item['최저입찰가']}\n"
                f"⏰ 입찰시작: {item['입찰시작']}\n"
                f"⏰ 입찰마감: {item['입찰마감']}\n\n"
                f"🔗 상세링크:\n{item['link']}\n"
                "--------------------------------------\n"
            )
            return message
        except Exception as e:
            print(f"메시지 포맷팅 중 오류 발생: {str(e)}")
            return f"⚠️ 메시지 포맷팅 오류: {str(e)}"