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
    
    # Products table
    cursor.execute('''CREATE TABLE IF NOT EXISTS products (
        id TEXT PRIMARY KEY,
        fin_prdt_cd TEXT,
        kor_co_nm TEXT,
        fin_prdt_nm TEXT,
        category TEXT,
        join_way TEXT,
        mtrt_int TEXT,
        etc_note TEXT,
        pref_categories TEXT
    )''')
    
    # Options table (Rates)
    cursor.execute('''CREATE TABLE IF NOT EXISTS options (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id TEXT,
        save_trm INTEGER,
        intr_rate REAL,
        intr_rate2 REAL,
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

def save_data(category, products_list, options_list):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 1. 기존 데이터 삭제 (해당 카테고리만)
        cursor.execute("DELETE FROM options WHERE product_id IN (SELECT id FROM products WHERE category = ?)", (category,))
        cursor.execute("DELETE FROM products WHERE category = ?", (category,))
        
        # 2. 신규 상품 데이터 삽입
        for p in products_list:
            cursor.execute('''INSERT INTO products 
                (id, fin_prdt_cd, kor_co_nm, fin_prdt_nm, category, join_way, mtrt_int, etc_note, pref_categories)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                (f"{category}_{p['fin_prdt_cd']}", p['fin_prdt_cd'], p['kor_co_nm'], p['fin_prdt_nm'], category, 
                 p.get('join_way', '정보 없음'), p.get('mtrt_int', '정보 없음'), p.get('etc_note', '정보 없음'), 
                 p.get('pref_categories', '[]')))
                
        # 3. 신규 금리 옵션 삽입
        for o in options_list:
            cursor.execute('''INSERT INTO options (product_id, save_trm, intr_rate, intr_rate2)
                VALUES (?, ?, ?, ?)''',
                (f"{category}_{o['fin_prdt_cd']}", int(o['save_trm']), o['intr_rate'], o['intr_rate2']))
                
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
        SELECT p.id, p.kor_co_nm, p.fin_prdt_nm, o.save_trm, o.intr_rate, o.intr_rate2, p.join_way, p.mtrt_int, p.etc_note, p.pref_categories
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

def get_product_detail(product_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    prod = cursor.fetchone()
    if prod:
        cursor.execute("SELECT save_trm, intr_rate, intr_rate2 FROM options WHERE product_id = ?", (product_id,))
        opts = cursor.fetchall()
        conn.close()
        return {'product': prod, 'options': opts}
    conn.close()
    return None
