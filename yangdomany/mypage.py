from flask import Blueprint, render_template, request, jsonify
from pymongo import MongoClient
from bson import ObjectId
from login import login_required, get_current_user

mypage_bp = Blueprint('mypage', __name__)

# MongoDB 연결
client = MongoClient('mongodb+srv://psunyong2:V8Zh6sdvBfaAdUYv@yangdomany.8pjaosi.mongodb.net/'')
db = client['yangdomany']

@mypage_bp.route('/mypage')
@login_required
def mypage():
    user = get_current_user()
    return render_template('mypage.html', user=user)

@mypage_bp.route('/api/my-tickets')
def my_tickets():
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401
    
    # 내가 올린 티켓
    tickets = list(db.tickets.find({'seller': user['nickname']}).sort('created_at', -1))
    
    for ticket in tickets:
        if '_id' in ticket:
            ticket['id'] = ticket['_id']
            del ticket['_id']
        if 'created_at' in ticket and hasattr(ticket['created_at'], 'strftime'):
            ticket['created_at'] = ticket['created_at'].strftime('%Y-%m-%d')
    
    return jsonify({'success': True, 'tickets': tickets})

@mypage_bp.route('/api/my-polaroids')
def my_polaroids():
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401
    
    # 내가 올린 폴라로이드
    polaroids = list(db.polaroids.find({'seller': user['nickname']}).sort('created_at', -1))
    
    for item in polaroids:
        if '_id' in item:
            item['id'] = item['_id']
            del item['_id']
        if 'created_at' in item and hasattr(item['created_at'], 'strftime'):
            item['created_at'] = item['created_at'].strftime('%Y-%m-%d')
    
    return jsonify({'success': True, 'polaroids': polaroids})

@mypage_bp.route('/api/update-profile', methods=['POST'])
def update_profile():
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401
    
    data = request.json
    nickname = data.get('nickname', '').strip()
    phone = data.get('phone', '').strip()
    
    if not nickname or not phone:
        return jsonify({'success': False, 'message': '모든 항목을 입력해주세요.'}), 400
    
    # 닉네임 중복 확인 (자신 제외)
    if nickname != user['nickname']:
        existing = db.users.find_one({'nickname': nickname})
        if existing:
            return jsonify({'success': False, 'message': '이미 사용 중인 닉네임입니다.'}), 400
    
    # 프로필 업데이트
    db.users.update_one(
        {'_id': ObjectId(user['id'])},
        {'$set': {'nickname': nickname, 'phone': phone}}
    )
    
    return jsonify({'success': True, 'message': '프로필이 수정되었습니다.'})

@mypage_bp.route('/api/delete-ticket/<int:ticket_id>', methods=['DELETE'])
def delete_ticket(ticket_id):
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401
    
    # 티켓 소유자 확인
    ticket = db.tickets.find_one({'_id': ticket_id})
    if not ticket:
        return jsonify({'success': False, 'message': '티켓을 찾을 수 없습니다.'}), 404
    
    if ticket['seller'] != user['nickname']:
        return jsonify({'success': False, 'message': '권한이 없습니다.'}), 403
    
    # 삭제
    db.tickets.delete_one({'_id': ticket_id})
    
    return jsonify({'success': True, 'message': '삭제되었습니다.'})

@mypage_bp.route('/api/delete-polaroid/<int:polaroid_id>', methods=['DELETE'])
def delete_polaroid(polaroid_id):
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401
    
    # 폴라로이드 소유자 확인
    polaroid = db.polaroids.find_one({'_id': polaroid_id})
    if not polaroid:
        return jsonify({'success': False, 'message': '폴라로이드를 찾을 수 없습니다.'}), 404
    
    if polaroid['seller'] != user['nickname']:
        return jsonify({'success': False, 'message': '권한이 없습니다.'}), 403
    
    # 삭제
    db.polaroids.delete_one({'_id': polaroid_id})
    
    return jsonify({'success': True, 'message': '삭제되었습니다.'})

