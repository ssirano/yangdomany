from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import jwt
import os
from functools import wraps

auth_bp = Blueprint('auth', __name__)

# MongoDB 연결
client = MongoClient('mongodb+srv://psunyong2:V8Zh6sdvBfaAdUYv@yangdomany.8pjaosi.mongodb.net/')
db = client['yangdomany']

# JWT 설정
SECRET_KEY = os.environ.get('SECRET_KEY', 'e13e5b2d2b72d126c883fad60d88ded4c1bea0159f1a324197eb4eb439f85809')
JWT_EXPIRATION_HOURS = 24

# 로그인 필수 데코레이터
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = session.get('token')
        if not token:
            return redirect(url_for('auth.login_page'))
        
        try:
            jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        except:
            session.pop('token', None)
            return redirect(url_for('auth.login_page'))
        
        return f(*args, **kwargs)
    return decorated_function

# JWT 토큰에서 사용자 정보 가져오기
def get_current_user():
    token = session.get('token')
    if not token:
        return None
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        from bson import ObjectId
        user = db.users.find_one({'_id': ObjectId(payload['user_id'])})
        if user:
            user['id'] = str(user['_id'])
            del user['_id']
            if 'password' in user:  # password 필드가 있을 때만 삭제
                del user['password']
        return user
    except Exception as e:
        print(f"토큰 검증 오류: {e}")
        return None

@auth_bp.route('/login')
def login_page():
    # 이미 로그인된 경우 메인으로
    if session.get('token'):
        return redirect(url_for('main'))
    return render_template('login.html')

@auth_bp.route('/register')
def register_page():
    # 이미 로그인된 경우 메인으로
    if session.get('token'):
        return redirect(url_for('main'))
    return render_template('register.html')

@auth_bp.route('/api/register', methods=['POST'])
def register():
    data = request.json
    
    # 필수 필드 확인
    required_fields = ['email', 'password', 'nickname', 'phone']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'success': False, 'message': f'{field}는 필수 항목입니다.'}), 400
    
    email = data['email'].strip()
    password = data['password']
    nickname = data['nickname'].strip()
    phone = data['phone'].strip()
    
    # 이메일 중복 확인
    if db.users.find_one({'email': email}):
        return jsonify({'success': False, 'message': '이미 사용 중인 이메일입니다.'}), 400
    
    # 닉네임 중복 확인
    if db.users.find_one({'nickname': nickname}):
        return jsonify({'success': False, 'message': '이미 사용 중인 닉네임입니다.'}), 400
    
    # 비밀번호 해시
    hashed_password = generate_password_hash(password)
    
    # 사용자 생성
    user = {
        'email': email,
        'password': hashed_password,
        'nickname': nickname,
        'phone': phone,
        'created_at': datetime.now(),
        'rating': 5.0,
        'trade_count': 0
    }
    
    result = db.users.insert_one(user)
    
    # JWT 토큰 생성
    token = jwt.encode({
        'user_id': str(result.inserted_id),
        'email': email,
        'nickname': nickname,
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    }, SECRET_KEY, algorithm='HS256')
    
    # PyJWT 2.0 이상에서는 자동으로 문자열 반환, 이전 버전 호환성
    if isinstance(token, bytes):
        token = token.decode('utf-8')
    
    # 세션에 토큰 저장
    session['token'] = token
    session.permanent = True
    
    return jsonify({
        'success': True,
        'message': '회원가입이 완료되었습니다.',
        'token': token,
        'user': {
            'email': email,
            'nickname': nickname
        }
    })

@auth_bp.route('/api/login', methods=['POST'])
def login():
    data = request.json
    
    email = data.get('email', '').strip()
    password = data.get('password', '')
    
    if not email or not password:
        return jsonify({'success': False, 'message': '이메일과 비밀번호를 입력해주세요.'}), 400
    
    # 사용자 찾기
    user = db.users.find_one({'email': email})
    
    if not user:
        return jsonify({'success': False, 'message': '존재하지 않는 이메일입니다.'}), 401
    
    # 비밀번호 확인
    if not check_password_hash(user['password'], password):
        return jsonify({'success': False, 'message': '비밀번호가 일치하지 않습니다.'}), 401
    
    # JWT 토큰 생성
    token = jwt.encode({
        'user_id': str(user['_id']),
        'email': user['email'],
        'nickname': user['nickname'],
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    }, SECRET_KEY, algorithm='HS256')
    
    # PyJWT 2.0 이상에서는 자동으로 문자열 반환, 이전 버전 호환성
    if isinstance(token, bytes):
        token = token.decode('utf-8')
    
    # 세션에 토큰 저장
    session['token'] = token
    session.permanent = True
    
    return jsonify({
        'success': True,
        'message': '로그인 성공',
        'token': token,
        'user': {
            'email': user['email'],
            'nickname': user['nickname']
        }
    })

@auth_bp.route('/api/logout', methods=['POST'])
def logout():
    session.pop('token', None)
    return jsonify({'success': True, 'message': '로그아웃 되었습니다.'})

@auth_bp.route('/api/me')
def get_me():
    user = get_current_user()
    if user:
        return jsonify({'success': True, 'user': user})
    return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401

@auth_bp.route('/api/check-email')
def check_email():
    email = request.args.get('email', '').strip()
    if not email:
        return jsonify({'available': False})
    
    exists = db.users.find_one({'email': email}) is not None
    return jsonify({'available': not exists})

@auth_bp.route('/api/check-nickname')
def check_nickname():
    nickname = request.args.get('nickname', '').strip()
    if not nickname:
        return jsonify({'available': False})
    
    exists = db.users.find_one({'nickname': nickname}) is not None

    return jsonify({'available': not exists})

@auth_bp.route('/api/is-admin')
def is_admin():
    user = get_current_user()
    if not user:
        return jsonify({'is_admin': False})
    
    from admin import ADMIN_EMAILS
    is_admin_user = user.get('email') in ADMIN_EMAILS
    
    return jsonify({'is_admin': is_admin_user})