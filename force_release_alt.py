# -*- coding: utf-8 -*-
"""
강력한 Alt 키 해제 스크립트 (여러 방법 조합)
"""
import ctypes
from ctypes import windll
import time

print("="*60)
print("Alt 키 강력 해제 시작...")
print("="*60)

# 방법 1: keybd_event로 Alt Up (20회)
print("\n[방법 1] keybd_event - Alt Up (20회)")
for i in range(20):
    windll.user32.keybd_event(0x12, 0, 0x0002, 0)  # VK_MENU, KEYEVENTF_KEYUP
    time.sleep(0.01)
print("  [OK] 완료")

# 방법 2: 양쪽 Alt 키 모두 해제 (Left Alt, Right Alt)
print("\n[방법 2] 좌우 Alt 키 개별 해제")
for i in range(10):
    windll.user32.keybd_event(0xA4, 0, 0x0002, 0)  # VK_LMENU (Left Alt)
    windll.user32.keybd_event(0xA5, 0, 0x0002, 0)  # VK_RMENU (Right Alt)
    time.sleep(0.01)
print("  [OK] 완료")

# 방법 3: GetAsyncKeyState로 상태 확인 후 해제
print("\n[방법 3] 키 상태 확인 및 해제")
alt_state_before = windll.user32.GetAsyncKeyState(0x12)
print(f"  Alt 키 상태 (해제 전): {alt_state_before}")

for i in range(10):
    windll.user32.keybd_event(0x12, 0, 0x0002, 0)
    time.sleep(0.01)

time.sleep(0.1)
alt_state_after = windll.user32.GetAsyncKeyState(0x12)
print(f"  Alt 키 상태 (해제 후): {alt_state_after}")
print("  [OK] 완료")

# 방법 4: SendInput을 사용한 해제 (더 저수준)
print("\n[방법 4] SendInput으로 Alt 해제")
try:
    INPUT_KEYBOARD = 1
    KEYEVENTF_KEYUP = 0x0002
    
    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [
            ("wVk", ctypes.c_ushort),
            ("wScan", ctypes.c_ushort),
            ("dwFlags", ctypes.c_ulong),
            ("time", ctypes.c_ulong),
            ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))
        ]
    
    class INPUT(ctypes.Structure):
        _fields_ = [
            ("type", ctypes.c_ulong),
            ("ki", KEYBDINPUT)
        ]
    
    for i in range(5):
        # Alt Up 이벤트
        extra = ctypes.c_ulong(0)
        ki = KEYBDINPUT(0x12, 0, KEYEVENTF_KEYUP, 0, ctypes.pointer(extra))
        inp = INPUT(INPUT_KEYBOARD, ki)
        windll.user32.SendInput(1, ctypes.pointer(inp), ctypes.sizeof(inp))
        time.sleep(0.02)
    
    print("  [OK] 완료")
except Exception as e:
    print(f"  [SKIP] SendInput 실패: {e}")

# 최종 확인
print("\n" + "="*60)
final_state = windll.user32.GetAsyncKeyState(0x12)
print(f"최종 Alt 키 상태: {final_state}")
if final_state & 0x8000:
    print("[경고] Alt 키가 여전히 눌린 것으로 감지됩니다.")
    print("  -> 물리적으로 Alt 키를 한 번 눌렀다 떼어주세요.")
else:
    print("[완료] Alt 키가 해제되었습니다!")
print("="*60)
