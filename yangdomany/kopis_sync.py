import os
import requests
from datetime import datetime, timedelta
from pymongo import MongoClient
from dotenv import load_dotenv
import xml.etree.ElementTree as ET
import time
import re

load_dotenv()

KOPIS_API_KEY = os.environ.get('KOPIS_API_KEY')
MONGODB_URI = os.environ.get('MONGODB_URI')

client = MongoClient(MONGODB_URI)
db = client.yangdomany

def sync_kopis_shows():
    """KOPIS에서 공연 정보 가져와서 DB 업데이트"""
    
    today = datetime.now().strftime('%Y%m%d')
    end_date = (datetime.now() + timedelta(days=90)).strftime('%Y%m%d')
    
    print(f"=== KOPIS 동기화 시작 ===")
    print(f"기간: {today} ~ {end_date}")
    
    # 전체 페이지 조회
    plays = fetch_all_pages('연극', today, end_date)
    print(f"\n✅ 연극 총 {len(plays)}개 조회 완료")
    
    musicals = fetch_all_pages('뮤지컬', today, end_date)
    print(f"✅ 뮤지컬 총 {len(musicals)}개 조회 완료")
    
    # DB 업데이트
    all_shows = plays + musicals
    update_database(all_shows)
    
    print(f"\n=== 총 {len(all_shows)}개 공연 동기화 완료 ===")

def fetch_all_pages(genre, start_date, end_date):
    """모든 페이지 가져오기"""
    all_shows = []
    page = 1
    max_pages = 10  # 최대 10페이지 (1000개)
    
    while page <= max_pages:
        print(f"\n📄 {genre} {page}페이지 조회 중...")
        shows = fetch_page(genre, start_date, end_date, page, 100)
        
        if not shows:
            print(f"  → 더 이상 데이터 없음")
            break
        
        print(f"  → {len(shows)}개 조회됨")
        all_shows.extend(shows)
        
        # 100개 미만이면 마지막 페이지
        if len(shows) < 100:
            print(f"  ✓ 마지막 페이지 (총 {len(all_shows)}개)")
            break
        
        page += 1
        time.sleep(0.5)  # API 부하 방지
    
    return all_shows

def fetch_page(genre, start_date, end_date, page, rows):
    """개별 페이지 조회"""
    url = "http://www.kopis.or.kr/openApi/restful/pblprfr"
    
    shcate = 'AAAA' if genre == '연극' else 'GGGA'
    
    params = {
        'service': KOPIS_API_KEY,
        'stdate': start_date,
        'eddate': end_date,
        'shcate': shcate,
        'cpage': page,
        'rows': rows,
        'newsql': 'Y'
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code != 200:
            print(f"  ❌ API 오류: {response.status_code}")
            return []
        
        root = ET.fromstring(response.content)
        
        shows = []
        for item in root.findall('.//db'):
            try:
                mt20id = item.find('mt20id')
                prfnm = item.find('prfnm')
                
                if mt20id is None or prfnm is None:
                    continue
                
                show = {
                    'kopis_id': mt20id.text,
                    'title': prfnm.text,
                    'category': genre,
                    'poster': item.find('poster').text if item.find('poster') is not None else '',
                    'venue': item.find('fcltynm').text if item.find('fcltynm') is not None else '',
                    'start_date': item.find('prfpdfrom').text.replace('.', '') if item.find('prfpdfrom') is not None else '',
                    'end_date': item.find('prfpdto').text.replace('.', '') if item.find('prfpdto') is not None else '',
                    'status': item.find('prfstate').text if item.find('prfstate') is not None else '공연중',
                    'synced_at': datetime.now()
                }
                
                shows.append(show)
                
            except Exception as e:
                continue
        
        return shows
        
    except Exception as e:
        print(f"  ❌ 오류: {e}")
        return []

def parse_price_info(price_text):
    """가격 정보 파싱"""
    if not price_text:
        return {}
    
    prices = {}
    pattern = r'([A-Z가-힣]+석)\s*([\d,]+)원'
    matches = re.findall(pattern, price_text)
    
    for seat_type, price_str in matches:
        price = int(price_str.replace(',', ''))
        prices[seat_type] = price
    
    return prices

def fetch_show_detail(kopis_id):
    """상세 정보 조회 (가격)"""
    url = f"http://www.kopis.or.kr/openApi/restful/pblprfr/{kopis_id}"
    
    params = {'service': KOPIS_API_KEY}
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        root = ET.fromstring(response.content)
        
        result = {'prices': {}}
        
        # 가격 정보
        pcseguidance = root.find('.//pcseguidance')
        if pcseguidance is not None and pcseguidance.text:
            result['prices'] = parse_price_info(pcseguidance.text)
        
        return result
        
    except Exception as e:
        return {'prices': {}}

def update_database(shows):
    """MongoDB 업데이트 (안전 버전)"""
    
    new_count = 0
    updated_count = 0
    price_count = 0
    
    print(f"\n💾 DB 업데이트 중...")
    
    # 현재 최대 ID 찾기 (안전하게)
    try:
        max_id_doc = db.shows.find_one(
            {'id': {'$type': 'number'}},
            sort=[('id', -1)]
        )
        next_id = int(max_id_doc['id']) + 1 if max_id_doc else 1
    except:
        next_id = db.shows.count_documents({}) + 1
    
    for i, show in enumerate(shows, 1):
        if i % 100 == 0:
            print(f"  {i}/{len(shows)}...")
        
        # 기존 공연 확인
        existing = db.shows.find_one({'kopis_id': show['kopis_id']})
        
        if existing:
            # 기존 ID 보존 (있으면)
            if 'id' in existing:
                try:
                    show['id'] = int(existing['id'])
                except:
                    show['id'] = next_id
                    next_id += 1
            else:
                show['id'] = next_id
                next_id += 1
            
            result = db.shows.update_one(
                {'kopis_id': show['kopis_id']},
                {'$set': show}
            )
            if result.modified_count > 0:
                updated_count += 1
        else:
            # 신규 공연
            show['id'] = next_id
            next_id += 1
            
            db.shows.insert_one(show)
            new_count += 1
        
        # 신규 200개만 가격 정보 수집
        if new_count > 0 and new_count <= 200:
            try:
                detail = fetch_show_detail(show['kopis_id'])
                
                if detail['prices']:
                    db.shows.update_one(
                        {'kopis_id': show['kopis_id']},
                        {'$set': {'prices': detail['prices']}}
                    )
                    price_count += 1
                
                time.sleep(0.3)
            except Exception as e:
                print(f"  ⚠️ 가격 정보 오류: {e}")
    
    print(f"\n✨ 공연 - 신규: {new_count}개, 업데이트: {updated_count}개")
    print(f"💰 가격 정보: {price_count}개")
    
    # 종료된 공연 처리
    today = datetime.now().strftime('%Y%m%d')
    ended_result = db.shows.update_many(
        {'end_date': {'$lt': today}, 'status': {'$ne': '공연완료'}},
        {'$set': {'status': '공연완료'}}
    )
    
    if ended_result.modified_count > 0:
        print(f"🏁 종료 처리: {ended_result.modified_count}개")

if __name__ == '__main__':
    sync_kopis_shows()