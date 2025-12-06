from dotenv import load_dotenv
load_dotenv() 
from flask import Flask, render_template, jsonify, request, redirect, url_for, session, g

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
import hashlib



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
@app.template_filter('format_number')
def format_number_filter(value):
    """숫자를 천 단위 콤마로 포맷"""
    try:
        return f"{int(value):,}"
    except:
        return value

@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

@app.route('/')
def main():
    # 연극 TOP 10 (status 조건 제거)
    boxoffice_plays = list(db.shows.find(
        {
            'boxoffice_category': '연극',
            'boxoffice_rank': {'$exists': True, '$gte': 1, '$lte': 10}
        }
    ).sort('boxoffice_rank', 1))
    
    # 뮤지컬 TOP 10 (status 조건 제거)
    boxoffice_musicals = list(db.shows.find(
        {
            'boxoffice_category': '뮤지컬',
            'boxoffice_rank': {'$exists': True, '$gte': 1, '$lte': 10}
        }
    ).sort('boxoffice_rank', 1))
    
    # 인기 배우
    actors = list(db.actors.find().sort('count', -1).limit(10))
    
    # ObjectId 처리
    for show in boxoffice_plays + boxoffice_musicals:
        if '_id' in show:
            show['id'] = show.get('id', show['_id'])
            del show['_id']
    
    for actor in actors:
        if '_id' in actor:
            del actor['_id']
    
    # 업데이트 날짜
    update_date = None
    if boxoffice_plays and boxoffice_plays[0].get('boxoffice_updated_at'):
        update_date = boxoffice_plays[0]['boxoffice_updated_at']
    elif boxoffice_musicals and boxoffice_musicals[0].get('boxoffice_updated_at'):
        update_date = boxoffice_musicals[0]['boxoffice_updated_at']
    
    return render_template('main.html', 
                         boxoffice_plays=boxoffice_plays,
                         boxoffice_musicals=boxoffice_musicals,
                         update_date=update_date,
                         actors=actors,
                         logged_in=session.get('logged_in', False),
                         nickname=session.get('nickname', ''))
@app.route('/transfer')
def transfer():
    return render_template('transfer.html')

@app.route('/polaroid')
def polaroid():
    return render_template('polaroid.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(e):
    return render_template('500.html'), 500

@app.route('/support')
def support():
    return render_template('support.html')

@app.route('/api/shows')
def get_shows():
    category = request.args.get('category', '')
    
    query = {}
    if category:
        query['category'] = category
    
    shows = list(db.shows.find(query))
    
    for show in shows:
        if '_id' in show:
            show['id'] = show.get('id', show['_id'])
            del show['_id']
        # prices는 그대로 포함
    
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

@app.route('/api/actor-search/<actor_name>', methods=['POST'])
def increment_actor_search(actor_name):
    """배우 검색 카운트 증가"""
    result = db.actors.update_one(
        {'name': actor_name},
        {'$inc': {'count': 1}}
    )
    
    return jsonify({
        'success': True,
        'matched': result.matched_count > 0
    })
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



@app.before_request
def track_visitor():
    """모든 요청마다 방문자 기록"""
    
    # static 파일, API 제외
    if request.path.startswith('/static') or request.path.startswith('/api'):
        return
    
    ip = request.remote_addr
    user_agent = request.headers.get('User-Agent', '')
    
    # 익명 해시 (개인정보 보호)
    visitor_hash = hashlib.md5(f"{ip}{user_agent}".encode()).hexdigest()
    
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # 오늘 첫 방문인지 확인
    existing = db.visitor_log.find_one({
        'visitor_hash': visitor_hash,
        'visited_at': {'$gte': today}
    })
    
    if not existing:
        # 신규 방문 기록
        db.visitor_log.insert_one({
            'visitor_hash': visitor_hash,
            'ip': ip[:10],  # IP 일부만 저장 (개인정보 보호)
            'user_id': g.get('user', {}).get('_id') if hasattr(g, 'user') else None,
            'visited_at': datetime.now(),
            'user_agent': user_agent,
            'page': request.path
        })
        
        # 일별 통계 업데이트
        db.user_stats.update_one(
            {'date': today},
            {
                '$inc': {'visitors': 1, 'page_views': 1},
                '$setOnInsert': {
                    'new_users': 0,
                    'ticket_created': 0,
                    'ticket_contact': 0
                }
            },
            upsert=True
        )
    else:
        # 페이지뷰만 증가
        db.user_stats.update_one(
            {'date': today},
            {'$inc': {'page_views': 1}}
        )

if __name__ == '__main__':

    app.run(debug=True, port=5000)


