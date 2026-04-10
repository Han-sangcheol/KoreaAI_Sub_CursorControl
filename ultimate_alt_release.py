# -*- coding: utf-8 -*-
"""
Windows 고정 키 상태 확인 및 해제
"""
import ctypes
from ctypes import windll, c_uint, c_int, Structure, byref
import time

# STICKYKEYS 구조체 정의
class STICKYKEYS(Structure):
    _fields_ = [
        ("cbSize", c_uint),
        ("dwFlags", c_uint),
    ]

# TOGGLEKEYS 구조체 정의  
class TOGGLEKEYS(Structure):
    _fields_ = [
        ("cbSize", c_uint),
        ("dwFlags", c_uint),
    ]

# FILTERKEYS 구조체 정의
class FILTERKEYS(Structure):
    _fields_ = [
        ("cbSize", c_uint),
        ("dwFlags", c_uint),
        ("iWaitMSec", c_uint),
        ("iDelayMSec", c_uint),
        ("iRepeatMSec", c_uint),
        ("iBounceMSec", c_uint),
    ]

SPI_GETSTICKYKEYS = 0x003A
SPI_SETSTICKYKEYS = 0x003B
SPI_GETFILTERKEYS = 0x0032
SPI_SETFILTERKEYS = 0x0033
SPI_GETTOGGLEKEYS = 0x0034
SPI_SETTOGGLEKEYS = 0x0035
SKF_STICKYKEYSON = 0x00000001

print("="*60)
print("Windows 접근성 기능 상태 확인")
print("="*60)

# 고정 키 확인
sticky = STICKYKEYS()
sticky.cbSize = ctypes.sizeof(STICKYKEYS)
windll.user32.SystemParametersInfoW(SPI_GETSTICKYKEYS, sticky.cbSize, byref(sticky), 0)

print(f"\n[고정 키 상태]")
print(f"  플래그: {sticky.dwFlags}")
if sticky.dwFlags & SKF_STICKYKEYSON:
    print("  [경고] 고정 키가 활성화되어 있습니다!")
    print("  -> 해제 시도 중...")
    
    # 고정 키 해제
    sticky.dwFlags &= ~SKF_STICKYKEYSON
    result = windll.user32.SystemParametersInfoW(SPI_SETSTICKYKEYS, sticky.cbSize, byref(sticky), 0)
    if result:
        print("  [OK] 고정 키 해제 완료")
    else:
        print("  [FAIL] 고정 키 해제 실패")
else:
    print("  [OK] 고정 키가 비활성화 상태입니다")

# 필터 키 확인
filter_keys = FILTERKEYS()
filter_keys.cbSize = ctypes.sizeof(FILTERKEYS)
windll.user32.SystemParametersInfoW(SPI_GETFILTERKEYS, filter_keys.cbSize, byref(filter_keys), 0)

print(f"\n[필터 키 상태]")
print(f"  플래그: {filter_keys.dwFlags}")
if filter_keys.dwFlags & 0x00000001:  # FKF_FILTERKEYSON
    print("  [경고] 필터 키가 활성화되어 있습니다!")
else:
    print("  [OK] 필터 키가 비활성화 상태입니다")

# 토글 키 확인
toggle = TOGGLEKEYS()
toggle.cbSize = ctypes.sizeof(TOGGLEKEYS)
windll.user32.SystemParametersInfoW(SPI_GETTOGGLEKEYS, toggle.cbSize, byref(toggle), 0)

print(f"\n[토글 키 상태]")
print(f"  플래그: {toggle.dwFlags}")
if toggle.dwFlags & 0x00000001:  # TKF_TOGGLEKEYSON
    print("  [경고] 토글 키가 활성화되어 있습니다!")
else:
    print("  [OK] 토글 키가 비활성화 상태입니다")

# 키보드 상태 완전 리셋
print("\n[방법 3] 키보드 상태 완전 리셋")
keyboard_state = (ctypes.c_ubyte * 256)()
windll.user32.GetKeyboardState(ctypes.byref(keyboard_state))

# Alt 키 관련 상태 모두 0으로
keyboard_state[0x12] = 0  # VK_MENU
keyboard_state[0xA4] = 0  # VK_LMENU
keyboard_state[0xA5] = 0  # VK_RMENU

result = windll.user32.SetKeyboardState(ctypes.byref(keyboard_state))
if result:
    print("  [OK] 키보드 상태 리셋 완료")
else:
    print("  [FAIL] 키보드 상태 리셋 실패")

print("\n" + "="*60)
print("Alt 키 해제 작업 완료!")
print("만약 여전히 Alt 키가 눌려있다면:")
print("  1. 물리적으로 Alt 키를 한 번 눌렀다 떼기")
print("  2. Shift 키를 5번 연속 누르기 (고정 키 해제)")
print("  3. 컴퓨터 재부팅")
print("="*60)
