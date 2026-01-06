from flask import Flask, render_template, jsonify, request
from database import init_db, get_last_update, update_timestamp, save_data, query_best_products
from api_client import fetch_from_api, API_KEY
import threading
import json
import os
from excel_processor import process_financial_excel
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize DB on start
init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/status')
def get_status():
    from database import get_last_update, get_categories_status
    return jsonify({
        'last_updated': get_last_update() or '데이터 없음',
        'categories': get_categories_status()
    })

@app.route('/api/products')
def get_products():
    category = request.args.get('category', 'deposit')
    term = int(request.args.get('term', 12))
    products = query_best_products(category, term, limit=50)
    
    result = []
    for p in products:
        result.append({
            'id': p[0],
            'bank': p[1],
            'name': p[2],
            'term': p[3],
            'rate': p[4],
            'rate2': p[5],
            'join_way': p[6],
            'mtrt_int': p[7],
            'etc_note': p[8],
            'pref_categories': json.loads(p[9] if p[9] else '[]'),
            'diff_score': p[10], # Complexity Score
            'prev_rate': p[11]   # For Trends
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
    category = request.form.get('category') # deposit, saving, credit, demand
    
    if file.filename == '' or category not in ['deposit', 'saving', 'credit', 'demand']:
        return jsonify({'error': '유효하지 않은 요청입니다.'}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    # 엑셀 프로세싱
    p, o, err = process_financial_excel(filepath, category)
    if err:
        return jsonify({'error': err}), 500

    save_data(category, p, o)
    update_timestamp()
    
    return jsonify({'message': f'{category} 데이터가 성공적으로 업데이트되었습니다.'})

def start_background_sync():
    def sync_task():
        categories = ['deposit', 'saving', 'credit', 'demand']
        # API 동기화는 이제 백업용으로만 작동하거나 생략 가능
        # 사용자가 엑셀을 업로드하므로 초기 MOCK 데이터를 유지하거나 빈 상태로 시작
        pass

    thread = threading.Thread(target=sync_task)
    thread.daemon = True
    thread.start()

@app.route('/api/update', methods=['POST'])
def update_route():
    start_background_sync()
    return jsonify({'message': 'Synchronization started in background'})

if __name__ == '__main__':
    # Initial check if data exists, if not, trigger a sync
    if not get_last_update():
        print("Empty database detected. Starting initial sync...")
        start_background_sync()
        
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port)
