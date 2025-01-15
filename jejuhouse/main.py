from classes.auction import Auction
from classes.blog import NaverBlog
from classes.oiljang import OilJang
from classes.kyocharo import Kyocharo
from lib.telegram import TelegramSender

import json
import time

def format_data(o_data, k_data):
    # 각각 첫 번째 매물만 선택
    sample_data = {
        '오일장': o_data[:1] if o_data else [],
        '교차로': k_data[:1] if k_data else []
    }
    formatted_json = json.dumps(sample_data, ensure_ascii=False, indent=2)
    print(formatted_json)

def filter_properties_by_keyword(data):
   urgent_sales = []
   excluded_types = ['아파트', '토지', '임야', '원룸', '투룸', '쓰리룸', '오피스텔','빌라','연립','다세대']
   bypass_keywords = ['통매매']  # 프리패스 키워드 목록
   
   for property in data:
       if '매물명' in property:
           # 프리패스 키워드가 있는지 먼저 확인
           has_bypass = any(keyword in property['매물명'] for keyword in bypass_keywords)
           
           if has_bypass:
               # 프리패스 키워드가 있으면 바로 추가
               urgent_sales.append(property)
           elif '급매' in property['매물명']:
               # 프리패스가 아닌 경우 기존 로직 실행
               is_excluded = any(excluded in property['매물종류'] for excluded in excluded_types)
               if not is_excluded:
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
# a = Auction()
# a_data = a.get_data()

# b = NaverBlog()
# b_data = b.get_data()
o = OilJang()
k = Kyocharo()

while True:
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
    time.sleep(60*3)
