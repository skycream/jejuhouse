import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, List
import time


def get_data(existing_data: List[Dict] = None) -> List[Dict]:
    """
    기존 데이터 리스트를 받아서 새로운 데이터를 추가하고 업데이트된 전체 리스트를 반환합니다.

    Args:
        existing_data: 기존 데이터 리스트. None인 경우 빈 리스트로 시작

    Returns:
        List[Dict]: 업데이트된 전체 데이터 리스트
    """
    print('제주도의 경매 데이터 조회를 시작합니다.')

    if existing_data is None:
        existing_data = []

    base_url = 'http://openapi.onbid.co.kr/openapi/services/KamcoPblsalThingInquireSvc/getKamcoPbctCltrList'
    service_key = 'qc3aOYZCyxYqx5N7K1ymM%2FQ40DOEBsK2%2FViC%2BKqrXG7UTDadEhH0MEHjuspVeOpq0ZEjOxczf5qaOIJ91%2F5wlQ%3D%3D'
    url = f'{base_url}?serviceKey={service_key}'

    # 기본 API 파라미터
    today = datetime.now()
    today_str = today.strftime('%Y%m%d')
    year_end = datetime(today.year, 12, 31).strftime('%Y%m%d')

    base_params = {
        'stdt': today_str,  # 오늘 날짜부터
        'eddt': year_end,  # 올해 말까지
        'AST_DVSN_CD': '0001',
        'numOfRows': 100
    }

    # 제주 데이터 조회
    jeju_params = base_params.copy()
    jeju_params['SIDO'] = '제주특별자치도'
    jeju_properties = get_region_data(url, jeju_params, '제주')

    # 새로운 데이터 병합
    new_properties = jeju_properties

    # 기존 데이터와 새로운 데이터 병합
    updated_data = update_property_data(existing_data, new_properties)

    # 결과 요약 출력
    jeju_items = [prop for prop in new_properties if '제주특별자치도' in prop['소재지']]

    print(f"\n새로 수집된 데이터:")
    print(f"제주 물건 수: {len(jeju_items)}개")
    print(f"전체 수집 물건 수: {len(new_properties)}개")
    print(f"최종 데이터 수: {len(updated_data)}개")

    return updated_data

def format_price(price: str) -> str:
    try:
        return format(int(price), ',') + '원'
    except ValueError:
        return price


def parse_property_data(xml_response: str) -> List[Dict]:
    root = ET.fromstring(xml_response)
    items = root.findall('.//item')
    properties = []

    for item in items:
        try:
            # 부동산만 필터링 (SCRN_GRP_CD가 0001인 경우)
            if item.find('SCRN_GRP_CD').text != '0001':
                continue

            # 상태 확인
            status = item.find('PBCT_CLTR_STAT_NM').text
            if not any(stat in status for stat in ['입찰진행중', '입찰예정', '입찰중', '입찰준비중']):
                continue

            # URL 생성에 필요한 파라미터 추출
            cltr_hstr_no = item.find('CLTR_HSTR_NO').text
            cltr_no = item.find('CLTR_NO').text
            plnm_no = item.find('PLNM_NO').text
            pbct_no = item.find('PBCT_NO').text
            pbct_cdtn_no = item.find('PBCT_CDTN_NO').text

            # 상세 페이지 URL 생성
            detail_url = (
                f"https://www.onbid.co.kr/op/cta/cltrdtl/collateralRealEstateDetail.do"
                f"?cltrHstrNo={cltr_hstr_no}"
                f"&cltrNo={cltr_no}"
                f"&plnmNo={plnm_no}"
                f"&pbctNo={pbct_no}"
                f"&scrnGrpCd=0001"
                f"&pbctCdtnNo={pbct_cdtn_no}"
            )

            property_info = {
                '물건번호': item.find('CLTR_MNMT_NO').text,
                '물건종류': item.find('CTGR_FULL_NM').text,
                '소재지': item.find('LDNM_ADRS').text,
                '최저입찰가': format_price(item.find('MIN_BID_PRC').text),
                '감정가': format_price(item.find('APSL_ASES_AVG_AMT').text),
                '입찰시작': datetime.strptime(item.find('PBCT_BEGN_DTM').text, '%Y%m%d%H%M%S').strftime('%Y-%m-%d %H:%M'),
                '입찰마감': datetime.strptime(item.find('PBCT_CLS_DTM').text, '%Y%m%d%H%M%S').strftime('%Y-%m-%d %H:%M'),
                '상태': status,
                '비율': item.find('FEE_RATE').text,
                '상세내용': item.find('GOODS_NM').text,
                'link': detail_url
            }
            properties.append(property_info)

        except Exception as e:
            prop_no = item.find('CLTR_MNMT_NO').text if item.find('CLTR_MNMT_NO') is not None else 'Unknown'
            print(f"물건번호 {prop_no} 파싱 중 오류 발생: {str(e)}")
            continue

    # 입찰시작시간 순으로 정렬
    return sorted(properties, key=lambda x: x['입찰시작'])


def get_total_count(xml_response: str) -> int:
    root = ET.fromstring(xml_response)
    total_count = root.find('.//totalCount')
    return int(total_count.text) if total_count is not None else 0


def update_property_data(existing_data, new_data):
    """기존 데이터와 새로운 데이터를 병합하여 반환합니다."""
    # 데이터가 반복 가능한 리스트인지 확인
    if not isinstance(existing_data, list):
        print("⚠️ existing_data가 리스트가 아닙니다. 빈 리스트로 초기화합니다.")
        existing_data = []
    if not isinstance(new_data, list):
        print("⚠️ new_data가 리스트가 아닙니다. 빈 리스트로 초기화합니다.")
        new_data = []

    # 기존 데이터와 새로운 데이터 병합
    data_dict = {item['물건번호']: {
        'data': item,
        'timestamp': datetime.strptime(item['입찰마감'], '%Y-%m-%d %H:%M')
    } for item in existing_data}

    update_count = 0
    add_count = 0

    for item in new_data:
        물건번호 = item['물건번호']
        new_timestamp = datetime.strptime(item['입찰마감'], '%Y-%m-%d %H:%M')

        if 물건번호 in data_dict:
            if new_timestamp >= data_dict[물건번호]['timestamp']:
                data_dict[물건번호] = {
                    'data': item,
                    'timestamp': new_timestamp
                }
                update_count += 1
        else:
            data_dict[물건번호] = {
                'data': item,
                'timestamp': new_timestamp
            }
            add_count += 1

    print(f"\n데이터 업데이트 현황:")
    print(f"- 새로 추가된 데이터: {add_count}개")
    print(f"- 업데이트된 데이터: {update_count}개")

    return [item['data'] for item in data_dict.values()]



def get_region_data(url: str, params: dict, region_name: str) -> List[Dict]:
    """특정 지역의 경매 데이터를 수집하는 함수"""
    properties = []
    total_count = 0

    # 첫 페이지 조회로 전체 데이터 수 확인
    response = requests.get(url, params=params)
    if response.status_code == 200:
        total_count = get_total_count(response.text)
        total_pages = (total_count + params['numOfRows'] - 1) // params['numOfRows']
        print(f"\n{region_name} 데이터 수: {total_count}개 (총 {total_pages}페이지)")

        # 모든 페이지 순차적으로 조회
        for page in range(1, total_pages + 1):
            params['pageNo'] = page
            print(
                f'{region_name} 페이지 {page}/{total_pages} 조회 중... (데이터 범위: {(page - 1) * 100 + 1}~{min(page * 100, total_count)})')

            response = requests.get(url, params=params)
            if response.status_code == 200:
                page_properties = parse_property_data(response.text)
                if page_properties:
                    properties.extend(page_properties)
                    print(f"- 현재까지 수집된 {region_name} 데이터: {len(properties)}개")
            else:
                print(f"데이터 조회 실패: {response.status_code}")
                continue

            time.sleep(0.5)

    return properties