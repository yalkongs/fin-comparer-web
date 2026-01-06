from flask import Flask, render_template, jsonify, request
from database import init_db, get_last_update, update_timestamp, save_data, query_best_products, get_categories_status
import json
import os
from excel_processor import process_financial_excel
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize DB on start
init_db()

def restore_from_saved_files():
    """서버에 보관된 최신 엑셀 파일들을 읽어 데이터베이스를 복구합니다."""
    categories = ['deposit', 'saving', 'credit', 'demand']
    for cat in categories:
        filename = f"latest_{cat}.xls"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(filepath):
            print(f"Restoring {cat} data from {filename}...")
            p, o, err = process_financial_excel(filepath, cat)
            if not err:
                save_data(cat, p, o)
    update_timestamp()

# 서버 시작 시 기존 파일이 있다면 복구 시도 (DB가 비어있을 경우 유용)
restore_from_saved_files()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/status')
def get_status():
    return jsonify({
        'last_updated': get_last_update() or '데이터 없음',
        'categories': get_categories_status()
    })

@app.route('/api/products')
def get_products():
    category = request.args.get('category', 'deposit')
    term = int(request.args.get('term', 12))
    products = query_best_products(category, term, limit=50)
    
    import re
    result = []
    for p in products:
        bank_name = p[1]
        # Remove suffixes like 은행, 뱅크, 주식회사 and redundant spaces
        bank_name = re.sub(r'(은행|뱅크|주식회사|\s)', '', bank_name)
        
        result.append({
            'id': p[0], 'bank': bank_name, 'name': p[2], 'term': p[3], 'rate': p[4], 'rate2': p[5],
            'join_way': p[6], 'mtrt_int': p[7], 'etc_note': p[8],
            'pref_categories': json.loads(p[9] if p[9] else '[]'),
            'diff_score': p[10], 'prev_rate': p[11]
        })
    return jsonify(result)

@app.route('/api/analysis')
def get_analysis():
    category = request.args.get('category', 'deposit')
    term = int(request.args.get('term', 12))
    from database import get_sector_analysis
    return jsonify(get_sector_analysis(category, term))

@app.route('/api/upload', methods=['POST'])
def upload_excel():
    if 'file' not in request.files:
        return jsonify({'error': '파일이 없습니다.'}), 400
    
    file = request.files['file']
    category = request.form.get('category')
    
    if file.filename == '' or category not in ['deposit', 'saving', 'credit', 'demand']:
        return jsonify({'error': '유효하지 않은 요청입니다.'}), 400

    # 카테고리별 고정 파일명으로 저장 (영속성 유지)
    filename = f"latest_{category}.xls"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    # 엑셀 프로세싱 및 DB 저장
    p, o, err = process_financial_excel(filepath, category)
    if err:
        return jsonify({'error': err}), 500

    save_data(category, p, o)
    update_timestamp()
    
    return jsonify({'message': f'{category} 데이터가 성공적으로 업데이트되었습니다.'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port)
