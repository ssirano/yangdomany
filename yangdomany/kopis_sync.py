import os
import requests
from datetime import datetime, timedelta
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

KOPIS_API_KEY = os.environ.get('KOPIS_API_KEY')
MONGODB_URI = os.environ.get('MONGODB_URI')

client = MongoClient(MONGODB_URI)
db = client.yangdomany

def sync_kopis_shows():
    """KOPIS에서 공연 정보 가져와서 DB 업데이트"""
    
    # 현재 날짜 기준 +30일 공연 조회
    today = datetime.now().strftime('%Y%m%d')
    end_date = (datetime.now() + timedelta(days=30)).strftime('%Y%m%d')
    
    # 연극 조회
    plays = fetch_kopis_data('연극', today, end_date)
    # 뮤지컬 조회
    musicals = fetch_kopis_data('뮤지컬', today, end_date)
    
    # DB 업데이트
    update_database(plays + musicals)
    
    print(f"✅ {len(plays + musicals)}개 공연 업데이트 완료")

def fetch_kopis_data(genre, start_date, end_date):
    """KOPIS API 호출"""
    url = f"http://www.kopis.or.kr/openApi/restful/pblprfr"
    
    params = {
        'service': KOPIS_API_KEY,
        'stdate': start_date,
        'eddate': end_date,
        'shcate': 'AAAA' if genre == '연극' else 'GGGA',  # 연극: AAAA, 뮤지컬: GGGA
        'cpage': 1,
        'rows': 100
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        # XML 파싱 (KOPIS는 XML 반환)
        import xml.etree.ElementTree as ET
        root = ET.fromstring(response.content)
        
        shows = []
        for item in root.findall('.//db'):
            show = {
                'kopis_id': item.find('mt20id').text,
                'title': item.find('prfnm').text,
                'category': genre,
                'poster': item.find('poster').text,  # 이미지 URL
                'venue': item.find('fcltynm').text,
                'start_date': item.find('prfpdfrom').text,
                'end_date': item.find('prfpdto').text,
                'status': 'active',
                'synced_at': datetime.now()
            }
            shows.append(show)
        
        return shows
        
    except Exception as e:
        print(f"❌ KOPIS API 오류: {e}")
        return []

def fetch_show_detail(kopis_id):
    """개별 공연 상세 정보 (배우 정보 포함)"""
    url = f"http://www.kopis.or.kr/openApi/restful/pblprfr/{kopis_id}"
    
    params = {
        'service': KOPIS_API_KEY
    }
    
    try:
        response = requests.get(url, params=params)
        import xml.etree.ElementTree as ET
        root = ET.fromstring(response.content)
        
        # 출연진 파싱
        actors_text = root.find('.//prfcast').text if root.find('.//prfcast') is not None else ''
        actors = [a.strip() for a in actors_text.split(',') if a.strip()]
        
        return actors
        
    except Exception as e:
        print(f"❌ 상세 정보 오류: {e}")
        return []

def update_database(shows):
    """MongoDB 업데이트"""
    for show in shows:
        # 배우 정보 추가 조회
        show['actors'] = fetch_show_detail(show['kopis_id'])
        
        # upsert: 있으면 업데이트, 없으면 삽입
        db.shows.update_one(
            {'kopis_id': show['kopis_id']},
            {'$set': show},
            upsert=True
        )
    
    # 종료된 공연 처리
    today = datetime.now().strftime('%Y%m%d')
    db.shows.update_many(
        {'end_date': {'$lt': today}, 'status': 'active'},
        {'$set': {'status': 'ended'}}
    )

if __name__ == '__main__':
    sync_kopis_shows()