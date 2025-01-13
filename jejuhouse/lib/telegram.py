import requests
import json
from datetime import datetime

class TelegramSender:
    def __init__(self):
        self.bot_token = "5523500847:AAEJ46kC3hyKH3p3pnfC-7KoUfz0Ul-Sv3k"  # 여기에 봇 토큰을 입력하세요
        self.chat_id = "-4247377251"   

    def send_message(self, text):
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        response = requests.post(url, json=payload)
        return response.json()

    def format_property_message(self, property):
        # 기본 정보 포맷팅
        message = f"--------------------------------\n"
        message += f"🏠 <b>{property['매물명']}</b>\n"
        
        # 가격 정보 추가
        if '매매가격' in property:
            message += f" 매매가: {property['매매가격']}\n"
        if '전세금' in property:
            message += f" 전세금: {property['전세금']}\n"
        if '보증금' in property and '월세' in property:
            message += f" 보증금/월세: {property['보증금']}/{property['월세']}\n"
        
        # 면적 정보
        if '전용면적' in property:
            message += f" 전용면적: {property['전용면적']}\n"
        # 위치 정보
        if '소재지' in property:
            message += f" {property['소재지']}\n"
        if 'link' in property:
            message += f"🔗 Link: {property['link']}\n"

        return message
