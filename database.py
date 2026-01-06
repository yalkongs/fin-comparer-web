import sqlite3
from datetime import datetime
import os

DB_PATH = "finance_products.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Meta table for update tracking
    cursor.execute('''CREATE TABLE IF NOT EXISTS meta (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')
    
    # Products table (Added diff_score)
    cursor.execute('''CREATE TABLE IF NOT EXISTS products (
        id TEXT PRIMARY KEY,
        fin_prdt_cd TEXT,
        kor_co_nm TEXT,
        fin_prdt_nm TEXT,
        category TEXT,
        join_way TEXT,
        mtrt_int TEXT,
        etc_note TEXT,
        pref_categories TEXT,
        diff_score INTEGER DEFAULT 0
    )''')
    
    # Options table (Added prev_rate for Trends)
    cursor.execute('''CREATE TABLE IF NOT EXISTS options (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id TEXT,
        save_trm INTEGER,
        intr_rate REAL,
        intr_rate2 REAL,
        prev_rate REAL,
        FOREIGN KEY (product_id) REFERENCES products (id)
    )''')
    
    conn.commit()
    conn.close()

def get_last_update():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM meta WHERE key = 'last_updated'")
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def update_timestamp():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('last_updated', ?)", (now,))
    conn.commit()
    conn.close()

def get_bank_sector(bank_name):
    major = ['국민은행', '우리은행', '신한은행', '하나은행', '농협은행', '기업은행']
    internet = ['카카오뱅크', '케이뱅크', '토스뱅크']
    if any(m in bank_name for m in major): return '시중은행'
    if any(i in bank_name for i in internet): return '인터넷뱅크'
    return '지방/기타은행'

def save_data(category, products_list, options_list):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 1. 기존 금리 백업 (Trends 기능용)
        prev_rates = {}
        cursor.execute("SELECT product_id, intr_rate2 FROM options")
        for pid, rate in cursor.fetchall():
            prev_rates[pid] = rate

        # 2. 기존 데이터 삭제
        if category == 'credit':
            cursor.execute("DELETE FROM options WHERE product_id IN (SELECT id FROM products WHERE category IN ('credit_general', 'credit_limit'))")
            cursor.execute("DELETE FROM products WHERE category IN ('credit_general', 'credit_limit')")
        else:
            cursor.execute("DELETE FROM options WHERE product_id IN (SELECT id FROM products WHERE category = ?)", (category,))
            cursor.execute("DELETE FROM products WHERE category = ?", (category,))
        
        # 3. 신규 상품 데이터 삽입
        for p in products_list:
            p_cat = p.get('category', category)
            p_id = f"{p_cat}_{p['fin_prdt_cd']}"
            
            # 우대조건 개수에 따른 난이도 점수 계산
            import json
            try:
                prefs = json.loads(p.get('pref_categories', '[]'))
                diff = min(3, len(prefs)) if isinstance(prefs, list) else 1
            except: diff = 1

            cursor.execute('''INSERT INTO products 
                (id, fin_prdt_cd, kor_co_nm, fin_prdt_nm, category, join_way, mtrt_int, etc_note, pref_categories, diff_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                (p_id, p['fin_prdt_cd'], p['kor_co_nm'], p['fin_prdt_nm'], p_cat, 
                 p.get('join_way', '정보 없음'), p.get('mtrt_int', '정보 없음'), p.get('etc_note', '정보 없음'), 
                 p.get('pref_categories', '[]'), diff))
                
        # 4. 신규 금리 옵션 삽입 (이전 금리와 비교)
        for o in options_list:
            o_cat = o.get('category', category)
            p_id = f"{o_cat}_{o['fin_prdt_cd']}"
            prev = prev_rates.get(p_id, o['intr_rate2']) # Default to current if new
            
            cursor.execute('''INSERT INTO options (product_id, save_trm, intr_rate, intr_rate2, prev_rate)
                VALUES (?, ?, ?, ?, ?)''',
                (p_id, int(o['save_trm']), o['intr_rate'], o['intr_rate2'], prev))
                
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def query_best_products(category, term=12, limit=20):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    order = "DESC" if category in ['deposit', 'saving'] else "ASC"
    
    query = f'''
        SELECT p.id, p.kor_co_nm, p.fin_prdt_nm, o.save_trm, o.intr_rate, o.intr_rate2, p.join_way, p.mtrt_int, p.etc_note, p.pref_categories, p.diff_score, o.prev_rate
        FROM products p
        JOIN options o ON p.id = o.product_id
        WHERE p.category = ? AND o.save_trm = ?
        ORDER BY o.intr_rate2 {order}
        LIMIT ?
    '''
    cursor.execute(query, (category, term, limit))
    results = cursor.fetchall()
    conn.close()
    return results

def get_sector_analysis(category, term=12):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.kor_co_nm, AVG(o.intr_rate2) 
        FROM products p JOIN options o ON p.id = o.product_id
        WHERE p.category = ? AND o.save_trm = ?
        GROUP BY p.kor_co_nm
    ''', (category, term))
    rows = cursor.fetchall()
    conn.close()
    
    analysis = {'시중은행': [], '인터넷뱅크': [], '지방/기타은행': []}
    for bank, rate in rows:
        sector = get_bank_sector(bank)
        analysis[sector].append(rate)
    
    result = []
    for sector, rates in analysis.items():
        avg = sum(rates) / len(rates) if rates else 0
        result.append({'sector': sector, 'avg_rate': round(avg, 2), 'count': len(rates)})
    return result
def get_categories_status():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT category, COUNT(*) FROM products GROUP BY category")
    rows = cursor.fetchall()
    conn.close()
    return {row[0]: row[1] for row in rows}
