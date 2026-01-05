import pandas as pd
import json
import re

def process_financial_excel(file_path, category):
    """
    제공된 실제 엑셀 파일(적금, 정기예금, 개인신용대출)의 구조를 정밀 분석하여
    데이터를 추출하는 최적화된 프로세서입니다.
    """
    try:
        # 1. 파일 읽기 (금감원 특유의 구형 XLS 대응)
        try:
            df = pd.read_excel(file_path)
        except Exception:
            df_list = pd.read_html(file_path)
            df = df_list[0] if df_list else None
            
        if df is None:
            return None, None, "파일 내용을 읽을 수 없습니다."

        # 2. 헤더 클렌징 (줄바꿈 제거 및 앞뒤 공백 제거)
        df.columns = [str(c).replace('\n', ' ').replace('\r', ' ').replace('  ', ' ').strip() for c in df.columns]
        
    except Exception as e:
        return None, None, f"분석 중 오류 발생: {str(e)}"

    # 3. 데이터 정제 함수
    def to_float(val):
        if pd.isnull(val) or str(val).strip() == '-': return 0.0
        try:
            # %, 쉼표 등 제거하고 숫자만 추출
            s = re.sub(r'[^0-9\.]', '', str(val))
            return float(s) if s else 0.0
        except: return 0.0

    products = []
    options = []
    
    # 4. 카테고리별 컬럼 설정
    if category == 'credit':
        c_bank = '금융회사'
        c_name = '대출종류' # 신용대출 파일에는 '상품명' 대신 '대출종류'가 있음
        c_base = '평균금리'
        c_max = '평균금리' # 신용대출 파일 특성상 평균치를 기준으로 표시
    else:
        c_bank = '금융회사'
        c_name = '상품명'
        c_base = '세전 이자율'
        c_max = '최고 우대금리'

    # 실제 존재하는 컬럼인지 확인 (유연성 확보)
    actual_cols = df.columns.tolist()
    if c_bank not in actual_cols:
        # '금융회사명' 등의 유사어 검색
        for col in actual_cols:
            if '금융회사' in col: c_bank = col; break
    
    if c_name not in actual_cols:
        for col in actual_cols:
            if '상품' in col or '종류' in col: c_name = col; break

    if c_base not in actual_cols:
        for col in actual_cols:
            if '이자율' in col or '금리' in col: c_base = col; break

    # 5. 데이터 추출
    for idx, row in df.iterrows():
        bank = str(row.get(c_bank, '')).strip()
        name = str(row.get(c_name, '')).strip()
        
        # 유효하지 않은 행 건너뛰기
        if not bank or bank == 'nan' or not name or name == 'nan': continue
        
        base_rate = to_float(row.get(c_base))
        max_rate = to_float(row.get(c_max, base_rate))
        
        # 금리 정보가 없는 행은 무시
        if base_rate == 0 and max_rate == 0: continue

        # 상세 설명 통합
        note_parts = []
        for col in actual_cols:
            if col not in [c_bank, c_name, c_base, c_max]:
                val = str(row.get(col, '')).strip()
                if val and val != 'nan' and val != '-':
                    note_parts.append(f"[{col}] {val}")
        
        full_note = " | ".join(note_parts)
        p_cd = f"EX_{category}_{idx}_{re.sub(r'[^a-zA-Z0-9]', '', bank)[:5]}"
        
        # 우대 태그 자동 생성
        tags = []
        for kw in ["첫거래", "급여", "자동이체", "카드", "앱", "마케팅"]:
            if kw in full_note: tags.append(kw)

        products.append({
            'fin_prdt_cd': p_cd,
            'kor_co_nm': bank,
            'fin_prdt_nm': name,
            'join_way': str(row.get('가입방법', str(row.get('가입경로', '상세 정보 참조')))),
            'mtrt_int': "상세 정보 참조",
            'etc_note': full_note,
            'pref_categories': json.dumps(list(set(tags)) if tags else ["일반"], ensure_ascii=False)
        })

        # 기간별 옵션 생성 (신용대출은 고정/변동 개념이지만 UI 호환성을 위해 12개월 등 기본값 생성)
        for t in [12, 24, 36]:
            options.append({'fin_prdt_cd': p_cd, 'save_trm': t, 'intr_rate': base_rate, 'intr_rate2': max_rate})

    return products, options, None
