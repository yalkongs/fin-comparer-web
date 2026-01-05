import pandas as pd
import json
import re
import numpy as np

def process_financial_excel(file_path, category):
    """
    금융감독원 표준 엑셀 양식을 분석하여 데이터를 추출합니다.
    """
    try:
        # 데이터가 보통 2~4행부터 시작할 수 있으므로 헤더를 찾는 과정 포함
        df = pd.read_excel(file_path)
        
        # 실제 데이터가 시작되는 헤더 행 찾기 (금융회사명이 있는 행)
        header_row_idx = 0
        for i, row in df.head(10).iterrows():
            if any("금융회사" in str(cell) for cell in row):
                header_row_idx = i
                break
        
        # 헤더를 재설정하여 읽기
        df = pd.read_excel(file_path, header=header_row_idx)
        df.columns = [str(c).strip() for c in df.columns]
        
    except Exception as e:
        return None, None, f"파일 읽기 실패: {str(e)}"

    products = []
    options = []
    
    # 1. 컬럼 매핑 로직 (유연한 검색)
    def find_col(keywords):
        for col in df.columns:
            if any(k in col for k in keywords):
                return col
        return None

    col_bank = find_col(['금융회사명', '금융기관', '은행'])
    col_name = find_col(['금융상품명', '상품명'])
    col_join = find_col(['가입방법', '가입경로'])
    col_mtrt = find_col(['만기 후 이자율', '만기후'])
    col_note = find_col(['우대조건', '우대사항', '유의사항'])
    
    # 금리 컬럼 찾기 (12개월 기준을 우선적으로 찾음)
    col_base_rate = find_col(['저축 금리', '기준금리', '최저금리', '평균금리'])
    col_max_rate = find_col(['최고 우대금리', '최고금리', '우대금리'])

    # 컬럼이 하나도 없으면 오류
    if not col_bank or not col_name:
        return None, None, "필수 항목(금융회사명, 상품명)을 찾을 수 없습니다. 엑셀 헤더를 확인해주세요."

    for index, row in df.iterrows():
        bank = str(row.get(col_bank, '')).strip()
        name = str(row.get(col_name, '')).strip()
        
        if not bank or bank == 'nan' or name == 'nan': continue

        # 고유 ID 생성
        p_cd = f"EXCEL_{category}_{index}"
        
        # 상세 설명 정제
        note = str(row.get(col_note, ''))
        pref_tags = []
        # 우대조건 키워드 분석하여 태그화
        for keyword in ["급여", "첫거래", "첫 거래", "자동이체", "카드", "관리비", "오픈뱅킹"]:
            if keyword in note:
                pref_tags.append(keyword)

        products.append({
            'fin_prdt_cd': p_cd,
            'kor_co_nm': bank,
            'fin_prdt_nm': name,
            'join_way': str(row.get(col_join, '정보 없음')),
            'mtrt_int': str(row.get(col_mtrt, '정보 없음')),
            'etc_note': note if note != 'nan' else '정보 없음',
            'pref_categories': json.dumps(pref_tags if pref_tags else ["일반"], ensure_ascii=False)
        })

        # 금리 데이터 추출 (숫자형으로 변환)
        try:
            r1 = float(row.get(col_base_rate, 0)) if pd.notnull(row.get(col_base_rate)) else 0
            r2 = float(row.get(col_max_rate, 0)) if pd.notnull(row.get(col_max_rate)) else r1
            if r2 < r1: r2 = r1 # 최고금리가 기본보다 낮을 수 없음
        except:
            r1, r2 = 0, 0

        # 기간별 옵션 (엑셀에 기간별 컬럼이 따로 없을 경우 현재 추출값으로 12, 24, 36개월 생성)
        for t in [12, 24, 36]:
            options.append({
                'fin_prdt_cd': p_cd,
                'save_trm': t,
                'intr_rate': r1,
                'intr_rate2': r2
            })

    return products, options, None
