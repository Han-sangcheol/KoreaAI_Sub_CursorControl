"""
Cursor 프롬프트 입력창 자동화 프로그램
- status.json과 roll.txt 파일을 모니터링
- 두 파일의 내용을 합쳐서 Cursor IDE의 프롬프트 입력창에 자동으로 입력
- Windows 메시지를 사용하여 백그라운드에서 안전하게 입력 (사용자의 작업 방해 없음)
- 입력 후 자동으로 엔터 키를 눌러 전송
- 여러 개의 Cursor 인스턴스가 실행 중일 때 사용자가 선택할 수 있도록 지원
- 사용자 입력 감지: 키보드/마우스 입력이 3초간 없을 때까지 대기 후 실행
- 2초 안전 타이머: 입력 차단이 2초 이상 지속되지 않도록 자동 해제
- Ctrl+L 2회 전략: 프롬프트 창 열림/닫힘 상태와 무관하게 확실하게 붙여넣기
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
                safety_timer = threading.Timer(2.0, emergency_unblock_input)
                safety_timer.daemon = True
                safety_timer.start()
                print("  → [안전장치] 2초 타이머 가동")
                
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
    윈도우를 강제로 전면으로 가져오기 (Windows 보안 정책 우회)
    
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
            time.sleep(0.1)
        
        # 4. 윈도우를 보이게 설정
        win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
        time.sleep(0.05)
        
        # 5. 현재 프로세스와 전면 윈도우의 스레드를 연결 (Windows 보안 우회)
        if current_foreground != 0:
            current_thread = win32api.GetCurrentThreadId()
            foreground_thread = win32process.GetWindowThreadProcessId(current_foreground)[0]
            
            if current_thread != foreground_thread:
                # 스레드 연결
                windll.user32.AttachThreadInput(current_thread, foreground_thread, True)
                
                # 윈도우를 전면으로
                win32gui.SetForegroundWindow(hwnd)
                win32gui.BringWindowToTop(hwnd)
                win32gui.SetActiveWindow(hwnd)
                
                # 스레드 분리
                windll.user32.AttachThreadInput(current_thread, foreground_thread, False)
            else:
                win32gui.SetForegroundWindow(hwnd)
        else:
            win32gui.SetForegroundWindow(hwnd)
        
        time.sleep(0.2)
        
        # 6. 확인
        new_foreground = win32gui.GetForegroundWindow()
        return new_foreground == hwnd
        
    except Exception as e:
        print(f"  ⚠ 윈도우 활성화 오류: {e}")
        return False


def wait_for_user_idle(idle_seconds=3.0, check_interval=0.5):
    """
    사용자가 키보드나 마우스를 사용하지 않는 상태가 지정된 시간만큼 지속될 때까지 대기
    이 함수 호출 시점부터 idle_seconds 동안 입력이 없어야 함
    
    Args:
        idle_seconds: 대기할 유휴 시간(초)
        check_interval: 확인 간격(초)
    """
    print(f"\n  → 사용자 입력 감지 시작 ({idle_seconds}초간 유휴 상태 대기)")
    print(f"     [INFO] 키보드나 마우스를 사용하면 타이머가 리셋됩니다")
    
    # 이 시점부터 idle_seconds 동안 입력이 없어야 함
    idle_start_time = time.time()
    last_input_detected_time = time.time()
    total_start_time = time.time()
    
    while True:
        current_time = time.time()
        system_idle_time = get_idle_duration()
        elapsed_since_last_input = current_time - last_input_detected_time
        elapsed_total = current_time - total_start_time
        
        # 시스템 유휴 시간이 0.5초 미만이면 사용자가 방금 입력함
        if system_idle_time < 0.5:
            if elapsed_since_last_input > 0.5:  # 이전에 유휴 상태였다면
                print(f"\n  ⚠ 사용자 입력 감지! 타이머 리셋 (총 대기: {elapsed_total:.1f}초)")
            last_input_detected_time = current_time
            idle_start_time = current_time
        
        # 마지막 입력 이후 경과 시간 계산
        time_since_last_input = current_time - last_input_detected_time
        
        # idle_seconds 이상 입력이 없으면 완료
        if time_since_last_input >= idle_seconds:
            # ★ 100% 진행률 표시 먼저 출력
            bar_full = '█' * 20
            print(f"     [{bar_full}] 100.0% | 유휴: {idle_seconds:.1f}초 / {idle_seconds}초 (총 대기: {elapsed_total:.1f}초)    ")
            print(f"  ✓ 유휴 상태 {idle_seconds}초 확인 완료! (총 대기 시간: {elapsed_total:.1f}초)")
            print(f"  → 이제 복사 및 붙여넣기를 진행합니다...")
            break
        
        # 진행 상태 표시
        progress = (time_since_last_input / idle_seconds) * 100
        bar_length = 20
        filled = int(bar_length * time_since_last_input / idle_seconds)
        bar = '█' * filled + '░' * (bar_length - filled)
        
        print(f"     [{bar}] {progress:5.1f}% | 유휴: {time_since_last_input:.1f}초 / {idle_seconds}초 (총 대기: {elapsed_total:.1f}초)    ", end='\r')
        time.sleep(check_interval)
    
    print()  # 줄바꿈


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


def send_text_to_cursor(text, cursor_window):
    """
    텍스트를 지정된 Cursor 프롬프트 입력창에 입력하고 엔터
    Electron 앱 특성상 윈도우 활성화 후 키보드 시뮬레이션 사용
    사용자가 키보드/마우스를 사용 중이면 3.0초간 유휴 상태가 될 때까지 대기
    유휴 대기 중에 미리 클립보드에 복사하여 대기 완료 후 초고속으로 붙여넣기 실행
    
    Ctrl+L을 2회 실행하여 프롬프트 창 상태와 무관하게 확실하게 붙여넣기:
    - 1차: Ctrl+L + 붙여넣기 (열려있으면 닫힘 → 실패, 닫혀있으면 열림 → 성공)
    - 2차: Ctrl+L + 붙여넣기 (1차의 반대 상태이므로 1차 실패했으면 성공)
    - 결과: 최소 1회는 반드시 성공
    
    전체 실행 시간이 너무 길면 타임아웃으로 종료하여 모니터링 루프가 멈추지 않도록 함
    """
    global input_block_active, safety_timer
    
    start_time = time.time()
    timeout_seconds = 30.0  # 최대 30초 제한
    
    try:
        if not text:
            print("입력할 텍스트가 비어있습니다.")
            return False
        
        print(f"입력할 텍스트: {text[:50]}...")
        
        # ★ 유휴 대기 전에 미리 클립보드에 복사 (대기 시간 단축)
        import pyperclip
        print("  → 클립보드에 미리 복사...")
        pyperclip.copy(text)
        print("  → 준비 완료!")
        
        # 타임아웃 체크
        if time.time() - start_time > timeout_seconds:
            print(f"  ⚠ 타임아웃 ({timeout_seconds}초 초과)")
            return False
        
        # 사용자 입력이 없는 상태가 3.0초 지속될 때까지 대기
        wait_for_user_idle(idle_seconds=3.0, check_interval=0.5)
        
        # 타임아웃 체크
        if time.time() - start_time > timeout_seconds:
            print(f"  ⚠ 타임아웃 ({timeout_seconds}초 초과)")
            return False
        
        # ★ 유휴 상태 확인 즉시 초고속 붙여넣기 시작
        print("  → ⚡ 초고속 붙여넣기 시작!")
        
        # Cursor 윈도우를 강제로 전면으로 가져오기
        print("  → Cursor 윈도우 활성화...")
        hwnd = cursor_window.handle
        
        success = force_window_to_foreground(hwnd)
        if success:
            print("  → ✓ Cursor 윈도우 활성화 완료")
        else:
            print("  → ⚠ 윈도우 활성화 실패했지만 계속 진행...")
        
        # 타임아웃 체크
        if time.time() - start_time > timeout_seconds:
            print(f"  ⚠ 전체 타임아웃 ({timeout_seconds}초 초과)")
            return False
        
        # ★ 사용자 입력 차단 시작 (붙여넣기 중 방해 방지)
        input_blocked = block_user_input(True)
        
        try:
            # ★★★ Ctrl+L 2회 전략: 어떤 상태든 중간에 한 번은 열린 상태가 됨
            print("  → [1차 시도] Ctrl+L로 프롬프트 창 토글...")
            try:
                send_keys("^l")  # Ctrl+L (첫 번째)
                time.sleep(1.2)  # 프롬프트 창 열림 대기 (충분한 시간 확보)
                
                # 첫 번째 붙여넣기 시도
                send_keys("^a")  # Ctrl+A
                time.sleep(0.15)
                send_keys("^v")  # Ctrl+V
                time.sleep(1.0)  # 붙여넣기 완료 대기
                send_keys("{ENTER}")
                time.sleep(0.3)
                print("  → [1차 시도] 붙여넣기 완료")
            except Exception as e:
                print(f"  ⚠ [1차 시도] 오류: {e}")
            
            # 시도 간 대기
            time.sleep(0.3)
            
            # ★★★ 두 번째 시도: 상태가 반대로 되었으므로 다시 시도
            print("  → [2차 시도] Ctrl+L로 프롬프트 창 토글...")
            try:
                send_keys("^l")  # Ctrl+L (두 번째)
                time.sleep(1.2)  # 프롬프트 창 열림 대기 (충분한 시간 확보)
                
                # 두 번째 붙여넣기 시도
                send_keys("^a")  # Ctrl+A
                time.sleep(0.15)
                send_keys("^v")  # Ctrl+V
                time.sleep(1.0)  # 붙여넣기 완료 대기
                send_keys("{ENTER}")
                time.sleep(0.3)
                print("  → [2차 시도] 붙여넣기 완료")
            except Exception as e:
                print(f"  ⚠ [2차 시도] 오류: {e}")
            
            print("  → ✓ 2회 시도 완료! (최소 1회는 성공)")
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


def monitor_files_and_send(status_file, roll_file, cursor_window, check_interval=1.0):
    """
    status.json과 roll.txt 파일을 모니터링하다가 변경 시 내용을 합쳐서 Cursor에 자동 입력
    
    Args:
        status_file: 모니터링할 status.json 파일 경로
        roll_file: 모니터링할 roll.txt 파일 경로
        cursor_window: 입력할 Cursor 윈도우 객체
        check_interval: 파일 확인 간격(초)
    """
    global input_block_active, safety_timer
    
    print(f"\n" + "="*80)
    print(f"파일 모니터링 시작")
    print(f"="*80)
    print(f"모니터링 대상 파일:")
    print(f"  - {status_file}")
    print(f"  - {roll_file}")
    print(f"확인 간격: {check_interval}초")
    print(f"종료하려면 Ctrl+C를 누르세요.")
    print(f"="*80 + "\n")
    
    last_hash = None
    check_count = 0
    
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
                    
                    # Cursor에 내용 전송 (사용자 유휴 대기 포함)
                    try:
                        success = send_text_to_cursor(combined_content, cursor_window)
                        
                        if success:
                            print(f"\n" + "="*80)
                            print(f"✓ 작업 완료! 파일 내용이 Cursor에 전송되었습니다.")
                            print(f"="*80 + "\n")
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
    
    print("\n1단계: Cursor 윈도우 선택")
    print("-" * 50)
    
    # 모든 Cursor 윈도우 찾기
    cursor_windows = find_all_cursor_windows()
    
    if not cursor_windows:
        print("실행 중인 Cursor 윈도우를 찾을 수 없습니다.")
        sys.exit(1)
    
    # 사용자가 윈도우 선택
    cursor_window = select_cursor_window(cursor_windows)
    
    if not cursor_window:
        print("Cursor 윈도우가 선택되지 않았습니다.")
        sys.exit(1)
    
    print("\n2단계: 파일 모니터링 시작")
    print("-" * 50)
    
    # 파일 모니터링 시작
    success = monitor_files_and_send(status_file, roll_file, cursor_window)
    
    if success:
        print("\n✓ 프로그램이 정상적으로 종료되었습니다.")
        sys.exit(0)
    else:
        print("\n✗ 프로그램 실행 중 오류가 발생했습니다.")
        sys.exit(1)
