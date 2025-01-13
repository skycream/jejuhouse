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
        highest_num = latest_num
        
        for listing in listings:
            current_num = int(listing.get('offer_idx', '0'))
            
            if current_num > latest_num:
                # 오일장 형식과 동일하게 구조화하되 모든 데이터 보존
                converted_info = {
                    '플랫폼': '교차로',
                    'link': 'https://land.jejukcr.com/offer/'+str(listing.get('offer_idx', '')),
                    '매물정보': {
                        '매물번호': listing.get('offer_idx', ''),
                        '종류': listing.get('cateid_str', ''),
                        '거래유형': listing.get('trade_str', ''),
                        '상태': listing.get('state_STR', ''),
                        '광고종료일': listing.get('end_date', ''),
                        '건물종류': listing.get('kind_STR', ''),
                        '신규매물여부': listing.get('new_BOOL', '')
                    },
                    '매물명': listing.get('summary', ''),
                    '매물종류': listing.get('cateid_str', ''),
                    '소재지': listing.get('addr_full', ''),
                    '도로명주소': listing.get('road_addr', ''),
                    '매매가격': f"{listing.get('sale_price', '')}만원" if listing.get('trade_str') == '매매' else '',
                    '융자금': '',  # 교차로 데이터에 없는 필드이지만 형식 통일을 위해 추가
                    '면적단가': listing.get('unit_price_STR', ''),
                    '토지면적': listing.get('land_area', ''),
                    '보증금': f"{listing.get('deposit', '')}만원" if listing.get('deposit') else '',
                    '월세': f"{listing.get('monthly_rent', '')}만원" if listing.get('monthly_rent') and listing.get('trade_str') == '월세' else '',
                    '년세': f"{listing.get('monthly_rent', '')}만원" if listing.get('monthly_rent') and listing.get('trade_str') == '년세' else '',
                    # '권리금': '0원',
                    '공급면적': f"{listing.get('area1', '')} ㎡" if listing.get('area1') else '0 ㎡',
                    '전용면적': f"{listing.get('area2', '')}㎡" if listing.get('area2') else '0㎡',
                    '대지면적': f"{listing.get('land_area', '')} ㎡" if listing.get('land_area') else '',
                    '연면적': f"{listing.get('total_area', '')} ㎡" if listing.get('total_area') else '',
                    '월관리비': listing.get('maintenance_cost', ''),
                    '방향': listing.get('direction_STR', ''),
                    '방수 / 욕실수': listing.get('rooms_bathrooms', ''),
                    '입주가능일': listing.get('live_in_state_STR', ''),
                    '사용승인일': listing.get('completion_date', ''),
                    '해당동': listing.get('dong_number', ''),
                    '해당층총 층수': f"{listing.get('current_floor', '')}/{listing.get('total_floor', '')}",
                    # '총세대수': listing.get('households_LABEL', ''),
                    '총주차대수': {
                        '주차대수': listing.get('parking_count', ''),
                        '비율': None
                    },
                    '건물종류': listing.get('kind_STR', ''),
                    '건물형태': listing.get('building_type_STR', ''),
                    '건축물용도': listing.get('building_use_STR', ''),
                    '연락처': [
                        listing.get('phone1', ''),
                        listing.get('phone2', '')
                    ],
                    '매물번호': listing.get('offer_idx', ''),
                    '위치정보': {
                        '주소': listing.get('addr', ''),
                        '도로명주소': listing.get('road_addr', ''),
                        '지역명': listing.get('dong_STR', ''),
                        '건물명': listing.get('title_STR', ''),
                        '위도': listing.get('lat', ''),
                        '경도': listing.get('lng', ''),
                        '상세주소': listing.get('addr_full', '')
                    },
                    '부가정보': {
                        '특징': listing.get('feature', ''),
                        '요약정보': listing.get('summary', ''),
                        '관리비여부': listing.get('maintenance_cost_yn', ''),
                        '엘리베이터': listing.get('entrance_structure_STR', ''),
                        '입주가능일': listing.get('live_in_state_STR', ''),
                        '방구조': listing.get('rooms_bathrooms', ''),
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
                    },
                    '상세정보': listing.get('feature', '')
                }

                # 빈 값 제거
                def clean_dict(d):
                    if isinstance(d, dict):
                        return {k: clean_dict(v) for k, v in d.items() 
                               if v is not None and v != '' and v != '-' and v != 'n' and clean_dict(v) != {}}
                    elif isinstance(d, list):
                        return [clean_dict(x) for x in d if x is not None and x != '']
                    return d

                cleaned_info = clean_dict(converted_info)
                processed_listings.append(cleaned_info)
                
                if current_num > highest_num:
                    highest_num = current_num
                
                print(f"새로운 매물 발견: {current_num}")
                print("-" * 50)
        
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