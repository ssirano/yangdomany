import os
import requests
from datetime import datetime, timedelta
from pymongo import MongoClient
from dotenv import load_dotenv
import xml.etree.ElementTree as ET
import time

load_dotenv()

KOPIS_API_KEY = os.environ.get('KOPIS_API_KEY')
MONGODB_URI = os.environ.get('MONGODB_URI')

client = MongoClient(MONGODB_URI)
db = client.yangdomany

def sync_kopis_shows():
    """KOPIS에서 공연 정보 가져와서 DB 업데이트"""
    
    # 현재 날짜 기준 공연 조회 (오늘부터 +90일)
    today = datetime.now().strftime('%Y%m%d')
    end_date = (datetime.now() + timedelta(days=90)).strftime('%Y%m%d')
    
    print(f"=== KOPIS 동기화 시작 ===")
    print(f"기간: {today} ~ {end_date}")
    
    # 연극 조회 (모든 페이지)
    plays = fetch_all_kopis_data('연극', today, end_date)
    print(f"✅ 연극 {len(plays)}개 조회 완료")
    
    # 뮤지컬 조회 (모든 페이지)
    musicals = fetch_all_kopis_data('뮤지컬', today, end_date)
    print(f"✅ 뮤지컬 {len(musicals)}개 조회 완료")
    
    # DB 업데이트
    all_shows = plays + musicals
    update_database(all_shows)
    
    print(f"=== 총 {len(all_shows)}개 공연 동기화 완료 ===")

def fetch_all_kopis_data(genre, start_date, end_date):
    """모든 페이지의 공연 데이터 가져오기"""
    all_shows = []
    page = 1
    rows_per_page = 100  # 최대값
    
    while True:
        print(f"  📄 {genre} {page}페이지 조회 중...")
        shows = fetch_kopis_data(genre, start_date, end_date, page, rows_per_page)
        
        if not shows:
            break
        
        all_shows.extend(shows)
        
        # 100개 미만이면 마지막 페이지
        if len(shows) < rows_per_page:
            break
        
        page += 1
        time.sleep(0.5)  # API 과부하 방지
    
    return all_shows

def fetch_kopis_data(genre, start_date, end_date, page=1, rows=100):
    """KOPIS API 호출 (페이지별)"""
    url = "http://www.kopis.or.kr/openApi/restful/pblprfr"
    
    # 장르 코드: 연극(AAAA), 뮤지컬(GGGA)
    shcate = 'AAAA' if genre == '연극' else 'GGGA'
    
    params = {
        'service': KOPIS_API_KEY,
        'stdate': start_date,
        'eddate': end_date,
        'shcate': shcate,
        'cpage': page,
        'rows': rows,
        'newsql': 'Y'  # 최신 공연 우선
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        root = ET.fromstring(response.content)
        
        # 에러 체크
        if root.find('.//msgBody') is not None:
            error_msg = root.find('.//msgBody').text
            print(f"  ⚠️  API 에러: {error_msg}")
            return []
        
        shows = []
        for item in root.findall('.//db'):
            try:
                mt20id = item.find('mt20id')
                prfnm = item.find('prfnm')
                poster = item.find('poster')
                fcltynm = item.find('fcltynm')
                prfpdfrom = item.find('prfpdfrom')
                prfpdto = item.find('prfpdto')
                prfstate = item.find('prfstate')
                
                # 필수 필드 체크
                if None in [mt20id, prfnm, poster, fcltynm, prfpdfrom, prfpdto]:
                    continue
                
                show = {
                    'kopis_id': mt20id.text,
                    'title': prfnm.text,
                    'category': genre,
                    'poster': poster.text,
                    'venue': fcltynm.text,
                    'start_date': prfpdfrom.text,
                    'end_date': prfpdto.text,
                    'status': prfstate.text if prfstate is not None else '공연중',
                    'synced_at': datetime.now()
                }
                shows.append(show)
                
            except Exception as e:
                print(f"  ⚠️  개별 공연 파싱 오류: {e}")
                continue
        
        return shows
        
    except requests.exceptions.Timeout:
        print(f"  ❌ API 타임아웃")
        return []
    except requests.exceptions.RequestException as e:
        print(f"  ❌ API 요청 오류: {e}")
        return []
    except ET.ParseError as e:
        print(f"  ❌ XML 파싱 오류: {e}")
        return []
    except Exception as e:
        print(f"  ❌ 예상치 못한 오류: {e}")
        return []

def fetch_show_detail(kopis_id):
    """개별 공연 상세 정보 (배우 정보)"""
    url = f"http://www.kopis.or.kr/openApi/restful/pblprfr/{kopis_id}"
    
    params = {
        'service': KOPIS_API_KEY
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        root = ET.fromstring(response.content)
        
        # 출연진 파싱
        prfcast = root.find('.//prfcast')
        if prfcast is not None and prfcast.text:
            actors_text = prfcast.text
            # "배우1, 배우2, 배우3" 형식
            actors = [a.strip() for a in actors_text.split(',') if a.strip()]
            return actors[:10]  # 최대 10명
        
        return []
        
    except Exception as e:
        print(f"  ⚠️  상세 정보 오류 ({kopis_id}): {e}")
        return []

def update_database(shows):
    """MongoDB 업데이트"""
    
    updated_count = 0
    new_count = 0
    
    for i, show in enumerate(shows, 1):
        # 진행률 표시
        if i % 50 == 0:
            print(f"  💾 DB 업데이트 중... {i}/{len(shows)}")
        
        #배우 정보 추가 조회 (너무 많으면 시간 오래 걸림)
        
        show['actors'] = fetch_show_detail(show['kopis_id'])
        time.sleep(0.3)
        
        # upsert: 있으면 업데이트, 없으면 삽입
        result = db.shows.update_one(
            {'kopis_id': show['kopis_id']},
            {'$set': show},
            upsert=True
        )
        
        if result.upserted_id:
            new_count += 1
        elif result.modified_count > 0:
            updated_count += 1
    
    print(f"  ✨ 신규: {new_count}개, 업데이트: {updated_count}개")
    
    # 종료된 공연 처리
    today = datetime.now().strftime('%Y%m%d')
    ended_result = db.shows.update_many(
        {'end_date': {'$lt': today}, 'status': {'$ne': '공연완료'}},
        {'$set': {'status': '공연완료'}}
    )
    
    if ended_result.modified_count > 0:
        print(f"  🏁 종료 처리: {ended_result.modified_count}개")

if __name__ == '__main__':
    sync_kopis_shows()