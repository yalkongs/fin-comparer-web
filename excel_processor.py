import pandas as pd
import json
import re

def process_financial_excel(file_path, target_category):
    """
    엑셀 파일을 분석하고, 신용대출의 경우 일반신용과 한도대출을 분리하여 처리합니다.
    """
    try:
        try:
            df = pd.read_excel(file_path)
        except Exception:
            df_list = pd.read_html(file_path)
            df = df_list[0] if df_list else None
            
        if df is None: return None, None, "파일을 읽을 수 없습니다."

        # 헤더 클렌징
        raw_cols = df.columns.tolist()
        df.columns = [str(c).replace('\n', '').replace('\r', '').replace(' ', '').strip() for c in df.columns]
        
    except Exception as e:
        return None, None, f"분석 중 오류 발생: {str(e)}"

    def to_float(val):
        if pd.isnull(val) or str(val).strip() in ['-', '']: return 0.0
        try:
            s = re.sub(r'[^0-9\.]', '', str(val))
            return float(s) if s else 0.0
        except: return 0.0

    col_map = {
        'bank': ['금융회사', '금융기관', '은행명'],
        'name': ['상품명', '대출종류', '금융상품명'],
        'base_rate': ['세전이자율', '평균금리', '최저금리', '기준금리', '저축금리', '900점초과', '801~900점'],
        'max_rate': ['최고우대금리', '최고금리', '우대금리']
    }

    def find_actual_col(keys):
        for k in keys:
            clean_k = k.replace(' ', '')
            for col in df.columns:
                if clean_k in col: return col
        return None

    c_bank = find_actual_col(col_map['bank'])
    c_name = find_actual_col(col_map['name'])
    c_base = find_actual_col(col_map['base_rate'])
    c_max = find_actual_col(col_map['max_rate'])
    
    if not c_bank or not c_name:
        return None, None, f"필수 컬럼을 찾을 수 없습니다. (감지된 헤더: {', '.join(df.columns)})"

    products = []
    options = []
    
    for idx, row in df.iterrows():
        bank = str(row.get(c_bank, '')).strip()
        name = str(row.get(c_name, '')).strip()
        
        if not bank or bank in ['nan', ''] or not name or name in ['nan', '']:
            continue
        
        # --- [중요] 일반신용과 한도대출 분리 로직 ---
        is_limit_loan = "마이너스" in name or "한도대출" in name
        
        # 업로드 시 선택한 카테고리에 맞는 데이터만 처리
        if "credit" in target_category:
            if target_category == "credit_limit" and not is_limit_loan: continue
            if target_category == "credit_general" and is_limit_loan: continue
        # ------------------------------------------

        base_rate = to_float(row.get(c_base))
        max_rate = to_float(row.get(c_max)) if c_max else base_rate
        if max_rate == 0 and base_rate > 0: max_rate = base_rate
        if base_rate == 0 and max_rate == 0: continue

        note_parts = []
        for i, col in enumerate(df.columns):
            if col not in [c_bank, c_name, c_base, c_max]:
                val = str(row.iloc[i]).strip()
                if val and val not in ['nan', '-', '']:
                    note_parts.append(f"[{raw_cols[i]}] {val}")
        
        full_note = " | ".join(note_parts)
        p_cd = f"EX_{target_category}_{idx}_{re.sub(r'[^a-zA-Z0-9]', '', bank)[:5]}"
        
        tags = []
        for kw in ["첫거래", "급여", "자동이체", "카드", "앱"]:
            if kw in full_note: tags.append(kw)

        products.append({
            'fin_prdt_cd': p_cd,
            'kor_co_nm': bank,
            'fin_prdt_nm': name,
            'category': target_category, # 분류된 카테고리 저장
            'join_way': "상세 정보 참조",
            'mtrt_int': "상세 정보 참조",
            'etc_note': full_note,
            'pref_categories': json.dumps(list(set(tags)) if tags else ["일반"], ensure_ascii=False)
        })

        for t in [12, 24, 36]:
            options.append({'fin_prdt_cd': p_cd, 'save_trm': t, 'intr_rate': base_rate, 'intr_rate2': max_rate})

    return products, options, None
