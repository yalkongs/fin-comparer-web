from flask import Flask, render_template, jsonify, request
from database import init_db, get_last_update, update_timestamp, save_data, query_best_products
from api_client import fetch_from_api, API_KEY
import threading
import json

app = Flask(__name__)

# Initialize DB on start
init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/status')
def status():
    return jsonify({
        'last_updated': get_last_update() or '데이터 없음'
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
            'pref_categories': json.loads(p[9] if p[9] else '[]')
        })
    return jsonify(result)

def start_background_sync():
    def sync_task():
        categories = ['deposit', 'saving', 'mortgage', 'credit']
        for cat in categories:
            p, o = fetch_from_api(cat, API_KEY)
            save_data(cat, p, o)
        update_timestamp()

    # Run in background to not block UI
    thread = threading.Thread(target=sync_task)
    thread.daemon = True # Ensure thread closes with app
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
        
    app.run(port=5001, debug=True)
