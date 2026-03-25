"""
Cursor 프롬프트 입력창 자동화 프로그램
- status.json과 roll.txt 파일을 모니터링
- 두 파일의 내용을 합쳐서 Cursor IDE의 프롬프트 입력창에 자동으로 입력
- Windows 메시지를 사용하여 백그라운드에서 안전하게 입력 (사용자의 작업 방해 없음)
- 입력 후 자동으로 엔터 키를 눌러 전송
- 여러 개의 Cursor 인스턴스가 실행 중일 때 사용자가 선택할 수 있도록 지원
- 사용자 입력 감지: 키보드/마우스 입력이 3초간 없을 때까지 대기 후 실행
- 2초 안전 타이머: 입력 차단이 2초 이상 지속되지 않도록 자동 해제
- Ctrl+N으로 새 프롬프트 창을 열어서 확실하게 붙여넣기
- 사용자 입력 감지 시작 시 콘솔에 3-2-1 카운트다운 표시
- 선택 개수와 일치할 때: 제목에 "prompt"가 포함된 Cursor 개수가 요청한 윈도우 개수와 같으면 자동 선택
"""

import pywinauto
from pywinauto import Application
from pywinauto.keyboard import send_keys
import time
import sys
import os
from pathlib import Path
import hashlib
import json
import win32gui
import win32con
import win32api
import win32clipboard
import win32process
import ctypes
from ctypes import windll, Structure, c_long, byref
import threading
import subprocess
import multiprocessing


# ============================================================
# 설정 (Configuration)
# ============================================================
class Config:
    """프로그램 실행 시간 관련 설정"""
    
    # 사용자 입력 감지 설정
    USER_IDLE_SECONDS = 3.0          # 사용자 입력이 없어야 하는 대기 시간 (초)
    USER_IDLE_CHECK_INTERVAL = 0.5   # 사용자 입력 감지 체크 간격 (초)
    
    # 윈도우 활성화 설정
    WINDOW_ACTIVATION_RETRY_DELAY = 0.5   # 윈도우 활성화 재시도 간격 (초)
    WINDOW_STABILIZATION_DELAY = 0.5      # 윈도우 안정화 대기 시간 (초)
    
    # 붙여넣기 작업 설정
    NEW_PROMPT_OPEN_DELAY = 0.5      # 새 프롬프트 창 열기 대기 (초)
    PASTE_COMPLETION_DELAY = 0.5     # 붙여넣기 후 대기 시간 (초)
    
    # 안전장치 설정
    INPUT_BLOCK_SAFETY_TIMEOUT = 2.0 # 입력 차단 자동 해제 시간 (초)
    OPERATION_TIMEOUT = 30.0         # 전체 작업 타임아웃 (초)
    
    # 파일 모니터링 설정
    FILE_CHECK_INTERVAL = 1.0        # 파일 변경 확인 간격 (초)

# ============================================================


class LASTINPUTINFO(Structure):
    """
    Windows API의 LASTINPUTINFO 구조체
    마지막 입력 시간 정보를 가져오기 위한 구조체
    """
    _fields_ = [
        ('cbSize', c_long),
        ('dwTime', c_long),
    ]


# 전역 변수로 입력 차단 상태 추적
input_block_active = False
safety_timer = None


def emergency_unblock_input():
    """
    긴급 입력 차단 해제 함수 (2초 후 자동 실행)
    """
    global input_block_active
    
    print("  ⚠ [안전장치] 2초 경과 - 긴급 차단 해제 시작")
    
    # 3회 연속 해제 시도
    for attempt in range(3):
        try:
            result = windll.user32.BlockInput(False)
            if result:
                print(f"  ✓ [안전장치] 차단 해제 성공 (시도 {attempt + 1}/3)")
                input_block_active = False
                return
            else:
                print(f"  ⚠ [안전장치] 차단 해제 실패 (시도 {attempt + 1}/3)")
        except Exception as e:
            print(f"  ⚠ [안전장치] 예외 발생 (시도 {attempt + 1}/3): {e}")
        
        time.sleep(0.1)  # 0.1초 대기 후 재시도
    
    # 3회 실패 후에도 상태 업데이트
    input_block_active = False
    print("  ⚠ [안전장치] 3회 시도 완료")


def block_user_input_safe(block=True):
    """
    사용자의 키보드와 마우스 입력을 안전하게 차단하거나 해제
    차단 시 2초 후 자동으로 해제되는 안전장치 포함
    
    Args:
        block: True이면 입력 차단, False이면 차단 해제
    
    Returns:
        bool: 성공 여부
    """
    global input_block_active, safety_timer
    
    try:
        if block:
            # 입력 차단 시작
            result = windll.user32.BlockInput(True)
            if result:
                print("  → 사용자 입력 차단 (붙여넣기 중)")
                input_block_active = True
                
                # 2초 후 자동 해제 타이머 시작
                safety_timer = threading.Timer(Config.INPUT_BLOCK_SAFETY_TIMEOUT, emergency_unblock_input)
                safety_timer.daemon = True
                safety_timer.start()
                print(f"  → [안전장치] {Config.INPUT_BLOCK_SAFETY_TIMEOUT}초 타이머 가동")
                
                return True
            else:
                print("  ⚠ 입력 차단 실패")
                return False
        else:
            # 입력 차단 해제
            # 안전 타이머 취소
            if safety_timer and safety_timer.is_alive():
                safety_timer.cancel()
                print("  → [안전장치] 타이머 취소")
            
            # 3회 연속 해제 시도
            for attempt in range(3):
                result = windll.user32.BlockInput(False)
                if result:
                    print(f"  → 사용자 입력 차단 해제 (시도 {attempt + 1}/3)")
                    input_block_active = False
                    return True
                else:
                    print(f"  ⚠ 차단 해제 실패 (시도 {attempt + 1}/3)")
                    time.sleep(0.1)
            
            # 3회 실패해도 상태 업데이트
            input_block_active = False
            return False
            
    except Exception as e:
        print(f"  ⚠ 입력 차단/해제 오류: {e}")
        input_block_active = False
        return False


def block_user_input(block=True):
    """
    사용자의 키보드와 마우스 입력을 차단하거나 해제 (하위 호환성 유지)
    """
    return block_user_input_safe(block)


def get_idle_duration():
    """
    사용자가 마지막으로 키보드나 마우스를 사용한 이후 경과 시간(초) 반환
    
    Returns:
        float: 유휴 시간(초)
    """
    lastInputInfo = LASTINPUTINFO()
    lastInputInfo.cbSize = ctypes.sizeof(lastInputInfo)
    windll.user32.GetLastInputInfo(byref(lastInputInfo))
    
    millis = windll.kernel32.GetTickCount() - lastInputInfo.dwTime
    return millis / 1000.0


def force_window_to_foreground(hwnd):
    """
    윈도우를 강제로 전면으로 가져오기 (여러 방법 조합)
    
    Args:
        hwnd: 윈도우 핸들
    
    Returns:
        bool: 성공 여부
    """
    try:
        # 1. 현재 전면 윈도우 확인
        current_foreground = win32gui.GetForegroundWindow()
        
        # 2. 이미 전면이면 성공
        if current_foreground == hwnd:
            return True
        
        # 3. 최소화 상태면 복원
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            time.sleep(0.2)
        
        # 4. 윈도우를 보이게 설정
        win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
        time.sleep(0.1)
        
        # 5. Alt 키를 눌러서 입력 포커스 획득 (Windows 보안 정책 우회)
        windll.user32.keybd_event(0x12, 0, 0, 0)  # Alt Down
        time.sleep(0.05)
        
        # 6. 현재 프로세스와 전면 윈도우의 스레드를 연결
        if current_foreground != 0:
            try:
                current_thread = win32api.GetCurrentThreadId()
                foreground_thread = win32process.GetWindowThreadProcessId(current_foreground)[0]
                
                if current_thread != foreground_thread:
                    # 스레드 연결
                    windll.user32.AttachThreadInput(current_thread, foreground_thread, True)
                    time.sleep(0.05)
            except:
                pass
        
        # 7. 여러 방법으로 윈도우 활성화 시도
        try:
            win32gui.SetForegroundWindow(hwnd)
        except:
            pass
        
        try:
            win32gui.BringWindowToTop(hwnd)
        except:
            pass
        
        try:
            win32gui.SetActiveWindow(hwnd)
        except:
            pass
        
        # 8. Alt 키 해제
        windll.user32.keybd_event(0x12, 0, 2, 0)  # Alt Up
        time.sleep(0.05)
        
        # 9. 스레드 분리
        if current_foreground != 0:
            try:
                current_thread = win32api.GetCurrentThreadId()
                foreground_thread = win32process.GetWindowThreadProcessId(current_foreground)[0]
                if current_thread != foreground_thread:
                    windll.user32.AttachThreadInput(current_thread, foreground_thread, False)
            except:
                pass
        
        time.sleep(0.3)
        
        # 10. 확인
        new_foreground = win32gui.GetForegroundWindow()
        success = (new_foreground == hwnd)
        
        if not success:
            # 11. 최후의 수단: 윈도우 클릭
            try:
                rect = win32gui.GetWindowRect(hwnd)
                x = rect[0] + 100
                y = rect[1] + 50
                
                # 마우스 이동 및 클릭
                windll.user32.SetCursorPos(x, y)
                time.sleep(0.1)
                windll.user32.mouse_event(2, 0, 0, 0, 0)  # Left down
                windll.user32.mouse_event(4, 0, 0, 0, 0)  # Left up
                time.sleep(0.2)
                
                new_foreground = win32gui.GetForegroundWindow()
                success = (new_foreground == hwnd)
            except:
                pass
        
        return success
        
    except Exception as e:
        print(f"  ⚠ 윈도우 활성화 오류: {e}")
        return False


def detect_cancel_gesture():
    """
    사용자의 취소 제스처를 감지 (마우스 흔들기 2회 이상 또는 더블 클릭)
    
    Returns:
        bool: 취소 제스처 감지 여부
    """
    try:
        import win32api
        
        # 마우스 위치 추적
        mouse_positions = []
        mouse_move_count = 0
        last_pos = win32api.GetCursorPos()
        check_start = time.time()
        
        # 0.5초 동안 마우스 움직임 감지
        while time.time() - check_start < 0.5:
            current_pos = win32api.GetCursorPos()
            
            # 마우스가 10픽셀 이상 움직였는지 확인
            if abs(current_pos[0] - last_pos[0]) > 10 or abs(current_pos[1] - last_pos[1]) > 10:
                mouse_move_count += 1
                last_pos = current_pos
                
                # 2회 이상 움직임 감지시 취소
                if mouse_move_count >= 2:
                    return True
            
            # 더블 클릭 감지 (왼쪽 버튼)
            left_button_state = win32api.GetAsyncKeyState(0x01)  # VK_LBUTTON
            if left_button_state & 0x8000:  # 버튼이 눌린 상태
                time.sleep(0.05)
                # 짧은 시간 후 다시 확인
                left_button_state2 = win32api.GetAsyncKeyState(0x01)
                if left_button_state2 & 0x8000:
                    return True
            
            time.sleep(0.05)
        
        return False
    except Exception as e:
        print(f"  [WARNING] 취소 제스처 감지 오류: {e}")
        return False


def wait_for_user_idle(idle_seconds=3.0, check_interval=0.5):
    """
    사용자가 키보드나 마우스를 사용하지 않는 상태가 지정된 시간만큼 지속될 때까지 대기
    이 함수 호출 시점부터 idle_seconds 동안 입력이 없어야 함
    유휴 대기 중 마우스 포인터 옆에 남은 시간을 실시간 표시 (총 5초: 입력감지 3초 + 활성화 1초 + 안정화 1초)
    마우스를 2회 이상 흔들거나 더블 클릭하면 취소됨
    
    Args:
        idle_seconds: 대기할 유휴 시간(초)
        check_interval: 확인 간격(초)
    
    Returns:
        tuple: (countdown_process, 성공 여부, 취소 여부)
    """
    print(f"\n  -> 사용자 입력 감지 시작 ({idle_seconds}초간 유휴 상태 대기)")
    print(f"     [INFO] 키보드나 마우스를 사용하면 타이머가 리셋됩니다")
    print(f"     [INFO] 마우스를 2회 이상 흔들거나 더블 클릭하면 취소됩니다")
    
    # 이 시점부터 idle_seconds 동안 입력이 없어야 함
    idle_start_time = time.time()
    last_input_detected_time = time.time()
    total_start_time = time.time()
    countdown_process = None
    last_cancel_check_time = time.time()
    
    while True:
        current_time = time.time()
        system_idle_time = get_idle_duration()
        elapsed_since_last_input = current_time - last_input_detected_time
        elapsed_total = current_time - total_start_time
        
        # 카운트다운이 표시 중일 때만 취소 제스처 감지 (0.5초마다)
        if countdown_process and countdown_process.poll() is None:
            if current_time - last_cancel_check_time >= 0.5:
                if detect_cancel_gesture():
                    print(f"\n  [CANCEL] 사용자 취소 제스처 감지! (마우스 흔들기 또는 더블 클릭)")
                    
                    # 카운트다운 프로세스 종료
                    try:
                        countdown_process.terminate()
                        countdown_process.wait(timeout=0.5)
                    except:
                        pass
                    
                    return None, False, True  # 취소됨
                last_cancel_check_time = current_time
        
        # 시스템 유휴 시간이 0.5초 미만이면 사용자가 방금 입력함
        if system_idle_time < 0.5:
            if elapsed_since_last_input > 0.5:
                print(f"\n  [WARNING] 사용자 입력 감지! 타이머 리셋 (총 대기: {elapsed_total:.1f}초)")
                
                # 카운트다운 프로세스 종료
                if countdown_process and countdown_process.poll() is None:
                    try:
                        countdown_process.terminate()
                    except:
                        pass
                    countdown_process = None
                    
            last_input_detected_time = current_time
            idle_start_time = current_time
        
        # 마지막 입력 이후 경과 시간 계산
        time_since_last_input = current_time - last_input_detected_time
        
        # 카운트다운 프로세스 시작 (0.5초 유휴 후) - 총 5초 카운트다운
        if time_since_last_input >= 0.5 and countdown_process is None:
            try:
                countdown_script = os.path.join(os.path.dirname(__file__), 'realtime_countdown.py')
                if os.path.exists(countdown_script):
                    # 전체 프로세스 시간: 입력감지(3초) + 활성화(1초) + 안정화(1초) = 5초
                    total_process_time = idle_seconds + 2.0
                    remaining = total_process_time - time_since_last_input
                    if remaining > 0:
                        countdown_process = subprocess.Popen(
                            [sys.executable, countdown_script, str(remaining)],
                            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                        )
            except Exception as e:
                print(f"  [WARNING] 카운트다운 시작 오류: {e}")
        
        # idle_seconds 이상 입력이 없으면 완료
        if time_since_last_input >= idle_seconds:
            bar_full = '█' * 20
            print(f"     [{bar_full}] 100.0% | 유휴: {idle_seconds:.1f}초 / {idle_seconds}초 (총 대기: {elapsed_total:.1f}초)    ")
            print(f"  [OK] 유휴 상태 {idle_seconds}초 확인 완료! (총 대기 시간: {elapsed_total:.1f}초)")
            
            # 카운트다운 프로세스는 계속 유지 (활성화 + 안정화 단계에서 사용)
            print(f"  -> 이제 복사 및 붙여넣기를 진행합니다...")
            return countdown_process, True, False  # 성공, 취소되지 않음
        
        # 진행 상태 표시 (블록 형태)
        progress = (time_since_last_input / idle_seconds) * 100
        bar_length = 20
        filled = int(bar_length * time_since_last_input / idle_seconds)
        bar = '█' * filled + '░' * (bar_length - filled)
        
        print(f"     [{bar}] {progress:5.1f}% | 유휴: {time_since_last_input:.1f}초 / {idle_seconds}초 (총 대기: {elapsed_total:.1f}초)    ", end='\r')
        time.sleep(check_interval)
    
    print()


def get_files_combined_hash(status_file, roll_file):
    """
    두 파일의 통합 해시값을 계산하여 반환 (파일 변경 감지용)
    """
    try:
        combined_content = ""
        
        # status.json 읽기
        if os.path.exists(status_file):
            with open(status_file, 'r', encoding='utf-8') as f:
                combined_content += f.read()
        
        # roll.txt 읽기
        if os.path.exists(roll_file):
            with open(roll_file, 'r', encoding='utf-8') as f:
                combined_content += f.read()
        
        return hashlib.md5(combined_content.encode()).hexdigest()
    except Exception as e:
        print(f"파일 해시 계산 오류: {e}")
        return None


def read_and_combine_files(status_file, roll_file):
    """
    status.json과 roll.txt 파일의 내용을 읽어서 합쳐서 반환
    """
    try:
        combined_text = ""
        
        # status.json 읽기
        if os.path.exists(status_file):
            with open(status_file, 'r', encoding='utf-8') as f:
                status_content = f.read()
                combined_text += f"=== status.json ===\n{status_content}\n\n"
        else:
            print(f"경고: {status_file} 파일을 찾을 수 없습니다.")
        
        # roll.txt 읽기
        if os.path.exists(roll_file):
            with open(roll_file, 'r', encoding='utf-8') as f:
                roll_content = f.read()
                combined_text += f"=== roll.txt ===\n{roll_content}"
        else:
            print(f"경고: {roll_file} 파일을 찾을 수 없습니다.")
        
        return combined_text if combined_text else None
    except Exception as e:
        print(f"파일 읽기 오류: {e}")
        return None


def find_all_cursor_windows():
    """
    실행 중인 모든 Cursor 애플리케이션 윈도우를 찾아서 리스트로 반환
    제한 없이 모든 Cursor 윈도우를 검색
    """
    try:
        print("Cursor 윈도우 검색 중...")
        
        # UIA 백엔드로 데스크톱 검색
        desktop = pywinauto.Desktop(backend="uia")
        
        cursor_windows = []
        seen_handles = set()
        
        # 방법 1: desktop.windows()로 모든 최상위 윈도우 검색
        try:
            windows = desktop.windows()
            for window in windows:
                try:
                    title = window.window_text()
                    handle = window.handle
                    
                    # 중복 방지 및 Cursor 윈도우만 선택
                    if handle not in seen_handles and "Cursor" in title and title.strip():
                        cursor_windows.append({
                            'window': window,
                            'title': title,
                            'handle': handle
                        })
                        seen_handles.add(handle)
                except:
                    continue
        except Exception as e:
            print(f"  검색 오류 (방법1): {e}")
        
        # 방법 2: Win32 API로 모든 윈도우 검색 (보완)
        try:
            def enum_windows_callback(hwnd, results):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if "Cursor" in title and title.strip() and hwnd not in seen_handles:
                        try:
                            # pywinauto 윈도우 객체로 변환
                            from pywinauto.application import Application
                            app = Application(backend="uia").connect(handle=hwnd)
                            window = app.window(handle=hwnd)
                            
                            results.append({
                                'window': window,
                                'title': title,
                                'handle': hwnd
                            })
                            seen_handles.add(hwnd)
                        except:
                            pass
                return True
            
            results = []
            win32gui.EnumWindows(enum_windows_callback, results)
            cursor_windows.extend(results)
        except Exception as e:
            print(f"  검색 오류 (방법2): {e}")
        
        # 중복 제거 (handle 기준)
        unique_windows = []
        unique_handles = set()
        for win_info in cursor_windows:
            if win_info['handle'] not in unique_handles:
                unique_windows.append(win_info)
                unique_handles.add(win_info['handle'])
        
        print(f"✓ {len(unique_windows)}개의 Cursor 윈도우 발견")
        return unique_windows
        
    except Exception as e:
        print(f"윈도우 찾기 오류: {e}")
        import traceback
        traceback.print_exc()
        return []


def select_cursor_window(cursor_windows):
    """
    여러 Cursor 윈도우 중 사용자가 선택할 수 있도록 메뉴 표시
    엔터만 입력하면 다시 입력 받음
    """
    if len(cursor_windows) == 0:
        print("실행 중인 Cursor 윈도우를 찾을 수 없습니다.")
        return None
    
    if len(cursor_windows) == 1:
        print(f"Cursor 윈도우 찾음: {cursor_windows[0]['title']}")
        return cursor_windows[0]['window']
    
    # 여러 개의 Cursor 윈도우가 있는 경우
    print(f"\n{len(cursor_windows)}개의 Cursor 윈도우가 실행 중입니다:")
    print("-" * 80)
    
    for idx, win_info in enumerate(cursor_windows, 1):
        print(f"{idx:2d}. {win_info['title']}")
    
    print("-" * 80)
    
    # 사용자 선택
    while True:
        try:
            choice = input(f"\n입력할 Cursor 윈도우 번호를 선택하세요 (1-{len(cursor_windows)}, Enter=재입력): ").strip()
            
            # 엔터만 입력한 경우 다시 입력 받기
            if not choice:
                print("다시 입력하세요.")
                continue
            
            choice_idx = int(choice) - 1
            
            if 0 <= choice_idx < len(cursor_windows):
                selected = cursor_windows[choice_idx]
                print(f"\n선택됨: {selected['title']}")
                return selected['window']
            else:
                print(f"⚠ 1부터 {len(cursor_windows)} 사이의 숫자를 입력하세요.")
        except ValueError:
            print("⚠ 올바른 숫자를 입력하세요.")
        except KeyboardInterrupt:
            print("\n\n취소되었습니다.")
            return None


def find_chat_input(cursor_window):
    """
    Cursor 윈도우 내에서 채팅 입력창을 찾아서 반환
    여러 방법을 시도하여 가장 적합한 입력창을 찾음
    """
    try:
        print("프롬프트 입력창 검색 중...")
        
        # 방법 1: Edit 컨트롤 중에서 여러 줄 편집 가능한 것 찾기
        edit_controls = cursor_window.descendants(control_type="Edit")
        
        suitable_controls = []
        for control in edit_controls:
            try:
                if control.is_visible() and control.is_enabled():
                    # 위치 정보 가져오기 (채팅 입력창은 보통 하단에 위치)
                    rect = control.rectangle()
                    window_rect = cursor_window.rectangle()
                    
                    # 윈도우 하단 50% 영역에 있는 컨트롤 우선
                    if rect.top > window_rect.top + (window_rect.height() * 0.5):
                        suitable_controls.append((control, rect.top))
                        print(f"  - 후보 발견: 위치 y={rect.top}")
            except:
                continue
        
        # 가장 아래쪽에 있는 컨트롤 선택
        if suitable_controls:
            suitable_controls.sort(key=lambda x: x[1], reverse=True)
            selected = suitable_controls[0][0]
            print(f"✓ 프롬프트 입력창 찾음 (Edit 컨트롤)")
            return selected
        
        # 방법 2: 모든 Edit 컨트롤 중 첫 번째 가시적인 것
        for control in edit_controls:
            try:
                if control.is_visible() and control.is_enabled():
                    print(f"✓ 프롬프트 입력창 찾음 (기본 Edit)")
                    return control
            except:
                continue
        
        # 방법 3: Document 타입 찾기 (Monaco Editor 같은 경우)
        doc_controls = cursor_window.descendants(control_type="Document")
        for control in doc_controls:
            try:
                if control.is_visible() and control.is_enabled():
                    print(f"✓ 프롬프트 입력창 찾음 (Document)")
                    return control
            except:
                continue
        
        print("✗ 프롬프트 입력창을 찾지 못했습니다.")
        return None
    except Exception as e:
        print(f"입력창 찾기 오류: {e}")
        return None


def send_text_to_cursor(text, cursor_window, countdown_process=None):
    """
    텍스트를 지정된 Cursor 프롬프트 입력창에 입력하고 엔터
    Electron 앱 특성상 윈도우 활성화 후 키보드 시뮬레이션 사용
    사용자가 키보드/마우스를 사용 중이면 3.0초간 유휴 상태가 될 때까지 대기
    
    입력 차단 후 클립보드에 복사하여 사용자가 복사한 내용이 덮어씌워지는 것을 방지
    Ctrl+N으로 새로운 프롬프트 창을 열어서 깨끗한 상태에서 붙여넣기 실행
    
    전체 실행 시간이 너무 길면 타임아웃으로 종료하여 모니터링 루프가 멈추지 않도록 함
    
    Args:
        text: 입력할 텍스트
        cursor_window: Cursor 윈도우 객체
        countdown_process: 카운트다운 프로세스 (계속 표시용)
    """
    global input_block_active, safety_timer
    
    start_time = time.time()
    timeout_seconds = Config.OPERATION_TIMEOUT
    activation_start_time = None
    
    try:
        if not text:
            print("입력할 텍스트가 비어있습니다.")
            return False
        
        print(f"입력할 텍스트: {text[:50]}...")
        
        # ★★★ 현재 상태 저장 (복원을 위해)
        print("  → 현재 상태 저장 중...")
        original_foreground_hwnd = None
        original_mouse_pos = None
        paste_start_mouse_pos = None  # 붙여넣기 시작 시점의 마우스 위치
        
        try:
            # 현재 전면 윈도우 저장
            original_foreground_hwnd = win32gui.GetForegroundWindow()
            if original_foreground_hwnd:
                try:
                    original_window_title = win32gui.GetWindowText(original_foreground_hwnd)
                    print(f"  → 원래 활성 윈도우: {original_window_title[:50]}")
                except:
                    print(f"  → 원래 활성 윈도우 핸들: {original_foreground_hwnd}")
            
            # 현재 마우스 위치 저장 (3초 대기 시작 전)
            cursor_pos = win32api.GetCursorPos()
            original_mouse_pos = (cursor_pos[0], cursor_pos[1])
            print(f"  → 원래 마우스 위치: ({original_mouse_pos[0]}, {original_mouse_pos[1]})")
        except Exception as e:
            print(f"  ⚠ 상태 저장 오류: {e}")
        
        # 타임아웃 체크
        if time.time() - start_time > timeout_seconds:
            print(f"  ⚠ 타임아웃 ({timeout_seconds}초 초과)")
            return False
        
        # 사용자 입력이 없는 상태가 지정된 시간만큼 지속될 때까지 대기
        countdown_process, idle_success, cancelled = wait_for_user_idle(idle_seconds=Config.USER_IDLE_SECONDS, check_interval=Config.USER_IDLE_CHECK_INTERVAL)
        
        # 취소된 경우
        if cancelled:
            print(f"  ⚠ 사용자가 작업을 취소했습니다.")
            return False
        
        # 타임아웃 체크
        if time.time() - start_time > timeout_seconds:
            print(f"  ⚠ 타임아웃 ({timeout_seconds}초 초과)")
            if countdown_process and countdown_process.poll() is None:
                try:
                    countdown_process.terminate()
                except:
                    pass
            return False
        
        # ★ 유휴 상태 확인 즉시 초고속 붙여넣기 시작
        print("  → ⚡ 초고속 붙여넣기 시작!")
        
        # Cursor 윈도우를 강제로 전면으로 가져오기 (여러 번 시도)
        hwnd = cursor_window.handle
        
        print(f"  → Cursor 윈도우 활성화 중 (최대 3회 시도, 약 {Config.WINDOW_ACTIVATION_RETRY_DELAY * 2}초)...")
        activation_start_time = time.time()
        activation_success = False
        for attempt in range(3):
            success = force_window_to_foreground(hwnd)
            if success:
                activation_time = time.time() - activation_start_time
                print(f"  → ✓ Cursor 윈도우 활성화 완료 (시도 {attempt + 1}/3, {activation_time:.1f}초 소요)")
                activation_success = True
                break
            else:
                print(f"  → ⚠ 활성화 실패, 재시도... (시도 {attempt + 1}/3)")
                time.sleep(Config.WINDOW_ACTIVATION_RETRY_DELAY)
        
        if not activation_success:
            activation_time = time.time() - activation_start_time
            print(f"  → ⚠ 3회 시도 완료 ({activation_time:.1f}초 소요), 마지막 시도 진행...")
            # 마지막 한 번 더 시도
            force_window_to_foreground(hwnd)
            time.sleep(0.5)
        
        # 윈도우 활성화 후 충분한 안정화 시간
        print(f"  → 윈도우 안정화 대기 중 ({Config.WINDOW_STABILIZATION_DELAY}초)...")
        stabilization_start = time.time()
        time.sleep(Config.WINDOW_STABILIZATION_DELAY)
        stabilization_time = time.time() - stabilization_start
        print(f"  → ✓ 안정화 완료 ({stabilization_time:.1f}초 소요)")
        
        # 카운트다운 프로세스 종료 (0초 도달)
        if countdown_process and countdown_process.poll() is None:
            try:
                countdown_process.terminate()
                countdown_process.wait(timeout=0.5)
            except:
                pass
        
        # 타임아웃 체크
        if time.time() - start_time > timeout_seconds:
            print(f"  ⚠ 전체 타임아웃 ({timeout_seconds}초 초과)")
            return False
        
        # ★ 프롬프트 창 영역 클릭 (포커스 확보)
        print("  → 프롬프트 입력창 클릭...")
        try:
            rect = win32gui.GetWindowRect(hwnd)
            # 윈도우 하단 중앙 부근 클릭 (프롬프트 입력창이 보통 하단에 위치)
            x = rect[0] + (rect[2] - rect[0]) // 2  # 중앙
            y = rect[3] - 100  # 하단에서 100px 위
            
            windll.user32.SetCursorPos(x, y)
            time.sleep(0.2)
            windll.user32.mouse_event(2, 0, 0, 0, 0)  # Left down
            windll.user32.mouse_event(4, 0, 0, 0, 0)  # Left up
            time.sleep(0.5)  # 클릭 후 포커스 안정화
            print(f"  → 프롬프트 창 클릭 완료 (위치: {x}, {y})")
        except Exception as e:
            print(f"  ⚠ 프롬프트 클릭 오류: {e}")
        
        # ★ 사용자 입력 차단 시작 (붙여넣기 중 방해 방지)
        input_blocked = block_user_input(True)
        
        # ★★★ 입력 차단 시작 시점의 마우스 위치 저장 (붙여넣기 작업 시작 기준점)
        try:
            cursor_pos = win32api.GetCursorPos()
            paste_start_mouse_pos = (cursor_pos[0], cursor_pos[1])
            print(f"  → 붙여넣기 시작 시점 마우스 위치: ({paste_start_mouse_pos[0]}, {paste_start_mouse_pos[1]})")
        except Exception as e:
            print(f"  ⚠ 시작 시점 마우스 위치 저장 오류: {e}")
        
        try:
            # ★★★ 입력 차단 후 클립보드에 복사 (사용자 복사 내용 덮어쓰기 방지)
            import pyperclip
            print("  → 클립보드에 복사...")
            pyperclip.copy(text)
            time.sleep(0.3)  # 클립보드 복사 완료 대기
            print("  → 클립보드 복사 완료!")
            
            # Ctrl+N으로 새로운 프롬프트 창 열기
            print("  → Ctrl+N으로 새 프롬프트 창 열기...")
            try:
                send_keys("^n")  # Ctrl+N (새 프롬프트)
                time.sleep(Config.NEW_PROMPT_OPEN_DELAY)
                print("  → 새 프롬프트 창 열림")
            except Exception as e:
                print(f"  ⚠ 새 프롬프트 열기 오류: {e}")
            
            # 붙여넣기 실행
            print("  → 붙여넣기 실행...")
            try:
                send_keys("^v")  # Ctrl+V (붙여넣기)
                time.sleep(Config.PASTE_COMPLETION_DELAY)
                print("  → 붙여넣기 명령 전송 완료")
            except Exception as e:
                print(f"  ⚠ 붙여넣기 오류: {e}")
            
            try:
                send_keys("{ENTER}")  # Enter
                time.sleep(0.5)
                print("  → Enter 전송 완료")
            except Exception as e:
                print(f"  ⚠ Enter 전송 오류: {e}")
            
            print("  → ✓ 완료!")
            return True
        
        finally:
            # ★ 사용자 입력 차단 해제 (반드시 실행)
            # 3회 연속 검사를 통한 확실한 복구
            if input_blocked:
                print("  → 입력 차단 해제 시작...")
                
                # 안전 타이머 취소
                if safety_timer and safety_timer.is_alive():
                    safety_timer.cancel()
                    print("  → [안전장치] 타이머 취소됨")
                
                # 3회 연속 차단 해제 및 확인
                for verify_attempt in range(3):
                    try:
                        # 차단 해제 시도
                        result = windll.user32.BlockInput(False)
                        
                        # 0.05초 대기 후 상태 확인을 위해 다시 해제 시도
                        time.sleep(0.05)
                        verify_result = windll.user32.BlockInput(False)
                        
                        if result and verify_result:
                            print(f"  ✓ 차단 해제 확인 완료 (검증 {verify_attempt + 1}/3)")
                        else:
                            print(f"  ⚠ 차단 해제 미확인 - 재시도 (검증 {verify_attempt + 1}/3)")
                    except Exception as e:
                        print(f"  ⚠ 차단 해제 오류 (검증 {verify_attempt + 1}/3): {e}")
                
                # 전역 상태 업데이트
                input_block_active = False
                print("  ✓ 입력 차단 해제 완료 (3회 검증 완료)")
            
            # ★★★ 원래 상태로 복원
            print("  → 원래 상태로 복원 중...")
            
            # 원래 윈도우로 복원
            if original_foreground_hwnd and original_foreground_hwnd != 0:
                try:
                    print("  → 원래 윈도우 활성화...")
                    
                    # 간단한 방법으로 복원 시도
                    try:
                        win32gui.SetForegroundWindow(original_foreground_hwnd)
                    except:
                        # 실패 시 Alt 키 트릭 사용
                        windll.user32.keybd_event(0x12, 0, 0, 0)  # Alt Down
                        time.sleep(0.05)
                        try:
                            win32gui.SetForegroundWindow(original_foreground_hwnd)
                        except:
                            pass
                        windll.user32.keybd_event(0x12, 0, 2, 0)  # Alt Up
                    
                    time.sleep(0.3)
                    print("  → 원래 윈도우 복원 완료")
                except Exception as e:
                    print(f"  ⚠ 윈도우 복원 오류: {e}")
            
            # 원래 마우스 위치로 복원 (사용자가 이동하지 않은 경우에만)
            if original_mouse_pos:
                try:
                    # 복원 직전에 현재 마우스 위치 다시 확인 (사용자가 이동했는지 체크)
                    current_mouse_pos = win32api.GetCursorPos()
                    
                    # 붙여넣기 시작 시점의 마우스 위치와 비교 (입력 차단 후 이동 감지)
                    if paste_start_mouse_pos:
                        mouse_moved_during_paste = (
                            abs(current_mouse_pos[0] - paste_start_mouse_pos[0]) > 10 or
                            abs(current_mouse_pos[1] - paste_start_mouse_pos[1]) > 10
                        )
                        
                        if mouse_moved_during_paste:
                            print(f"  → 붙여넣기 중 사용자가 마우스를 이동함 - 위치 복원 생략")
                            print(f"     시작: ({paste_start_mouse_pos[0]}, {paste_start_mouse_pos[1]}), 현재: ({current_mouse_pos[0]}, {current_mouse_pos[1]})")
                        else:
                            # 마우스가 거의 같은 위치면 원래 위치로 복원
                            windll.user32.SetCursorPos(original_mouse_pos[0], original_mouse_pos[1])
                            print(f"  → 마우스 위치 복원 완료: ({original_mouse_pos[0]}, {original_mouse_pos[1]})")
                    else:
                        # paste_start_mouse_pos가 없으면 original_mouse_pos와 비교
                        mouse_moved = (
                            abs(current_mouse_pos[0] - original_mouse_pos[0]) > 10 or
                            abs(current_mouse_pos[1] - original_mouse_pos[1]) > 10
                        )
                        
                        if mouse_moved:
                            print(f"  → 사용자가 마우스를 이동함 - 위치 복원 생략")
                            print(f"     원래: ({original_mouse_pos[0]}, {original_mouse_pos[1]}), 현재: ({current_mouse_pos[0]}, {current_mouse_pos[1]})")
                        else:
                            windll.user32.SetCursorPos(original_mouse_pos[0], original_mouse_pos[1])
                            print(f"  → 마우스 위치 복원 완료: ({original_mouse_pos[0]}, {original_mouse_pos[1]})")
                except Exception as e:
                    print(f"  ⚠ 마우스 위치 복원 오류: {e}")
            
            print("  ✓ 복원 완료!")
            
    except Exception as e:
        print(f"✗ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        
        # ★ 예외 발생 시에도 입력 차단 해제 보장
        print("  → [긴급] 예외 발생으로 인한 입력 차단 해제...")
        for emergency_attempt in range(3):
            try:
                windll.user32.BlockInput(False)
                time.sleep(0.05)
                print(f"  ✓ 긴급 차단 해제 시도 {emergency_attempt + 1}/3")
            except:
                pass
        
        input_block_active = False
        
        return False


def monitor_files_and_send(status_file, roll_file, cursor_windows_list, check_interval=1.0):
    """
    status.json과 roll.txt 파일을 모니터링하다가 변경 시 내용을 합쳐서 Cursor에 자동 입력
    여러 Cursor 윈도우를 순환하면서 붙여넣기
    
    Args:
        status_file: 모니터링할 status.json 파일 경로
        roll_file: 모니터링할 roll.txt 파일 경로
        cursor_windows_list: 입력할 Cursor 윈도우 객체 리스트
        check_interval: 파일 확인 간격(초)
    """
    global input_block_active, safety_timer
    
    print(f"\n" + "="*80)
    print(f"파일 모니터링 시작")
    print(f"="*80)
    print(f"모니터링 대상 파일:")
    print(f"  - {status_file}")
    print(f"  - {roll_file}")
    print(f"선택된 Cursor 윈도우: {len(cursor_windows_list)}개")
    print(f"확인 간격: {check_interval}초")
    print(f"종료하려면 Ctrl+C를 누르세요.")
    print(f"="*80 + "\n")
    
    last_hash = None
    check_count = 0
    paste_count = 0  # 붙여넣기 성공 횟수
    last_paste_time = None  # 마지막 붙여넣기 시간
    current_window_index = 0  # 현재 윈도우 인덱스 (순환용)
    
    try:
        while True:
            # 두 파일의 통합 해시값 계산
            current_hash = get_files_combined_hash(status_file, roll_file)
            
            if current_hash is None:
                time.sleep(check_interval)
                continue
            
            # 초기화 시 해시 저장
            if last_hash is None:
                last_hash = current_hash
                print(f"[초기화] 파일 모니터링 준비 완료\n")
            
            # 파일이 변경되었는지 확인
            if current_hash != last_hash:
                print(f"\n" + "="*80)
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ★ 파일 변경 감지! ★")
                print(f"="*80)
                
                # 두 파일의 내용을 읽어서 합치기
                combined_content = read_and_combine_files(status_file, roll_file)
                
                if combined_content:
                    print(f"파일 내용 읽기 완료 (총 {len(combined_content)} 자)")
                    
                    # 현재 순서의 Cursor 윈도우 선택
                    cursor_window = cursor_windows_list[current_window_index]
                    window_info = f"[{current_window_index + 1}/{len(cursor_windows_list)}]"
                    
                    print(f"{window_info} 대상 윈도우: {cursor_window.window_text()}")
                    
                    # Cursor에 내용 전송 (사용자 유휴 대기 포함)
                    try:
                        success = send_text_to_cursor(combined_content, cursor_window)
                        
                        if success:
                            paste_count += 1
                            last_paste_time = time.strftime('%Y-%m-%d %H:%M:%S')
                            
                            print(f"\n" + "="*80)
                            print(f"✓ 작업 완료! 파일 내용이 Cursor에 전송되었습니다.")
                            print(f"  {window_info} [{paste_count}회째 붙여넣기 성공] {last_paste_time}")
                            print(f"="*80 + "\n")
                            
                            # 다음 윈도우로 순환
                            current_window_index = (current_window_index + 1) % len(cursor_windows_list)
                        else:
                            print(f"\n" + "="*80)
                            print(f"✗ 전송 실패 (함수 반환 False)")
                            print(f"="*80 + "\n")
                    except Exception as send_error:
                        print(f"\n" + "="*80)
                        print(f"✗ 전송 중 예외 발생: {send_error}")
                        print(f"="*80)
                        import traceback
                        traceback.print_exc()
                        print("="*80)
                        print("모니터링을 계속 진행합니다...\n")
                else:
                    print(f"✗ 파일 내용을 읽을 수 없습니다.\n")
            
            # 해시 업데이트
            last_hash = current_hash
            
            # 모니터링 상태 표시 (10번마다)
            check_count += 1
            if check_count % 10 == 0:
                print(f"[모니터링 중...] 확인 횟수: {check_count}회 ({time.strftime('%H:%M:%S')})", end='\r')
            
            # 대기
            time.sleep(check_interval)
            
    except KeyboardInterrupt:
        print("\n\n" + "="*80)
        print("모니터링 중지됨 (사용자 요청)")
        print("="*80)
        
        # ★ 프로그램 종료 시 입력 차단 해제 보장
        print("  → 입력 차단 상태 확인 및 해제...")
        for final_attempt in range(3):
            try:
                windll.user32.BlockInput(False)
                time.sleep(0.05)
                print(f"  ✓ 종료 시 차단 해제 {final_attempt + 1}/3")
            except:
                pass
        
        input_block_active = False
        if safety_timer and safety_timer.is_alive():
            safety_timer.cancel()
        
        print("  ✓ 안전하게 종료되었습니다.")
        return True
    except Exception as e:
        print(f"\n✗ 모니터링 오류: {e}")
        import traceback
        traceback.print_exc()
        
        # ★ 예외 발생 시 입력 차단 해제 보장
        print("  → [긴급] 예외로 인한 입력 차단 해제...")
        for emergency_attempt in range(3):
            try:
                windll.user32.BlockInput(False)
                time.sleep(0.05)
            except:
                pass
        
        input_block_active = False
        if safety_timer and safety_timer.is_alive():
            safety_timer.cancel()
        
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("Cursor 프롬프트 입력창 자동화 프로그램")
    print("=" * 50)
    
    # 고정된 파일 경로 사용
    status_file = "status.json"
    roll_file = "roll.txt"
    
    print(f"\n모니터링 대상 파일:")
    print(f"  - {status_file}")
    print(f"  - {roll_file}")
    
    # 파일 존재 확인
    if not os.path.exists(status_file):
        print(f"\n경고: {status_file} 파일이 아직 존재하지 않습니다.")
    
    if not os.path.exists(roll_file):
        print(f"경고: {roll_file} 파일이 아직 존재하지 않습니다.")
    
    if not os.path.exists(status_file) and not os.path.exists(roll_file):
        print("\n파일이 생성될 때까지 대기합니다...\n")
    
    # 선택할 Cursor 윈도우 개수 입력
    print("\n" + "=" * 50)
    while True:
        try:
            num_windows = input("선택할 Cursor 윈도우 개수 (1-10, 0=종료): ").strip()
            if not num_windows:
                continue
            
            num_windows = int(num_windows)
            
            if num_windows == 0:
                print("프로그램을 종료합니다.")
                sys.exit(0)
            
            if 1 <= num_windows <= 10:
                break
            else:
                print("⚠ 1부터 10 사이의 숫자를 입력하세요.")
        except ValueError:
            print("⚠ 올바른 숫자를 입력하세요.")
        except KeyboardInterrupt:
            print("\n\n프로그램을 종료합니다.")
            sys.exit(0)
    
    print(f"\n선택할 윈도우 개수: {num_windows}개")
    print("=" * 50)
    
    print("\n1단계: Cursor 윈도우 선택")
    print("-" * 50)
    
    # 모든 Cursor 윈도우 찾기
    cursor_windows = find_all_cursor_windows()
    
    if not cursor_windows:
        print("실행 중인 Cursor 윈도우를 찾을 수 없습니다.")
        sys.exit(1)
    
    if len(cursor_windows) < num_windows:
        print(f"⚠ 실행 중인 Cursor 윈도우가 {len(cursor_windows)}개뿐입니다.")
        print(f"  요청한 {num_windows}개를 선택할 수 없습니다.")
        sys.exit(1)
    
    # 제목에 "prompt" 포함 윈도우 개수가 요청 개수와 같으면 자동 선택
    prompt_windows = [
        w for w in cursor_windows
        if "prompt" in (w.get("title") or "").lower()
    ]
    selected_windows = []
    if len(prompt_windows) == num_windows:
        print(
            f'\n제목에 "prompt"가 포함된 Cursor 윈도우가 {num_windows}개뿐이어서 '
            "자동 선택합니다."
        )
        for w in prompt_windows:
            selected_windows.append(w["window"])
            print(f"  → {w['title']}")
    else:
        for i in range(num_windows):
            print(f"\n[{i + 1}/{num_windows}] 번째 Cursor 윈도우 선택:")
            cursor_window = select_cursor_window(cursor_windows)
            
            if not cursor_window:
                print("Cursor 윈도우가 선택되지 않았습니다.")
                sys.exit(1)
            
            selected_windows.append(cursor_window)
            print(f"  → 선택됨: {cursor_window.window_text()}")
    
    print(f"\n✓ 총 {len(selected_windows)}개의 Cursor 윈도우 선택 완료")
    print("\n선택된 윈도우 목록:")
    for i, win in enumerate(selected_windows):
        print(f"  {i + 1}. {win.window_text()}")
    
    print("\n2단계: 파일 모니터링 시작")
    print("-" * 50)
    
    # 파일 모니터링 시작 (여러 윈도우 전달)
    success = monitor_files_and_send(status_file, roll_file, selected_windows)
    
    if success:
        print("\n✓ 프로그램이 정상적으로 종료되었습니다.")
        sys.exit(0)
    else:
        print("\n✗ 프로그램 실행 중 오류가 발생했습니다.")
        sys.exit(1)
