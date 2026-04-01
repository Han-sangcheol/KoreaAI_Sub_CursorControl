# -*- coding: utf-8 -*-
"""
클립보드 수정 스크립트
"""
import win32clipboard
import time

print("="*60)
print("클립보드 초기화 시작...")
print("="*60)

# 클립보드 열기 및 비우기
try:
    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    print("[OK] 클립보드 비우기 성공")
    time.sleep(0.5)
    
    # 테스트 텍스트 설정
    test_text = "테스트 복사 성공!"
    win32clipboard.SetClipboardText(test_text, win32clipboard.CF_UNICODETEXT)
    print(f"[OK] 테스트 텍스트 설정: {test_text}")
    
    win32clipboard.CloseClipboard()
    print("[OK] 클립보드 초기화 완료")
    
    # 다시 열어서 확인
    time.sleep(0.3)
    win32clipboard.OpenClipboard()
    result = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
    win32clipboard.CloseClipboard()
    
    print(f"[OK] 클립보드 읽기 성공: {result}")
    print("="*60)
    print("클립보드가 정상 작동합니다!")
    print("이제 다른 프로그램에서 Ctrl+V로 붙여넣기 해보세요.")
    print("="*60)
    
except Exception as e:
    print(f"[ERROR] 클립보드 오류: {e}")
    try:
        win32clipboard.CloseClipboard()
    except:
        pass
    print("="*60)
