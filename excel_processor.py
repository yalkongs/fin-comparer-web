import pandas as pd
import json
import re

def process_financial_excel(file_path, category):
    """
    금융감독원 엑셀 파일(.xls, .xlsx)을 읽어서 DB에 저장할 수 있는 형식으로 변환합니다.
    사용자가 제공한 실제 파일 구조(헤더 내 줄바꿈 등)를 완벽히 반영합니다.
    """
    try:
        # 1. 파일 읽기 (금감원 XLS는 가끔 HTML 테이블일 수 있음)
        try:
            df = pd.read_excel(file_path)
        except Exception:
            df_list = pd.read_html(file_path)
            df = df_list[0] if df_list else None
            
        if df is None:
            return None, None, "파일을 읽을 수 없습니다. 올바른 엑셀 형식인지 확인해주세요."

        # 2. 헤더 정문화 (줄바꿈 제거 및 공백 제거)
        df.columns = [str(c).replace('\n', ' ').replace('  ', ' ').strip() for c in df.columns]
        
    except Exception as e:
        return None, None, f"분석 중 오류 발생: {str(e)}"

    # 3. 컬럼 매핑 사전 (실제 파일 기반 고도화)
    col_map = {
        'bank': ['금융회사', '금융회사명', '금융기관'],
        'name': ['상품명', '금융상품명'],
        'base_rate': ['세전 이자율', '세전\n이자율', '평균 금리', '최저 금리', '기준금리'],
        'max_rate': ['최고 우대금리', '최고\n우대금리', '최고 금리', '우대금리'],
        'join_way': ['가입방법', '가입제한 여부', '가입제한\n여부'],
        'note': ['우대조건', '유의사항', '대출종류', '금리 방식', '적립방식', '이자계산방식']
    }

    def find_actual_col(keys):
        for k in keys:
            for col in df.columns:
                if k in col:
                    return col
        return None

    c_bank = find_actual_col(col_map['bank'])
    c_name = find_actual_col(col_map['name'])
    c_base = find_actual_col(col_map['base_rate'])
    c_max = find_actual_col(col_map['max_rate'])
    
    if not c_bank or not c_name:
        return None, None, f"필수 컬럼을 찾을 수 없습니다. (현재 헤더: {', '.join(df.columns)})"

    products = []
    options = []
    
    # 4. 데이터 추출 루프
    for idx, row in df.iterrows():
        bank = str(row.get(c_bank, '')).strip()
        name = str(row.get(c_name, '')).strip()
        
        if not bank or bank == 'nan' or not name or name == 'nan':
            continue

        # 상세 정보 수집 (여러 컬럼 합치기)
        notes = []
        for k in col_map['note']:
            actual_col = find_actual_col([k])
            if actual_col and pd.notnull(row.get(actual_col)):
                notes.append(f"{k}: {row.get(actual_col)}")
        
        full_note = " | ".join(notes) if notes else "정보 없음"
        
        # 금리 숫자 변환 (%, 쉼표 제거)
        def clean_rate(val):
            if pd.isnull(val): return 0.0
            s_val = str(val).replace('%', '').replace(',', '').strip()
            try:
                return float(s_val)
            except ValueError:
                return 0.0

        base_rate = clean_rate(row.get(c_base))
        max_rate = clean_rate(row.get(c_max))
        if max_rate == 0: max_rate = base_rate

        # 고유 코드 생성
        p_cd = re.sub(r'[^a-zA-Z0-9]', '', f"{bank}{name}")[:30] + f"_{idx}"
        
        # 우대 태그 자동 생성
        pref_tags = []
        for kw in ["첫거래", "첫 거래", "급여", "자동이체", "카드", "앱", "마케팅"]:
            if kw in full_note:
                pref_tags.append(kw.replace(" ", ""))

        products.append({
            'fin_prdt_cd': p_cd,
            'kor_co_nm': bank,
            'fin_prdt_nm': name,
            'category': category,
            'join_way': str(row.get(find_actual_col(col_map['join_way']), '정보 없음')),
            'mtrt_int': "엑셀 상세 정보 참조",
            'etc_note': full_note,
            'pref_categories': json.dumps(list(set(pref_tags)) if pref_tags else ["일반"], ensure_ascii=False)
        })

        # 기간별 옵션 (대출은 기간 개념이 다르지만, 앱 UI 호환을 위해 12개월 기본 생성)
        terms = [12, 24, 36]
        for t in terms:
            options.append({
                'fin_prdt_cd': p_cd,
                'save_trm': t,
                'intr_rate': base_rate,
                'intr_rate2': max_rate
            })

    return products, options, None
