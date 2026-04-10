# -*- coding: utf-8 -*-
"""
긴급 Alt 키 해제 스크립트
"""
import ctypes
from ctypes import windll
import time

print("="*60)
print("Alt 키 강제 해제 시작...")
print("="*60)

# 모든 수정자 키 해제
try:
    # Alt 키 해제 (10회)
    for i in range(10):
        windll.user32.keybd_event(0x12, 0, 0x0002, 0)  # VK_MENU (Alt), KEYEVENTF_KEYUP
        time.sleep(0.05)
    print("[OK] Alt 키 해제 완료 (10회)")
    
    # Ctrl 키 해제
    for i in range(5):
        windll.user32.keybd_event(0x11, 0, 0x0002, 0)  # VK_CONTROL, KEYEVENTF_KEYUP
        time.sleep(0.05)
    print("[OK] Ctrl 키 해제 완료")
    
    # Shift 키 해제
    for i in range(5):
        windll.user32.keybd_event(0x10, 0, 0x0002, 0)  # VK_SHIFT, KEYEVENTF_KEYUP
        time.sleep(0.05)
    print("[OK] Shift 키 해제 완료")
    
    # Win 키 해제
    for i in range(5):
        windll.user32.keybd_event(0x5B, 0, 0x0002, 0)  # VK_LWIN, KEYEVENTF_KEYUP
        time.sleep(0.05)
    print("[OK] Win 키 해제 완료")
    
    print("="*60)
    print("모든 수정자 키 해제 완료!")
    print("="*60)
    
except Exception as e:
    print(f"[ERROR] {e}")
    import traceback
    traceback.print_exc()
