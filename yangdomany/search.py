from flask import Blueprint, render_template, request, jsonify
from pymongo import MongoClient

search_bp = Blueprint('search', __name__)

# MongoDB 연결
client = MongoClient('mongodb://localhost:27017/')
db = client['yangdomany']

@search_bp.route('/search')
def search_page():
    query = request.args.get('q', '')
    return render_template('search.html', query=query)

@search_bp.route('/api/search_all')
def search_all():
    query = request.args.get('q', '').strip()
    
    if not query:
        return jsonify({
            'shows': [],
            'tickets': [],
            'polaroids': [],
            'actors': []
        })
    
    # 공연 검색
    shows = list(db.shows.find({
        'title': {'$regex': query, '$options': 'i'}
    }))
    
    # 배우 검색
    actors = list(db.actors.find({
        'name': {'$regex': query, '$options': 'i'}
    }))
    
    # 배우 이름으로 공연 검색 (배우가 검색되었을 경우)
    if actors:
        actor_names = [a['name'] for a in actors]
        show_ids_from_cast = [cast['show_id'] for cast in db.show_casts.find({'actor': {'$in': actor_names}})]
        
        # 기존 검색 결과와 합치기
        existing_show_ids = [s['_id'] for s in shows]
        new_show_ids = [sid for sid in show_ids_from_cast if sid not in existing_show_ids]
        
        if new_show_ids:
            additional_shows = list(db.shows.find({'_id': {'$in': new_show_ids}}))
            shows.extend(additional_shows)
    
    # 공연 ID 목록
    show_ids = [s['_id'] for s in shows]
    
    # 티켓 검색 (공연명 또는 해당 공연 ID)
    tickets = list(db.tickets.find({
        '$or': [
            {'show_title': {'$regex': query, '$options': 'i'}},
            {'show_id': {'$in': show_ids}}
        ],
        'status': '판매중'
    }).sort('created_at', -1))
    
    # 폴라로이드 검색 (배우명, 공연명)
    polaroid_query = {
        '$or': [
            {'actor': {'$regex': query, '$options': 'i'}},
            {'show': {'$regex': query, '$options': 'i'}}
        ],
        'status': '거래중'
    }
    
    # 배우가 검색되었으면 배우명으로도 검색
    if actors:
        actor_names = [a['name'] for a in actors]
        polaroid_query = {
            '$or': [
                {'actor': {'$in': actor_names}},
                {'show': {'$regex': query, '$options': 'i'}}
            ],
            'status': '거래중'
        }
    
    polaroids = list(db.polaroids.find(polaroid_query).sort('created_at', -1))
    
    # ObjectId와 datetime 변환
    for show in shows:
        if '_id' in show:
            show['id'] = show['_id']
            del show['_id']
    
    for actor in actors:
        if '_id' in actor:
            del actor['_id']
    
    for ticket in tickets:
        if '_id' in ticket:
            ticket['id'] = ticket['_id']
            del ticket['_id']
        if 'created_at' in ticket and hasattr(ticket['created_at'], 'strftime'):
            ticket['created_at'] = ticket['created_at'].strftime('%Y-%m-%d')
    
    for polaroid in polaroids:
        if '_id' in polaroid:
            polaroid['id'] = polaroid['_id']
            del polaroid['_id']
        if 'created_at' in polaroid and hasattr(polaroid['created_at'], 'strftime'):
            polaroid['created_at'] = polaroid['created_at'].strftime('%Y-%m-%d')
    
    return jsonify({
        'shows': shows,
        'tickets': tickets,
        'polaroids': polaroids,
        'actors': actors
    })