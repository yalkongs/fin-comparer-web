import pandas as pd
import json
import re

def process_financial_excel(file_path, category):
    """
    금융감독원 실제 엑셀 데이터 분석 결과를 반영한 최적화 프로세서입니다.
    """
    try:
        # 1. 파일 읽기 (HTML 기반 XLS 및 일반 XLS/XLSX 대응)
        try:
            df = pd.read_excel(file_path)
        except Exception:
            df_list = pd.read_html(file_path)
            df = df_list[0] if df_list else None
            
        if df is None:
            return None, None, "파일 형식을 분석할 수 없습니다."

        # 2. 헤더 클렌징 (분석 결과: \n 줄바꿈 및 다중 공백 처리 필수)
        df.columns = [str(c).replace('\n', ' ').replace('\r', ' ').replace('  ', ' ').strip() for c in df.columns]
        
    except Exception as e:
        return None, None, f"분석 중 오류 발생: {str(e)}"

    # 3. 카테고리별 전략적 컬럼 매핑 (분석 결과 반영)
    if category == 'credit': # 대출은 '최저'가 기본 금리 기준이 되어야 함
        base_keys = ['최저 금리', '최저금리', '평균 금리', '평균금리']
        max_keys = ['최고 금리', '최고금리', '최대금리']
    else: # 예적금 및 입출금
        base_keys = ['세전 이자율', '저축 금리', '기준금리', '기본금리', '연리']
        max_keys = ['최고 우대금리', '우대금리', '최고금리']

    col_map = {
        'bank': ['금융회사', '금융회사명', '금융기관'],
        'name': ['상품명', '금융상품명'],
        'base_rate': base_keys,
        'max_rate': max_keys,
        'join_way': ['가입방법', '가입경로', '가입제한'],
        'note': ['우대조건', '유의사항', '대출종류', '금리 방식', '이자계산방식', '적립방식']
    }

    def find_actual_col(keys):
        for k in keys:
            for col in df.columns:
                if k in col: return col
        return None

    c_bank = find_actual_col(col_map['bank'])
    c_name = find_actual_col(col_map['name'])
    c_base = find_actual_col(col_map['base_rate'])
    c_max = find_actual_col(col_map['max_rate'])
    
    if not c_bank or not c_name:
        return None, None, "필수 항목(은행명, 상품명)을 찾을 수 없는 양식입니다."

    products = []
    options = []
    
    for idx, row in df.iterrows():
        bank = str(row.get(c_bank, '')).strip()
        name = str(row.get(c_name, '')).strip()
        if not bank or bank == 'nan' or not name or name == 'nan': continue

        # 상세 정보 통합 (분석된 모든 참고 컬럼 활용)
        note_parts = []
        for k_list in col_map['note']:
            col = find_actual_col([k_list])
            val = str(row.get(col, '')).strip()
            if col and val and val != 'nan':
                note_parts.append(f"[{col}] {val}")
        
        full_note = " | ".join(note_parts)

        # 금리 수치 정밀 추출
        def to_float(val):
            if pd.isnull(val): return 0.0
            try:
                # 숫자 외 문자(%, , 등) 제거
                s = re.sub(r'[^0-9\.]', '', str(val))
                return float(s) if s else 0.0
            except: return 0.0

        base_rate = to_float(row.get(c_base))
        max_rate = to_float(row.get(c_max))
        if max_rate == 0: max_rate = base_rate

        p_cd = f"EX_{category}_{idx}_{re.sub(r'[^a-zA-Z0-9]', '', bank)[:5]}"
        
        # 키워드 기반 우대 태그 자동화
        tags = []
        for kw in ["첫거래", "첫 거래", "급여", "자동이체", "카드", "앱", "마케팅"]:
            if kw in full_note: tags.append(kw.replace(" ", ""))

        products.append({
            'fin_prdt_cd': p_cd,
            'kor_co_nm': bank,
            'fin_prdt_nm': name,
            'join_way': str(row.get(find_actual_col(col_map['join_way']), '정보 없음')),
            'mtrt_int': "상세 정보 참조",
            'etc_note': full_note,
            'pref_categories': json.dumps(list(set(tags)) if tags else ["일반"], ensure_ascii=False)
        })

        # DB 일관성을 위한 기간별 데이터 생성 (기본 12, 24, 36개월)
        for t in [12, 24, 36]:
            options.append({'fin_prdt_cd': p_cd, 'save_trm': t, 'intr_rate': base_rate, 'intr_rate2': max_rate})

    return products, options, None
