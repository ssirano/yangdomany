import os
import requests
from datetime import datetime, timedelta
from pymongo import MongoClient
from dotenv import load_dotenv
import xml.etree.ElementTree as ET

load_dotenv()

KOPIS_API_KEY = os.environ.get('KOPIS_API_KEY')
MONGODB_URI = os.environ.get('MONGODB_URI')

client = MongoClient(MONGODB_URI)
db = client.yangdomany

def fetch_boxoffice():
    """KOPIS 박스오피스 데이터 가져오기"""
    
    # 현재 월의 1일 ~ 오늘
    today = datetime.now()
    
    stdate = today.replace(day=1).strftime('%Y%m%d')
    eddate = today.strftime('%Y%m%d')
    
    print(f"=== KOPIS 박스오피스 조회 ===")
    print(f"기간: {stdate} ~ {eddate}")
    print(f"(이달의 박스오피스 - 매일 업데이트)\n")
    
    # 연극 박스오피스
    print("📊 연극 박스오피스 조회 중...")
    play_ranking = fetch_boxoffice_by_category('AAAA', stdate, eddate)
    
    # 뮤지컬 박스오피스
    print("📊 뮤지컬 박스오피스 조회 중...")
    musical_ranking = fetch_boxoffice_by_category('GGGA', stdate, eddate)
    
    # DB 업데이트
    update_rankings(play_ranking + musical_ranking)
    
    print(f"\n✅ 박스오피스 동기화 완료")

def fetch_boxoffice_by_category(catecode, stdate, eddate):
    """카테고리별 박스오피스 조회"""
    
    url = "http://www.kopis.or.kr/openApi/restful/boxoffice"
    
    params = {
        'service': KOPIS_API_KEY,
        'stdate': stdate,
        'eddate': eddate,
        'catecode': catecode,
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code != 200:
            print(f"  ❌ HTTP 오류: {response.status_code}")
            return []
        
        root = ET.fromstring(response.content)
        
        # 에러 체크
        errmsg = root.find('.//errmsg')
        if errmsg is not None:
            returncode = root.find('.//returncode')
            print(f"  ❌ API 오류 ({returncode.text if returncode else ''}): {errmsg.text}")
            return []
        
        rankings = []
        
        for item in root.findall('.//boxof'):
            try:
                rnum = item.find('rnum')
                prfnm = item.find('prfnm')
                prfpd = item.find('prfpd')
                prfplcnm = item.find('prfplcnm')
                mt20id = item.find('mt20id')
                area = item.find('area')
                poster = item.find('poster')
                seatcnt = item.find('seatcnt')
                prfdtcnt = item.find('prfdtcnt')  # 공연횟수
                
                if rnum is None or prfnm is None:
                    continue
                
                ranking_data = {
                    'rank': int(rnum.text),
                    'title': prfnm.text,
                    'kopis_id': mt20id.text if mt20id is not None else None,
                    'category': '연극' if catecode == 'AAAA' else '뮤지컬',
                    'venue': prfplcnm.text if prfplcnm is not None else '',
                    'area': area.text if area is not None else '',
                    'period': prfpd.text if prfpd is not None else '',
                    'poster': poster.text if poster is not None else '',
                    'seats': int(seatcnt.text) if seatcnt is not None else 0,
                    'shows_count': int(prfdtcnt.text) if prfdtcnt is not None else 0,
                    'synced_at': datetime.now()
                }
                
                rankings.append(ranking_data)
                
                print(f"  {ranking_data['rank']}위: {ranking_data['title']}")
                
            except Exception as e:
                continue
        
        return rankings
        
    except Exception as e:
        print(f"  ❌ API 호출 오류: {e}")
        return []

def update_rankings(rankings):
    """박스오피스 순위로 인기도 점수 업데이트"""
    
    print(f"\n💾 인기도 점수 업데이트 중...")
    
    updated_count = 0
    created_count = 0
    
    for ranking_data in rankings:
        kopis_id = ranking_data.get('kopis_id')
        rank = ranking_data['rank']
        
        if not kopis_id:
            continue
        
        # 순위 점수: 1위 100점 → 10위 55점 → 50위 5점
        rank_score = max(105 - (rank * 5), 5)
        
        # shows 컬렉션에서 해당 공연 찾기
        show = db.shows.find_one({'kopis_id': kopis_id})
        
        if show:
            # 기존 공연: 점수 추가
            current_score = show.get('popularity_score', 0)
            new_score = current_score + rank_score
            
            db.shows.update_one(
                {'kopis_id': kopis_id},
                {
                    '$set': {
                        'popularity_score': new_score,
                        'boxoffice_rank': rank,
                        'boxoffice_category': ranking_data['category'],
                        'boxoffice_updated_at': datetime.now()
                    }
                }
            )
            
            updated_count += 1
            print(f"  ✓ {ranking_data['title'][:30]}: {rank}위 → +{rank_score}점")
            
        else:
            # 신규 공연: 박스오피스 정보로 생성
            max_show = db.shows.find_one({'id': {'$type': 'number'}}, sort=[('id', -1)])
            new_id = (max_show['id'] + 1) if max_show else 1
            
            db.shows.insert_one({
                'id': new_id,
                'kopis_id': kopis_id,
                'title': ranking_data['title'],
                'category': ranking_data['category'],
                'venue': ranking_data['venue'],
                'poster': ranking_data['poster'],
                'area': ranking_data['area'],
                'status': '공연중',
                'popularity_score': rank_score,
                'boxoffice_rank': rank,
                'boxoffice_category': ranking_data['category'],
                'boxoffice_updated_at': datetime.now(),
                'synced_at': datetime.now()
            })
            
            created_count += 1
            print(f"  📥 신규: {ranking_data['title'][:30]} ({rank}위)")
    
    print(f"\n✅ 업데이트: {updated_count}개, 신규: {created_count}개")

if __name__ == '__main__':
    fetch_boxoffice()