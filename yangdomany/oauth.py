from dotenv import load_dotenv
load_dotenv()

from flask import Blueprint, redirect, url_for, session
from authlib.integrations.flask_client import OAuth
from pymongo import MongoClient
import os
import jwt
from datetime import datetime, timedelta

oauth_bp = Blueprint('oauth', __name__)
oauth = OAuth()

MONGODB_URI = 'mongodb+srv://psunyong2:V8Zh6sdvBfaAdUYv@yangdomany.8pjaosi.mongodb.net/'
client = MongoClient(MONGODB_URI)
db = client['yangdomany']
users = db['users']

SECRET_KEY = os.environ.get('SECRET_KEY', 'e13e5b2d2b72d126c883fad60d88ded4c1bea0159f1a324197eb4eb439f85809')

# 환경변수 먼저 로드
google_client_id = os.environ.get('GOOGLE_CLIENT_ID')
google_client_secret = os.environ.get('GOOGLE_CLIENT_SECRET')
kakao_client_id = os.environ.get('KAKAO_CLIENT_ID')
kakao_client_secret = os.environ.get('KAKAO_CLIENT_SECRET')
naver_client_id = os.environ.get('NAVER_CLIENT_ID')
naver_client_secret = os.environ.get('NAVER_CLIENT_SECRET')

print(f"=== Kakao Credentials ===")
print(f"Client ID: {kakao_client_id}")
print(f"Client Secret: {kakao_client_secret[:10] if kakao_client_secret else None}...")
print(f"========================")

# Google OAuth
oauth.register(
    name='google',
    client_id=google_client_id,
    client_secret=google_client_secret,
    access_token_url='https://oauth2.googleapis.com/token',
    access_token_params=None,
    authorize_url='https://accounts.google.com/o/oauth2/v2/auth',
    authorize_params=None,
    api_base_url='https://www.googleapis.com/',
    userinfo_endpoint='https://openidconnect.googleapis.com/v1/userinfo',
    jwks_uri='https://www.googleapis.com/oauth2/v3/certs',
    client_kwargs={'scope': 'openid email profile'}
)

# Kakao OAuth - token_endpoint_auth_method 추가
oauth.register(
    name='kakao',
    client_id=kakao_client_id,
    client_secret=kakao_client_secret,
    access_token_url='https://kauth.kakao.com/oauth/token',
    authorize_url='https://kauth.kakao.com/oauth/authorize',
    api_base_url='https://kapi.kakao.com',
    client_kwargs={
        'scope': 'profile_nickname',
        'token_endpoint_auth_method': 'client_secret_post'  # 이 줄 추가
    }
)

oauth.register(
    name='naver',
    client_id=naver_client_id,
    client_secret=naver_client_secret,
    access_token_url='https://nid.naver.com/oauth2.0/token',
    authorize_url='https://nid.naver.com/oauth2.0/authorize',
    api_base_url='https://openapi.naver.com/',
    client_kwargs={'scope': 'name email'}
)


def find_or_create_user(provider, provider_id, email, nickname):
    user = users.find_one({'provider': provider, 'provider_id': provider_id})
    
    if not user:
        # 닉네임 중복 체크 및 자동 변경
        original_nickname = nickname
        counter = 1
        while users.find_one({'nickname': nickname}):
            nickname = f"{original_nickname}_{counter}"
            counter += 1
        
        user_data = {
            'provider': provider,
            'provider_id': provider_id,
            'email': email,
            'nickname': nickname,
            'phone': '',
            'rating': 5.0,
            'created_at': datetime.now()
        }
        result = users.insert_one(user_data)
        user_data['_id'] = result.inserted_id
        return user_data
    
    return user

def create_jwt_token(user):
    jwt_token = jwt.encode({
        'user_id': str(user['_id']),
        'email': user['email'],
        'nickname': user['nickname'],
        'exp': datetime.utcnow() + timedelta(hours=24)
    }, SECRET_KEY, algorithm='HS256')
    
    if isinstance(jwt_token, bytes):
        jwt_token = jwt_token.decode('utf-8')
    
    return jwt_token

@oauth_bp.route('/auth/google')
def google_login():
    redirect_uri = url_for('oauth.google_callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@oauth_bp.route('/auth/google/callback')
def google_callback():
    try:
        token = oauth.google.authorize_access_token()
        userinfo = token.get('userinfo')
        
        if not userinfo:
            return 'Login failed', 400
        
        provider_id = userinfo['sub']
        email = userinfo['email']
        nickname = userinfo.get('name', email.split('@')[0])
        
        user = find_or_create_user('google', provider_id, email, nickname)
        jwt_token = create_jwt_token(user)
        
        session.clear()
        session['token'] = jwt_token
        session.permanent = True
        
        return redirect(url_for('main'))
        
    except Exception as e:
        print(f"OAuth Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return f'Error: {str(e)}', 400

@oauth_bp.route('/auth/kakao')
def kakao_login():
    redirect_uri = url_for('oauth.kakao_callback', _external=True)
    return oauth.kakao.authorize_redirect(redirect_uri)

@oauth_bp.route('/auth/kakao/callback')
def kakao_callback():
    try:
        token = oauth.kakao.authorize_access_token()
        
        resp = oauth.kakao.get('v2/user/me', token=token)
        userinfo = resp.json()
        
        provider_id = str(userinfo['id'])
        kakao_account = userinfo.get('kakao_account', {})
        
        email = kakao_account.get('email', f'kakao_{provider_id}@kakao.local')
        nickname = kakao_account.get('profile', {}).get('nickname', f'카카오사용자_{provider_id[:8]}')
        
        user = find_or_create_user('kakao', provider_id, email, nickname)
        jwt_token = create_jwt_token(user)
        
        session.clear()
        session['token'] = jwt_token
        session.permanent = True
        
        return redirect(url_for('main'))
        
    except Exception as e:
        print(f"Kakao OAuth Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return f'Error: {str(e)}', 400
    
@oauth_bp.route('/auth/naver')
def naver_login():
    redirect_uri = url_for('oauth.naver_callback', _external=True)
    return oauth.naver.authorize_redirect(redirect_uri)

@oauth_bp.route('/auth/naver/callback')
def naver_callback():
    try:
        token = oauth.naver.authorize_access_token()
        
        resp = oauth.naver.get('v1/nid/me', token=token)
        userinfo = resp.json().get('response', {})
        
        provider_id = userinfo['id']
        email = userinfo.get('email', f'naver_{provider_id}@naver.local')
        nickname = userinfo.get('nickname', userinfo.get('name', f'네이버사용자_{provider_id[:8]}'))
        
        user = find_or_create_user('naver', provider_id, email, nickname)
        jwt_token = create_jwt_token(user)
        
        session.clear()
        session['token'] = jwt_token
        session.permanent = True
        
        return redirect(url_for('main'))
        
    except Exception as e:
        print(f"Naver OAuth Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return f'Error: {str(e)}', 400