import json
import re
import requests
import bs4

def get_data(self):
    a = clawer(self)


def clawer(self):
    cur_num = '4406936'
    res = requests.get(self.url + cur_num)
    res.encoding = 'utf-8'
    html = res.text
    bs = bs4.BeautifulSoup(html, 'html.parser')
    rows = bs.select("table.info_t tr")
    table_data = set_table_data(rows)

    # detail_data 처리: Tag 객체를 문자열로 변환
    detail_data = bs.select_one("div.detail_text_cont")
    if detail_data:
        table_data['상세정보'] = detail_data.decode_contents().strip()  # 문자열로 변환
    else:
        table_data['상세정보'] = None

    total_data = table_data
    json_data = json.dumps(total_data, ensure_ascii=False, indent=4)
    print(json_data)


def set_table_data(table_html_data):
    data = {}
    
    # 데이터 추출용 함수: <br>로 구분된 텍스트를 배열로 처리하고 불필요한 태그 및 공백 제거
    def get_text_with_br_as_list(td):
        if isinstance(td, str):  # 이미 문자열인 경우
            return td.strip()
        # <br> 태그를 기준으로 텍스트 분리 후 HTML 태그 및 공백 제거
        parts = re.split(r'<br\s*/?>', td.decode_contents())
        parts = [re.sub(r'</?br>', '', text).strip() for text in parts if text.strip()]  # 태그 제거
        if len(parts) > 1:
            return parts  # 배열로 반환
        return parts[0] if parts else ""  # 단일 값 반환
    
    # 텍스트 정리: \n, \t, 공백 제거 및 괄호 처리
    def clean_text(value):
        if not isinstance(value, str):  # 문자열이 아닐 경우 처리
            value = value.get_text(strip=True) if value else ""
        value = re.sub(r'[\n\t]+', '', value)  # \n, \t 제거
        value = re.sub(r'\s+', ' ', value)  # 중복 공백 제거
        return value.strip()
    
    # 괄호 속 데이터 분리 (특정 필드용)
    def split_parens(value):
        value = clean_text(value)  # 사전에 텍스트 정리
        match = re.match(r'(.+)\((.+)\)', value)
        if match:
            return match.group(1).strip(), match.group(2).strip()  # 괄호 밖과 안 데이터 분리
        return value, None  # 괄호가 없을 경우 그대로 반환

    for row in table_html_data:
        cols = row.find_all("td")
        
        if len(cols) == 2:  # 제목과 내용이 1:1 매핑된 경우
            key = clean_text(cols[0])
            value = get_text_with_br_as_list(cols[1])
            data[key] = value

        elif len(cols) == 4:  # 제목과 내용이 2개씩 있는 경우
            key1 = clean_text(cols[0])
            value1 = get_text_with_br_as_list(cols[1])
            key2 = clean_text(cols[2])
            value2 = get_text_with_br_as_list(cols[3])

            # "총주차대수"와 같은 경우 괄호 처리
            if key1 == "총주차대수":
                main_value, extra_value = split_parens(value1)
                data[key1] = {"주차대수": main_value, "비율": extra_value}
            else:
                data[key1] = value1

            if key2 == "총주차대수":
                main_value, extra_value = split_parens(value2)
                data[key2] = {"주차대수": main_value, "비율": extra_value}
            else:
                data[key2] = value2

    return data