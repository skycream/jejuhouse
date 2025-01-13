import requests
import xml.etree.ElementTree as ET
from datetime import datetime, date
from typing import Dict, List
import pickle
import os
import time


def get_data():
    print('서울 및 제주도의 경매 데이터 조회를 시작합니다.')

    try:
        # 현재 파일의 절대 경로 (classes/auction/get.py)
        current_file = os.path.abspath(__file__)

        # 최상위 jejuhouse 디렉토리 찾기
        # classes -> auction -> jejuhouse(내부) -> jejuhouse(외부) -> jejuhouse(최상위)
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_file)))))

        # PKL 파일 경로 설정
        pkl_filename = os.path.join(project_root, 'lastest_auction_bid.pkl')
        print(f"데이터 저장 경로: {pkl_filename}")
    except Exception as e:
        print(f"경로 설정 중 오류 발생: {str(e)}")
        raise

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

    # 서울 데이터 조회
    seoul_params = base_params.copy()
    seoul_params['SIDO'] = '서울특별시'
    seoul_properties = get_region_data(url, seoul_params, '서울')

    # 제주 데이터 조회
    jeju_params = base_params.copy()
    jeju_params['SIDO'] = '제주특별자치도'
    jeju_properties = get_region_data(url, jeju_params, '제주')

    # 전체 데이터 병합
    all_properties = seoul_properties + jeju_properties
    all_properties.sort(key=lambda x: x['입찰시작'])  # 입찰시작 시간순 정렬

    # 기존 데이터 로드 및 업데이트
    pkl_filename = 'onbid_properties.pkl'
    existing_data = load_existing_data(pkl_filename)
    updated_data = update_property_data(existing_data, all_properties)
    save_data(updated_data, pkl_filename)

    print("\n=== 서울/제주 진행 중인 경매 물건 목록 ===\n")

    # 서울 물건 출력
    print("\n--- 서울특별시 물건 ---")
    seoul_items = [prop for prop in all_properties if '서울특별시' in prop['소재지']]
    for prop in seoul_items:
        print(f"▶ 물건번호: {prop['물건번호']}")
        print(f"▶ 물건종류: {prop['물건종류']}")
        print(f"▶ 소재지: {prop['소재지']}")
        print(f"▶ 최저입찰가: {prop['최저입찰가']} ({prop['비율']})")
        print(f"▶ 감정가: {prop['감정가']}")
        print(f"▶ 입찰기간: {prop['입찰시작']} ~ {prop['입찰마감']}")
        print(f"▶ 현재상태: {prop['상태']}")
        print(f"▶ 상세내용: {prop['상세내용']}")
        print(f"▶ 상세페이지: {prop['상세페이지']}\n")
        print("-" * 80 + "\n")

    # 제주 물건 출력
    print("\n--- 제주특별자치도 물건 ---")
    jeju_items = [prop for prop in all_properties if '제주특별자치도' in prop['소재지']]
    for prop in jeju_items:
        print(f"▶ 물건번호: {prop['물건번호']}")
        print(f"▶ 물건종류: {prop['물건종류']}")
        print(f"▶ 소재지: {prop['소재지']}")
        print(f"▶ 최저입찰가: {prop['최저입찰가']} ({prop['비율']})")
        print(f"▶ 감정가: {prop['감정가']}")
        print(f"▶ 입찰기간: {prop['입찰시작']} ~ {prop['입찰마감']}")
        print(f"▶ 현재상태: {prop['상태']}")
        print(f"▶ 상세내용: {prop['상세내용']}")
        print(f"▶ 상세페이지: {prop['상세페이지']}\n")
        print("-" * 80 + "\n")

    print(f"서울 물건 수: {len(seoul_items)}개")
    print(f"제주 물건 수: {len(jeju_items)}개")
    print(f"전체 물건 수: {len(all_properties)}개")
    print(f"누적된 전체 데이터 수: {len(updated_data)}개")
    print(f"데이터가 {pkl_filename} 파일에 저장되었습니다.")

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
                '상세페이지': detail_url
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


def load_existing_data(filename: str) -> List[Dict]:
    if os.path.exists(filename):
        with open(filename, 'rb') as f:
            return pickle.load(f)
    return []


def update_property_data(existing_data: List[Dict], new_data: List[Dict]) -> List[Dict]:
    """
    기존 데이터와 새로운 데이터를 병합합니다.
    동일한 물건번호가 있는 경우 최신 데이터로 업데이트합니다.

    Args:
        existing_data (List[Dict]): 기존 pkl 파일의 데이터
        new_data (List[Dict]): 새로 수집한 데이터

    Returns:
        List[Dict]: 업데이트된 데이터 목록
    """
    # 물건번호를 키로 하는 딕셔너리 생성
    data_dict = {item['물건번호']: {
        'data': item,
        'timestamp': datetime.strptime(item['입찰마감'], '%Y-%m-%d %H:%M')
    } for item in existing_data}

    # 새로운 데이터 처리
    update_count = 0
    add_count = 0

    for item in new_data:
        물건번호 = item['물건번호']
        new_timestamp = datetime.strptime(item['입찰마감'], '%Y-%m-%d %H:%M')

        if 물건번호 in data_dict:
            # 기존 데이터가 있는 경우, 타임스탬프 비교
            if new_timestamp >= data_dict[물건번호]['timestamp']:
                data_dict[물건번호] = {
                    'data': item,
                    'timestamp': new_timestamp
                }
                update_count += 1
        else:
            # 새로운 데이터 추가
            data_dict[물건번호] = {
                'data': item,
                'timestamp': new_timestamp
            }
            add_count += 1

    print(f"\n데이터 업데이트 현황:")
    print(f"- 기존 데이터 수: {len(existing_data)}개")
    print(f"- 새로 추가된 데이터: {add_count}개")
    print(f"- 업데이트된 데이터: {update_count}개")
    print(f"- 최종 데이터 수: {len(data_dict)}개")

    # 딕셔너리를 리스트로 변환하여 반환
    return [item['data'] for item in data_dict.values()]


def save_data(data: List[Dict], filename: str):
    """
    데이터를 pkl 파일로 저장합니다.
    파일이 위치할 디렉토리가 없는 경우 생성합니다.

    Args:
        data (List[Dict]): 저장할 데이터
        filename (str): 저장할 파일 경로
    """
    try:
        # 디렉토리 확인 및 생성
        directory = os.path.dirname(filename)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
            print(f"디렉토리 생성: {directory}")

        # 데이터 저장
        with open(filename, 'wb') as f:
            pickle.dump(data, f)

        print(f"데이터가 {filename} 파일에 저장되었습니다.")
    except Exception as e:
        print(f"데이터 저장 중 오류 발생: {str(e)}")
        raise


def get_region_data(url: str, params: dict, region_name: str) -> List[Dict]:
    """특정 지역의 경매 데이터를 수집하는 함수"""
    properties = []
    total_count = 0
    page = 1

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

            # 과도한 API 호출 방지를 위한 잠시 대기
            time.sleep(0.5)

    return properties