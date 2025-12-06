# test_boxoffice_simple.py
import os
import requests
import xml.etree.ElementTree as ET
from dotenv import load_dotenv

load_dotenv()

KOPIS_API_KEY = os.environ.get('KOPIS_API_KEY')

# 여러 날짜 조합 시도
test_dates = [
    ('20230601', '20230630'),  # 2023년 6월 (문서 예시)
    ('20241101', '20241130'),  # 2024년 11월
    ('20251101', '20251130'),  # 2025년 11월 (현재)
]

for stdate, eddate in test_dates:
    print(f"\n{'='*60}")
    print(f"테스트: {stdate} ~ {eddate}")
    print('='*60)
    
    url = "http://www.kopis.or.kr/openApi/restful/boxoffice"
    
    params = {
        'service': KOPIS_API_KEY,
        'stdate': stdate,
        'eddate': eddate,
        'catecode': 'AAAA'
    }
    
    print(f"URL: {url}")
    print(f"파라미터: {params}\n")
    
    try:
        response = requests.get(url, params=params, timeout=10)
        
        print(f"상태 코드: {response.status_code}")
        print(f"\n응답 내용 (처음 800자):")
        print(response.text[:800])
        
        if response.status_code == 200:
            try:
                root = ET.fromstring(response.content)
                
                # 에러 확인
                returncode = root.find('.//returncode')
                errmsg = root.find('.//errmsg')
                
                if returncode is not None:
                    print(f"\nReturn Code: {returncode.text}")
                if errmsg is not None:
                    print(f"Error Message: {errmsg.text}")
                
                # 데이터 확인
                boxofs = root.findall('.//boxof')
                if boxofs:
                    print(f"\n✅ 박스오피스 데이터 {len(boxofs)}개 발견!")
                    for i, boxof in enumerate(boxofs[:3], 1):
                        rnum = boxof.find('rnum')
                        prfnm = boxof.find('prfnm')
                        if rnum is not None and prfnm is not None:
                            print(f"  {rnum.text}위: {prfnm.text}")
                else:
                    print("\n❌ 박스오피스 데이터 없음")
                    
            except ET.ParseError as e:
                print(f"\nXML 파싱 오류: {e}")
                
    except Exception as e:
        print(f"\n오류 발생: {e}")