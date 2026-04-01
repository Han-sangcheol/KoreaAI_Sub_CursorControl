# -*- coding: utf-8 -*-
"""
긴급 입력 차단 해제 스크립트
BlockInput으로 차단된 키보드/마우스 입력을 강제로 해제합니다.
"""
import ctypes
from ctypes import windll
import time

print("="*60)
print("긴급 입력 차단 해제 시작...")
print("="*60)

# 10회 연속 차단 해제 시도
success_count = 0
for i in range(10):
    try:
        result = windll.user32.BlockInput(False)
        if result:
            success_count += 1
            print(f"  [OK] 차단 해제 성공 (시도 {i + 1}/10)")
        else:
            print(f"  [FAIL] 차단 해제 실패 (시도 {i + 1}/10)")
        time.sleep(0.1)
    except Exception as e:
        print(f"  [ERROR] 예외 발생 (시도 {i + 1}/10): {e}")

print("="*60)
if success_count > 0:
    print(f"완료! ({success_count}회 성공)")
    print("이제 텍스트 복사가 가능합니다.")
else:
    print("해제 실패 - 관리자 권한으로 다시 시도하거나 재부팅이 필요할 수 있습니다.")
print("="*60)
