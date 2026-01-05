import pandas as pd
import json
import re

def process_financial_excel(file_path, category):
    """
    엑셀 파일을 읽어 products와 options 리스트로 변환합니다.
    금융감독원 엑셀 전문 양식을 기반으로 유연하게 컬럼을 매핑합니다.
    """
    try:
        df = pd.read_excel(file_path)
    except Exception as e:
        return None, None, f"파일 읽기 실패: {str(e)}"

    # 컬럼 매핑 사전 (한글 헤더 -> DB 필드)
    col_map = {
        '금융회사명': 'kor_co_nm',
        '금융상품명': 'fin_prdt_nm',
        '가입방법': 'join_way',
        '만기 후 이자율': 'mtrt_int',
        '우대조건': 'etc_note',
        '저축 금리': 'intr_rate',
        '최고 우대금리': 'intr_rate2',
        '저축 기간': 'save_trm'
    }

    # 대출용 매핑 추가
    if category in ['credit']:
        col_map.update({
            '평균 금리': 'intr_rate',
            '최저 금리': 'intr_rate',
            '최고 금리': 'intr_rate2'
        })

    # 실제 엑셀 컬럼에서 가장 유사한 것 찾기
    found_cols = {}
    for kor, eng in col_map.items():
        for col in df.columns:
            if kor in str(col):
                found_cols[eng] = col
                break

    products = []
    options = []
    
    # 데이터 정제 및 변환
    for index, row in df.iterrows():
        # 필수 정보 확인
        bank = str(row.get(found_cols.get('kor_co_nm'), '')).strip()
        name = str(row.get(found_cols.get('fin_prdt_nm'), '')).strip()
        
        if not bank or bank == 'nan' or not name or name == 'nan':
            continue

        # 고유 코드 생성 (은행+상품명 기반)
        p_cd = re.sub(r'[^a-zA-Z0-9]', '', f"{bank}{name}")[:20]
        
        # 상품 정보
        products.append({
            'fin_prdt_cd': p_cd,
            'kor_co_nm': bank,
            'fin_prdt_nm': name,
            'join_way': str(row.get(found_cols.get('join_way'), '정보 없음')),
            'mtrt_int': str(row.get(found_cols.get('mtrt_int'), '정보 없음')),
            'etc_note': str(row.get(found_cols.get('etc_note'), '정보 없음')),
            'pref_categories': json.dumps(["엑셀 데이터"], ensure_ascii=False)
        })

        # 금리 정보 (기간별 데이터 분리 로직 - 엑셀 구조에 따라 조정 가능)
        # 기본적으로 12, 24, 36개월 옵션을 생성하거나 엑셀에 명시된 값을 사용
        terms = [12, 24, 36]
        base_r = row.get(found_cols.get('intr_rate'), 0)
        max_r = row.get(found_cols.get('intr_rate2'), base_r)
        
        # 숫자가 아닌 경우 처리
        try:
            base_r = float(base_r) if pd.notnull(base_r) else 0
            max_r = float(max_r) if pd.notnull(max_r) else base_r
        except:
            base_r, max_r = 0, 0

        for t in terms:
            options.append({
                'fin_prdt_cd': p_cd,
                'save_trm': t,
                'intr_rate': base_r,
                'intr_rate2': max_r
            })

    return products, options, None
