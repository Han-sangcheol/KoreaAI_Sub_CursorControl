"""
Cursor 자동 입력 테스트 스크립트
- status.json과 roll.txt 파일 모니터링 방식 테스트용 스크립트
- 테스트 파일들을 순차적으로 수정하여 자동 입력 테스트
"""

import time
import os
import json


def test_file_monitor():
    """
    파일 모니터링 기능 테스트
    """
    # 테스트 파일 경로
    status_file = "status.json"
    roll_file = "roll.txt"
    
    print("=" * 50)
    print("Cursor 파일 모니터링 테스트")
    print("=" * 50)
    print(f"\n테스트 파일:")
    print(f"  - {status_file}")
    print(f"  - {roll_file}")
    print("\n별도의 터미널에서 다음 명령어를 먼저 실행하세요:")
    print(f"\n  python cursor_auto_input.py\n")
    print("그런 다음 아무 키나 눌러 테스트를 진행하세요...")
    input()
    
    # 테스트 케이스들
    test_cases = [
        {
            "name": "첫 번째 테스트",
            "status": {"status": "시작", "progress": 0},
            "roll": "프로젝트 구조를 보여주세요."
        },
        {
            "name": "두 번째 테스트",
            "status": {"status": "진행중", "progress": 30},
            "roll": "코드 리뷰를 진행해주세요."
        },
        {
            "name": "세 번째 테스트",
            "status": {"status": "거의 완료", "progress": 80},
            "roll": "테스트 케이스를 작성해주세요."
        },
        {
            "name": "마지막 테스트",
            "status": {"status": "완료", "progress": 100},
            "roll": "배포 준비를 도와주세요."
        }
    ]
    
    print("\n테스트 시작!\n")
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"[{i}/{len(test_cases)}] {test_case['name']}")
        
        # status.json 파일 쓰기
        with open(status_file, 'w', encoding='utf-8') as f:
            json.dump(test_case['status'], f, ensure_ascii=False, indent=2)
        print(f"  → {status_file} 업데이트 완료")
        
        # roll.txt 파일 쓰기
        with open(roll_file, 'w', encoding='utf-8') as f:
            f.write(test_case['roll'])
        print(f"  → {roll_file} 업데이트 완료")
        
        print(f"  → 다음 테스트까지 10초 대기...\n")
        
        # 다음 테스트까지 대기
        if i < len(test_cases):
            time.sleep(10)
    
    print("\n" + "=" * 50)
    print("테스트 완료!")
    print("=" * 50)
    print(f"\n테스트 파일들을 유지하시겠습니까?")
    choice = input("삭제하려면 'y'를 입력하세요 (기본: 유지): ")
    
    # 테스트 파일 삭제 (선택)
    if choice.lower() == 'y':
        if os.path.exists(status_file):
            os.remove(status_file)
            print(f"✓ {status_file} 삭제 완료")
        
        if os.path.exists(roll_file):
            os.remove(roll_file)
            print(f"✓ {roll_file} 삭제 완료")
    else:
        print("테스트 파일을 유지합니다.")


if __name__ == "__main__":
    test_file_monitor()
