from flask import Flask, render_template, jsonify, request, redirect, url_for
from pymongo import MongoClient
from datetime import datetime, timedelta
from bson import ObjectId
from search import search_bp
from login import auth_bp
from mypage import mypage_bp
from ticket import ticket_bp
import os

app = Flask(__name__)

# 세션 설정
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-this-in-production')
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=1)

# Blueprint 등록
app.register_blueprint(search_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(mypage_bp)
app.register_blueprint(ticket_bp)

# MongoDB 연결
client = MongoClient('mongodb://localhost:27017/')
db = client['yangdomany']

@app.route('/')
def main():
    # 인기순으로 정렬하여 상위 6개 가져오기
    shows = list(db.shows.find().sort('popularity', -1).limit(6))
    actors = list(db.actors.find().sort('count', -1))
    
    # ObjectId를 문자열로 변환
    for show in shows:
        if '_id' in show:
            show['id'] = show['_id']
            del show['_id']
    
    for actor in actors:
        if '_id' in actor:
            del actor['_id']
    
    return render_template('main.html', shows=shows, actors=actors)

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
    
    query = {}
    if show_id:
        query['show_id'] = show_id
    
    tickets = list(db.tickets.find(query).sort('created_at', -1))
    
    # 좌석 마스킹 import 추가 필요
    from ticket import mask_seat_info
    
    for ticket in tickets:
        if '_id' in ticket:
            ticket['id'] = ticket['_id']
            del ticket['_id']
        if 'created_at' in ticket:
            ticket['created_at'] = ticket['created_at'].strftime('%Y-%m-%d')
        
        # 좌석 정보 마스킹 추가
        if 'seat' in ticket:
            ticket['seat_original'] = ticket['seat']
            ticket['seat'] = mask_seat_info(ticket['seat'])
    
    return jsonify(tickets)

@app.route('/api/search')
def search():
    query = request.args.get('q', '').lower()
    
    # 작품 검색 (제목에서 검색)
    show_results = list(db.shows.find({
        'title': {'$regex': query, '$options': 'i'}
    }))
    
    # 배우 검색
    actor_results = list(db.actors.find({
        'name': {'$regex': query, '$options': 'i'}
    }))
    
    # 배우가 검색되면 해당 배우가 출연한 작품들 포함
    if actor_results and not show_results:
        actor_names = [a['name'] for a in actor_results]
        show_ids = [cast['show_id'] for cast in db.show_casts.find({'actor': {'$in': actor_names}})]
        show_results = list(db.shows.find({'_id': {'$in': show_ids}}))
    
    # ObjectId 변환
    for show in show_results:
        if '_id' in show:
            show['id'] = show['_id']
            del show['_id']
    
    for actor in actor_results:
        if '_id' in actor:
            del actor['_id']
    
    return jsonify({
        'shows': show_results,
        'actors': actor_results
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

if __name__ == '__main__':
    app.run(debug=True, port=5000)