from flask import Blueprint, request, jsonify
from pymongo import MongoClient
from datetime import datetime
from login import get_current_user

ticket_bp = Blueprint('ticket', __name__)

# MongoDB 연결
client = MongoClient('mongodb+srv://psunyong2:V8Zh6sdvBfaAdUYv@yangdomany.8pjaosi.mongodb.net/')
db = client['yangdomany']

def mask_seat_info(seat):
    """좌석 정보를 대략적으로 마스킹"""
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

@ticket_bp.route('/api/create-ticket', methods=['POST'])
def create_ticket():
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401
    
    if user.get('banned'):
        return jsonify({
            'success': False, 
            'message': f"계정이 정지되었습니다. 사유: {user.get('ban_reason', '관리자 문의')}"
        }), 403
    
    data = request.json
    
    required_fields = ['show_id', 'show_title', 'date', 'time', 'seat', 'price']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'success': False, 'message': f'{field}는 필수 항목입니다.'}), 400
    
    max_ticket = db.tickets.find_one(sort=[('_id', -1)])
    new_id = (max_ticket['_id'] + 1) if max_ticket else 1
    
    ticket = {
        '_id': new_id,
        'show_id': int(data['show_id']),
        'show_title': data['show_title'],
        'date': data['date'],
        'time': data['time'],
        'seat': data['seat'],
        'price': int(data['price']),
        'seller': user['nickname'],
        'seller_id': user['id'],
        'status': 'pending',
        'created_at': datetime.now(),
        'contact_method': data.get('contact_method', 'chat'),
        'contact_info': data.get('contact_info', '')
    }
    
    result = db.tickets.insert_one(ticket)
    
    # ===== 통계 업데이트 추가 =====
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    db.user_stats.update_one(
        {'date': today},
        {'$inc': {'ticket_created': 1}},
        upsert=True
    )
    # ==============================
    
    return jsonify({'success': True, 'message': '티켓이 등록되었습니다.', 'ticket_id': new_id})

@ticket_bp.route('/api/update-ticket/<int:ticket_id>', methods=['PUT'])
def update_ticket(ticket_id):
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401
    
    ticket = db.tickets.find_one({'_id': ticket_id})
    if not ticket:
        return jsonify({'success': False, 'message': '티켓을 찾을 수 없습니다.'}), 404
    
    if ticket['seller'] != user['nickname']:
        return jsonify({'success': False, 'message': '권한이 없습니다.'}), 403
    
    data = request.json
    
    update_data = {
        'date': data.get('date', ticket['date']),
        'time': data.get('time', ticket['time']),
        'seat': data.get('seat', ticket['seat']),
        'price': int(data.get('price', ticket['price'])),
        'contact_method': data.get('contact_method', ticket.get('contact_method', 'chat')),
        'contact_info': data.get('contact_info', ticket.get('contact_info', ''))
    }
    
    db.tickets.update_one({'_id': ticket_id}, {'$set': update_data})
    
    return jsonify({'success': True, 'message': '티켓이 수정되었습니다.'})

@ticket_bp.route('/api/ticket-contact/<int:ticket_id>')
def get_ticket_contact(ticket_id):
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401
    
    ticket = db.tickets.find_one({'_id': ticket_id})
    if not ticket:
        return jsonify({'success': False, 'message': '티켓을 찾을 수 없습니다.'}), 404
    
    from bson import ObjectId
    seller = db.users.find_one({'nickname': ticket['seller']})
    
    contact_info = {
        'method': ticket.get('contact_method', 'chat'),
        'seller_nickname': ticket['seller'],
        'seat_original': ticket.get('seat')
    }
    
    if ticket.get('contact_method') == 'phone':
        contact_info['phone'] = seller['phone'] if seller else ''
    elif ticket.get('contact_method') == 'kakao':
        contact_info['kakao_link'] = ticket.get('contact_info', '')
    else:
        contact_info['message'] = '채팅 기능은 준비 중입니다. 판매자에게 문의해주세요.'
    
    # ===== 통계 업데이트 추가 =====
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    db.user_stats.update_one(
        {'date': today},
        {'$inc': {'ticket_contact': 1}},
        upsert=True
    )
    # ==============================
    
    return jsonify({'success': True, 'contact': contact_info})