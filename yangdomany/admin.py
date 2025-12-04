from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
from functools import wraps
import os

admin_bp = Blueprint('admin', __name__)

client = MongoClient('mongodb+srv://psunyong2:V8Zh6sdvBfaAdUYv@yangdomany.8pjaosi.mongodb.net/')
db = client['yangdomany']

# 관리자 이메일 목록
ADMIN_EMAILS = os.environ.get('ADMIN_EMAILS', 'psunyong2@gmail.com').split(',')

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from login import get_current_user
        user = get_current_user()
        
        # 디버깅 출력
        print(f"=== Admin Check ===")
        print(f"User: {user}")
        print(f"User Email: {user.get('email') if user else 'None'}")
        print(f"Admin Emails: {ADMIN_EMAILS}")
        print(f"Is Admin: {user.get('email') in ADMIN_EMAILS if user else False}")
        print(f"==================")
        
        if not user or user.get('email') not in ADMIN_EMAILS:
            return redirect(url_for('main'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/admin')
@admin_required
def admin_dashboard():
    return render_template('admin.html')

@admin_bp.route('/api/admin/pending-tickets')
@admin_required
def get_pending_tickets():
    tickets = list(db.tickets.find({'status': 'pending'}).sort('created_at', -1))
    
    for ticket in tickets:
        ticket['_id'] = str(ticket['_id'])
        if 'created_at' in ticket:
            ticket['created_at'] = ticket['created_at'].strftime('%Y-%m-%d %H:%M')
    
    return jsonify({'success': True, 'tickets': tickets})

@admin_bp.route('/api/admin/all-tickets')
@admin_required
def get_all_tickets():
    tickets = list(db.tickets.find().sort('created_at', -1))
    
    for ticket in tickets:
        ticket['_id'] = str(ticket['_id'])
        if 'created_at' in ticket:
            ticket['created_at'] = ticket['created_at'].strftime('%Y-%m-%d %H:%M')
    
    return jsonify({'success': True, 'tickets': tickets})

@admin_bp.route('/api/admin/approve-ticket/<int:ticket_id>', methods=['POST'])
@admin_required
def approve_ticket(ticket_id):
    db.tickets.update_one(
        {'_id': ticket_id},
        {'$set': {'status': 'approved', 'approved_at': datetime.now()}}
    )
    return jsonify({'success': True, 'message': '승인되었습니다.'})

@admin_bp.route('/api/admin/reject-ticket/<int:ticket_id>', methods=['POST'])
@admin_required
def reject_ticket(ticket_id):
    data = request.json
    reason = data.get('reason', '')
    
    db.tickets.update_one(
        {'_id': ticket_id},
        {'$set': {'status': 'rejected', 'reject_reason': reason, 'rejected_at': datetime.now()}}
    )
    return jsonify({'success': True, 'message': '거부되었습니다.'})

@admin_bp.route('/api/admin/delete-ticket/<int:ticket_id>', methods=['DELETE'])
@admin_required
def admin_delete_ticket(ticket_id):
    db.tickets.delete_one({'_id': ticket_id})
    return jsonify({'success': True, 'message': '삭제되었습니다.'})

@admin_bp.route('/api/admin/users')
@admin_required
def get_users():
    users = list(db.users.find().sort('created_at', -1))
    
    for user in users:
        user['_id'] = str(user['_id'])
        if 'created_at' in user:
            user['created_at'] = user['created_at'].strftime('%Y-%m-%d')
        # password 제거
        if 'password' in user:
            del user['password']
    
    return jsonify({'success': True, 'users': users})

@admin_bp.route('/api/admin/ban-user/<user_id>', methods=['POST'])
@admin_required
def ban_user(user_id):
    data = request.json
    reason = data.get('reason', '')
    
    db.users.update_one(
        {'_id': ObjectId(user_id)},
        {'$set': {'banned': True, 'ban_reason': reason, 'banned_at': datetime.now()}}
    )
    return jsonify({'success': True, 'message': '사용자가 정지되었습니다.'})

@admin_bp.route('/api/admin/unban-user/<user_id>', methods=['POST'])
@admin_required
def unban_user(user_id):
    db.users.update_one(
        {'_id': ObjectId(user_id)},
        {'$set': {'banned': False}, '$unset': {'ban_reason': '', 'banned_at': ''}}
    )
    return jsonify({'success': True, 'message': '정지가 해제되었습니다.'})

@admin_bp.route('/api/admin/stats')
@admin_required
def get_stats():
    total_users = db.users.count_documents({})
    total_tickets = db.tickets.count_documents({})
    pending_tickets = db.tickets.count_documents({'status': 'pending'})
    approved_tickets = db.tickets.count_documents({'status': 'approved'})
    
    return jsonify({
        'success': True,
        'stats': {
            'total_users': total_users,
            'total_tickets': total_tickets,
            'pending_tickets': pending_tickets,
            'approved_tickets': approved_tickets
        }
    })