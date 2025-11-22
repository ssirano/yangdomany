from pymongo import MongoClient
from datetime import datetime

# MongoDB 연결
client = MongoClient('mongodb://localhost:27017/')
db = client['yangdomany']

# 기존 데이터 삭제 (초기화)
print("기존 데이터 삭제 중...")
db.shows.delete_many({})
db.show_casts.delete_many({})
db.actors.delete_many({})
db.tickets.delete_many({})
db.polaroids.delete_many({})
print("삭제 완료")

# Shows 데이터
shows = [
    {"_id": 1, "title": "웰컴투동막골", "category": "연극", "venue": "충무아트센터", "poster": "/static/images/posters/웰컴투동막골.jpg", "popularity": 95, "actors": ["박정복", "정원조", "고영빈", "이혜미"]},
    {"_id": 2, "title": "광염소나타", "category": "연극", "venue": "예술의전당", "poster": "/static/images/posters/광염소나타.jpg", "popularity": 88, "actors": ["곽동연", "이재균", "정휘"]},
    {"_id": 3, "title": "레미제라블", "category": "뮤지컬", "venue": "블루스퀘어", "poster": "/static/images/posters/레미제라블.jpg", "popularity": 92, "actors": ["민우혁", "카이", "린아"]},
    {"_id": 4, "title": "시카고", "category": "뮤지컬", "venue": "샤롯데씨어터", "poster": "/static/images/posters/시카고.jpg", "popularity": 85, "actors": ["아이비", "최정원", "신영숙"]},
    {"_id": 5, "title": "햄릿", "category": "연극", "venue": "LG아트센터", "poster": "/static/images/posters/햄릿.jpg", "popularity": 78, "actors": ["김현진", "이광수"]},
    {"_id": 6, "title": "맘마미아", "category": "뮤지컬", "venue": "디큐브아트센터", "poster": "/static/images/posters/맘마미아.jpg", "popularity": 80, "actors": ["박혜나", "손승연"]},
]

print("Shows 데이터 삽입 중...")
db.shows.insert_many(shows)
print(f"Shows {len(shows)}개 삽입 완료")

# Show Casts 데이터
show_casts = [
    {"show_id": 1, "actor": "박정복", "role": "표현철"},
    {"show_id": 1, "actor": "정원조", "role": "표현철"},
    {"show_id": 1, "actor": "고영빈", "role": "리수화"},
    {"show_id": 1, "actor": "이혜미", "role": "여일"},
    {"show_id": 2, "actor": "곽동연", "role": "백남준"},
    {"show_id": 2, "actor": "이재균", "role": "백남준"},
    {"show_id": 2, "actor": "정휘", "role": "선배"},
    {"show_id": 3, "actor": "민우혁", "role": "장발장"},
    {"show_id": 3, "actor": "카이", "role": "자베르"},
    {"show_id": 3, "actor": "린아", "role": "판틴"},
    {"show_id": 4, "actor": "아이비", "role": "록시"},
    {"show_id": 4, "actor": "최정원", "role": "벨마"},
    {"show_id": 5, "actor": "김현진", "role": "햄릿"},
]

print("Show Casts 데이터 삽입 중...")
db.show_casts.insert_many(show_casts)
print(f"Show Casts {len(show_casts)}개 삽입 완료")

# Actors 데이터
actors = [
    {"name": "박정복", "count": 1250, "image": "/static/images/actors/박정복.jpg"},
    {"name": "정원조", "count": 1180, "image": "/static/images/actors/정원조.jpg"},
    {"name": "고영빈", "count": 1120, "image": "/static/images/actors/고영빈.jpg"},
    {"name": "이재균", "count": 980, "image": "/static/images/actors/이재균.jpg"},
    {"name": "곽동연", "count": 890, "image": "/static/images/actors/곽동연.jpg"},
    {"name": "정휘", "count": 850, "image": "/static/images/actors/정휘.jpg"},
    {"name": "김현진", "count": 820, "image": "/static/images/actors/김현진.jpg"},
    {"name": "이혜미", "count": 780, "image": "/static/images/actors/이혜미.jpg"},
]

print("Actors 데이터 삽입 중...")
db.actors.insert_many(actors)
print(f"Actors {len(actors)}개 삽입 완료")

# Tickets 데이터
tickets = [
    {"_id": 1, "show_id": 1, "show_title": "웰컴투동막골", "date": "2024-12-15", "time": "14:00", "seat": "R석 10열 5번", "price": 70000, "seller": "user123", "status": "판매중", "created_at": datetime(2024, 11, 10)},
    {"_id": 2, "show_id": 1, "show_title": "웰컴투동막골", "date": "2024-12-20", "time": "19:00", "seat": "R석 12열 8번", "price": 65000, "seller": "user456", "status": "판매중", "created_at": datetime(2024, 11, 11)},
    {"_id": 3, "show_id": 3, "show_title": "레미제라블", "date": "2024-12-18", "time": "19:30", "seat": "VIP석 5열 3번", "price": 150000, "seller": "user789", "status": "판매중", "created_at": datetime(2024, 11, 12)},
    {"_id": 4, "show_id": 2, "show_title": "광염소나타", "date": "2024-12-22", "time": "15:00", "seat": "S석 8열 12번", "price": 60000, "seller": "user234", "status": "판매중", "created_at": datetime(2024, 11, 13)},
    {"_id": 5, "show_id": 4, "show_title": "시카고", "date": "2024-12-25", "time": "20:00", "seat": "R석 15열 6번", "price": 80000, "seller": "user567", "status": "판매중", "created_at": datetime(2024, 11, 14)},
]

print("Tickets 데이터 삽입 중...")
db.tickets.insert_many(tickets)
print(f"Tickets {len(tickets)}개 삽입 완료")

# Polaroids 데이터
polaroids = [
    {"_id": 1, "actor": "박정복", "show": "웰컴투동막골", "type": "교환", "want": "정원조", "description": "박정복 11/22 폴라로이드 정원조와 교환 원합니다", "image": "/static/images/polaroids/박정복_1.jpg", "seller": "user001", "status": "거래중", "created_at": datetime(2024, 11, 15)},
    {"_id": 2, "actor": "정원조", "show": "웰컴투동막골", "type": "양도", "want": "", "description": "정원조 11/25 폴라로이드 양도합니다 2만원", "image": "/static/images/polaroids/정원조_1.jpg", "seller": "user002", "status": "거래중", "created_at": datetime(2024, 11, 16)},
    {"_id": 3, "actor": "이재균", "show": "광염소나타", "type": "교환", "want": "곽동연", "description": "이재균 폴라로이드 곽동연이랑 교환해요", "image": "/static/images/polaroids/아재균_1.jpg", "seller": "user003", "status": "거래중", "created_at": datetime(2024, 11, 16)},
    {"_id": 4, "actor": "고영빈", "show": "웰컴투동막골", "type": "양도", "want": "", "description": "고영빈 11/26 폴라로이드 양도 3만원", "image": "/static/images/polaroids/고영빈_1.jpg", "seller": "user004", "status": "거래중", "created_at": datetime(2024, 11, 17)},
    {"_id": 5, "actor": "김현진", "show": "햄릿", "type": "교환", "want": "이혜미", "description": "김현진 폴라 이혜미와 교환합니다", "image": "/static/images/polaroids/김현진_1.jpg", "seller": "user005", "status": "거래중", "created_at": datetime(2024, 11, 17)},
    {"_id": 6, "actor": "정휘", "show": "레미제라블", "type": "양도", "want": "", "description": "정휘 폴라로이드 양도 2.5만원에 넘겨요", "image": "/static/images/polaroids/정휘_1.jpg", "seller": "user006", "status": "거래중", "created_at": datetime(2024, 11, 17)},
    {"_id": 7, "actor": "곽동연", "show": "광염소나타", "type": "교환", "want": "이재균", "description": "곽동연 폴라 이재균이랑 교환 원합니다", "image": "/static/images/polaroids/곽동연_1.jpg", "seller": "user007", "status": "거래중", "created_at": datetime(2024, 11, 18)},
    {"_id": 8, "actor": "박정복", "show": "웰컴투동막골", "type": "양도", "want": "", "description": "박정복 11/30 폴라 양도합니다", "image": "/static/images/polaroids/박정복_2.jpg", "seller": "user008", "status": "거래중", "created_at": datetime(2024, 11, 18)},
]

print("Polaroids 데이터 삽입 중...")
db.polaroids.insert_many(polaroids)
print(f"Polaroids {len(polaroids)}개 삽입 완료")

# 인덱스 생성
print("\n인덱스 생성 중...")
db.shows.create_index([("title", 1)])
db.shows.create_index([("category", 1)])
db.tickets.create_index([("show_id", 1)])
db.tickets.create_index([("status", 1)])
db.tickets.create_index([("created_at", -1)])
db.polaroids.create_index([("actor", 1)])
db.polaroids.create_index([("type", 1)])
db.polaroids.create_index([("status", 1)])
db.polaroids.create_index([("created_at", -1)])
db.actors.create_index([("name", 1)])
print("인덱스 생성 완료")

# 결과 확인
print("\n=== 데이터 삽입 결과 ===")
print(f"Shows: {db.shows.count_documents({})}개")
print(f"Show Casts: {db.show_casts.count_documents({})}개")
print(f"Actors: {db.actors.count_documents({})}개")
print(f"Tickets: {db.tickets.count_documents({})}개")
print(f"Polaroids: {db.polaroids.count_documents({})}개")

print("\n마이그레이션 완료!")
client.close()