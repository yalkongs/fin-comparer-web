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
        # xlrd 엔진을 명시적으로 사용하거나 HTML 파싱 시도
        try:
            df = pd.read_excel(file_path)
        except Exception:
            try:
                df_list = pd.read_html(file_path)
                df = df_list[0] if df_list else None
            except:
                df = None
            
        if df is None:
            return None, None, "파일 내용을 읽을 수 없습니다. (xlrd 라이브러리 설치 확인 필요)"

        # 2. 헤더 클렌징 (줄바꿈 제거 및 모든 공백 제거하여 비교 용이하게 함)
        # 엑셀의 헤더와 우리가 찾을 키워드 양쪽 모두 공백을 제거하고 비교합니다.
        raw_cols = df.columns.tolist()
        df.columns = [str(c).replace('\n', '').replace('\r', '').replace(' ', '').strip() for c in df.columns]
        
    except Exception as e:
        return None, None, f"분석 중 오류 발생: {str(e)}"

    # 3. 데이터 정제 함수
    def to_float(val):
        if pd.isnull(val) or str(val).strip() in ['-', '']: return 0.0
        try:
            # %, 쉼표 등 제거하고 숫자만 추출
            s = re.sub(r'[^0-9\.]', '', str(val))
            return float(s) if s else 0.0
        except: return 0.0

    # 4. 컬럼 매핑 사전 (공백 없이 정의)
    col_map = {
        'bank': ['금융회사', '금융기관', '은행명'],
        'name': ['상품명', '대출종류', '금융상품명'],
        'base_rate': ['세전이자율', '평균금리', '최저금리', '기준금리', '저축금리'],
        'max_rate': ['최고우대금리', '최고금리', '우대금리']
    }

    def find_actual_col(keys):
        for k in keys:
            # 키워드와 컬럼명 모두 공백 제거 후 비교
            clean_k = k.replace(' ', '')
            for col in df.columns:
                if clean_k in col: return col
        return None

    c_bank = find_actual_col(col_map['bank'])
    c_name = find_actual_col(col_map['name'])
    c_base = find_actual_col(col_map['base_rate'])
    c_max = find_actual_col(col_map['max_rate'])
    
    # 5. 필수 컬럼 체크 (에러 발생 시 현재 헤더 정보 포함)
    if not c_bank or not c_name:
        return None, None, f"필수 컬럼(은행명, 상품명)을 찾을 수 없습니다. (현재 감지된 헤더: {', '.join(df.columns)})"

    products = []
    options = []
    
    for idx, row in df.iterrows():
        bank = str(row.get(c_bank, '')).strip()
        name = str(row.get(c_name, '')).strip()
        
        # 유효하지 않은 행 건너뛰기
        if not bank or bank in ['nan', ''] or not name or name in ['nan', '']:
            continue
        
        base_rate = to_float(row.get(c_base))
        # max_rate가 없으면 base_rate와 동일하게 설정
        max_rate = to_float(row.get(c_max)) if c_max else base_rate
        if max_rate == 0 and base_rate > 0: max_rate = base_rate

        # 금리 정보가 아예 없는 행은 무시
        if base_rate == 0 and max_rate == 0: continue

        # 상세 정보 통합 (매핑된 컬럼 제외한 나머지)
        note_parts = []
        for i, col in enumerate(df.columns):
            if col not in [c_bank, c_name, c_base, c_max]:
                val = str(row.iloc[i]).strip()
                if val and val not in ['nan', '-', '']:
                    # 원본 컬럼명(raw_cols) 사용 시 가독성 좋음
                    note_parts.append(f"[{raw_cols[i]}] {val}")
        
        full_note = " | ".join(note_parts)
        p_cd = f"EX_{category}_{idx}_{re.sub(r'[^a-zA-Z0-9]', '', bank)[:5]}"
        
        # 우대 태그 생성
        tags = []
        for kw in ["첫거래", "급여", "자동이체", "카드", "앱", "마케팅"]:
            if kw in full_note: tags.append(kw)

        products.append({
            'fin_prdt_cd': p_cd,
            'kor_co_nm': bank,
            'fin_prdt_nm': name,
            'join_way': "상세 정보 참조",
            'mtrt_int': "상세 정보 참조",
            'etc_note': full_note,
            'pref_categories': json.dumps(list(set(tags)) if tags else ["일반"], ensure_ascii=False)
        })

        for t in [12, 24, 36]:
            options.append({'fin_prdt_cd': p_cd, 'save_trm': t, 'intr_rate': base_rate, 'intr_rate2': max_rate})

    return products, options, None
