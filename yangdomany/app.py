from dotenv import load_dotenv
load_dotenv() 
from flask import Flask, render_template, jsonify, request, redirect, url_for, session

from pymongo import MongoClient
from datetime import datetime, timedelta
from bson import ObjectId
from search import search_bp
from login import auth_bp
from mypage import mypage_bp
from ticket import ticket_bp
from oauth import oauth_bp, oauth
from admin import admin_bp
import os



app = Flask(__name__)
oauth.init_app(app)
# 세션 설정
app.secret_key = os.environ.get('SECRET_KEY', 'e13e5b2d2b72d126c883fad60d88ded4c1bea0159f1a324197eb4eb439f85809')
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = False  # 이 줄 추가 (로컬에서는 False)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=1)
# Blueprint 등록
app.register_blueprint(search_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(mypage_bp)
app.register_blueprint(ticket_bp)
app.register_blueprint(oauth_bp)
app.register_blueprint(admin_bp)
# MongoDB 연결
client = MongoClient('mongodb+srv://psunyong2:V8Zh6sdvBfaAdUYv@yangdomany.8pjaosi.mongodb.net/')
db = client['yangdomany']

@app.route('/')
def main():
    shows = list(db.shows.find().sort('popularity', -1).limit(6))
    actors = list(db.actors.find().sort('count', -1))
    
    for show in shows:
        if '_id' in show:
            show['id'] = show['_id']
            del show['_id']
    
    for actor in actors:
        if '_id' in actor:
            del actor['_id']
    
    # 세션 정보 전달
    return render_template('main.html', 
                         shows=shows, 
                         actors=actors,
                         logged_in=session.get('logged_in', False),
                         nickname=session.get('nickname', ''))

@app.route('/transfer')
def transfer():
    return render_template('transfer.html')

@app.route('/polaroid')
def polaroid():
    return render_template('polaroid.html')

@app.route('/api/shows')
def get_shows():
    category = request.args.get('category', '')
    
    query = {}
    if category:
        query['category'] = category
    
    shows = list(db.shows.find(query))
    
    # ObjectId를 문자열로 변환
    for show in shows:
        if '_id' in show:
            show['id'] = show['_id']
            del show['_id']
    
    return jsonify(shows)


@app.route('/api/tickets')
def get_tickets():
    show_id = request.args.get('show_id', type=int)
    
    query = {'status': 'approved'}  # 승인된 티켓만
    if show_id:
        query['show_id'] = show_id
    
    tickets = list(db.tickets.find(query).sort('created_at', -1))
    
    # mask_seat_info 함수 직접 정의 (import 제거)
    def mask_seat_info(seat):
        import re
        match = re.search(r'(\d+)열\s*(\d+)번', seat)
        if match:
            row = match.group(1)
            seat_num = int(match.group(2))
            start = max(1, seat_num - 2)
            end = seat_num + 2
            prefix = seat.split(match.group(0))[0]
            return f"{prefix}{row}열 {start}~{end}번"
        return seat
    
    # 나머지는 동일
    for ticket in tickets:
        if '_id' in ticket:
            ticket['id'] = ticket['_id']
            del ticket['_id']
        if 'created_at' in ticket:
            ticket['created_at'] = ticket['created_at'].strftime('%Y-%m-%d')
        
        if 'seat' in ticket:
            ticket['seat_original'] = ticket['seat']
            ticket['seat'] = mask_seat_info(ticket['seat'])
    
    return jsonify(tickets)

@app.route('/api/me')
def get_current_user():
    print(f"=== /api/me called ===")
    print(f"Cookies: {request.cookies}")
    print(f"Session: {dict(session)}")
    print(f"logged_in: {session.get('logged_in')}")
    print(f"=====================")
    
    if not session.get('logged_in'):
        return jsonify({'success': False}), 401
    
    user_id = session.get('user_id')
    user = db.users.find_one({'_id': ObjectId(user_id)})
    
    if user:
        user['_id'] = str(user['_id'])
        return jsonify({'success': True, 'user': user})
    
    return jsonify({'success': False}), 401
@app.route('/api/polaroids')
def get_polaroids():
    trade_type = request.args.get('type', '')
    actor = request.args.get('actor', '')
    
    query = {}
    if trade_type:
        query['type'] = trade_type
    if actor:
        query['actor'] = {'$regex': actor, '$options': 'i'}
    
    polaroids = list(db.polaroids.find(query).sort('created_at', -1))
    
    # ObjectId와 datetime 변환
    for item in polaroids:
        if '_id' in item:
            item['id'] = item['_id']
            del item['_id']
        if 'created_at' in item:
            item['created_at'] = item['created_at'].strftime('%Y-%m-%d')
    
    return jsonify(polaroids)

if __name__ == '__main__':

    app.run(debug=True, port=5000)


