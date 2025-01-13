import requests
import json
import pickle
import os

def get_data(self):
    # 마지막 교차로 매물 번호를 저장한 파일을 로드
    if os.path.exists('latest_kyocharo_property_num.pkl'):
        with open('latest_kyocharo_property_num.pkl', 'rb') as f:
            latest_num = pickle.load(f)
    else:
        latest_num = 0
    total_data = get_api_data(self.url, latest_num)
    # print(total_data)
    return total_data

def get_api_data(url, latest_num):
    try:
        res = requests.get(url)
        res.encoding = 'utf-8'
        data_dict = json.loads(res.text)
        
        listings = data_dict['result']['rows']
        processed_listings = []
        highest_num = latest_num  # 가장 높은 매물번호 추적
        
        for listing in listings:
            current_num = int(listing.get('offer_idx', '0'))
            
            # latest_num보다 큰 매물만 처리
            if current_num > latest_num:
                detailed_info = {
                    '매물정보': {
                        '매물번호': listing.get('offer_idx', ''),
                        '종류': listing.get('cateid_str', ''),
                        '거래유형': listing.get('trade_str', ''),
                        '상태': listing.get('state_STR', ''),
                        '광고종료일': listing.get('end_date', ''),
                        '건물종류': listing.get('kind_STR', ''),
                        '신규매물여부': listing.get('new_BOOL', '')
                    },
                    '위치정보': {
                        '주소': listing.get('addr', ''),
                        '도로명주소': listing.get('road_addr', ''),
                        '지역명': listing.get('dong_STR', ''),
                        '건물명': listing.get('title_STR', ''),
                        '위도': listing.get('lat', ''),
                        '경도': listing.get('lng', ''),
                        '상세주소': listing.get('addr_full', '')
                    },
                    '가격정보': {
                        '매매가': listing.get('sale_price', ''),
                        '보증금': listing.get('deposit', ''),
                        '월세': listing.get('monthly_rent', ''),
                        '년세': listing.get('monthly_rent', '') if listing.get('trade_str') == '년세' else '',
                        '표시가격': listing.get('price_STR', ''),
                        '한글가격': listing.get('price_HANGUL', '').replace('<span>', '').replace('</span>', ''),
                        '단가': listing.get('unit_price_STR', '')
                    },
                    '면적정보': {
                        '공급면적': {
                            '면적': listing.get('area1', ''),
                            '평형': listing.get('area1_PYEONG', ''),
                            '단위': '㎡'
                        },
                        '전용면적': {
                            '면적': listing.get('area2', ''),
                            '평형': listing.get('area2_PYEONG', ''),
                            '단위': '㎡'
                        }
                    },
                    '건물정보': {
                        '현재층': listing.get('current_floor', ''),
                        '전체층': listing.get('total_floor', ''),
                        '층타입': listing.get('floor_type_STR', ''),
                        '주차여부': listing.get('parking_yn_STR', ''),
                        '총세대수': listing.get('households_LABEL', ''),
                        '방향': listing.get('direction_STR', ''),
                        '난방': listing.get('heating_STR', '')
                    },
                    '중개사정보': {
                        '업체명': listing.get('user_name', ''),
                        '대표번호': listing.get('phone1', ''),
                        '휴대폰': listing.get('phone2', ''),
                        '등록자ID': listing.get('user_id', ''),
                        '중개사등록여부': listing.get('biz_yn', '')
                    },
                    '부가정보': {
                        '특징': listing.get('feature', ''),
                        '요약정보': listing.get('summary', ''),
                        '관리비여부': listing.get('maintenance_cost_yn', ''),
                        '엘리베이터': listing.get('entrance_structure_STR', ''),
                        '입주가능일': listing.get('live_in_state_STR', ''),
                        '방구조': f"{listing.get('rooms_bathrooms', '')}",
                        '옵션정보': {
                            '냉방시설': listing.get('cooler_options_STR', ''),
                            '가구': listing.get('furniture_options_STR', ''),
                            '주방시설': listing.get('kitchen_options_STR', ''),
                            '보안시설': listing.get('security_options_STR', '')
                        }
                    },
                    '시간정보': {
                        '등록일': listing.get('c_datetime', ''),
                        '수정일': listing.get('m_datetime', ''),
                        '갱신일': listing.get('renewed_datetime', '')
                    }
                }
                
                # 빈 값 제거
                def clean_dict(d):
                    if isinstance(d, dict):
                        return {k: clean_dict(v) for k, v in d.items() 
                               if v and v != '' and v != '-' and v != 'n' and clean_dict(v) != {}}
                    return d
                
                cleaned_info = clean_dict(detailed_info)
                processed_listings.append(cleaned_info)
                
                # 현재 매물번호가 더 크다면 highest_num 업데이트
                if current_num > highest_num:
                    highest_num = current_num
                
                print(f"새로운 매물 발견: {current_num}")
                print("-" * 50)
        
        # 가장 높은 매물번호 저장
        if highest_num > latest_num:
            with open('latest_kyocharo_property_num.pkl', 'wb') as f:
                pickle.dump(highest_num, f)
            print(f"최신 매물번호 업데이트: {latest_num} -> {highest_num}")
        
        return processed_listings
        
    except requests.exceptions.RequestException as e:
        print(f"요청 중 오류 발생: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"JSON 파싱 중 오류 발생: {e}")
        return None
    except Exception as e:
        print(f"예상치 못한 오류 발생: {e}")
        return None