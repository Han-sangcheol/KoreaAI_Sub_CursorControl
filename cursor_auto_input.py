"""
Cursor 프롬프트 입력창 자동화 프로그램
- status.json과 roll.txt 파일을 모니터링
- 두 파일의 내용을 합쳐서 Cursor IDE의 프롬프트 입력창에 자동으로 입력
- Windows 메시지를 사용하여 백그라운드에서 안전하게 입력 (사용자의 작업 방해 없음)
- 입력 후 자동으로 엔터 키를 눌러 전송
- 여러 개의 Cursor 인스턴스가 실행 중일 때 사용자가 선택할 수 있도록 지원
- 사용자 입력 감지: 키보드/마우스 입력이 3초간 없을 때까지 대기 후 실행
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
import ctypes
from ctypes import windll, Structure, c_long, byref


class LASTINPUTINFO(Structure):
    """
    Windows API의 LASTINPUTINFO 구조체
    마지막 입력 시간 정보를 가져오기 위한 구조체
    """
    _fields_ = [
        ('cbSize', c_long),
        ('dwTime', c_long),
    ]


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
    프롬프트 창이 닫혀있을 경우에만 Ctrl+Alt+B로 입력창 열기
    """
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
        
        # 사용자 입력이 없는 상태가 3.0초 지속될 때까지 대기
        wait_for_user_idle(idle_seconds=3.0, check_interval=0.5)
        
        # ★ 유휴 상태 확인 즉시 초고속 붙여넣기 시작
        print("  → ⚡ 초고속 붙여넣기 시작!")
        
        # Cursor 윈도우를 활성화
        cursor_window.set_focus()
        time.sleep(0.5)  # 윈도우 활성화 충분한 대기
        
        # 프롬프트 입력창 상태 확인 및 열기
        print("  → 프롬프트 입력창 상태 확인...")
        input_window_open = False
        initial_edit_count = 0
        
        try:
            edit_controls = cursor_window.descendants(control_type="Edit")
            visible_controls = [ctrl for ctrl in edit_controls if ctrl.is_visible() and ctrl.is_enabled()]
            initial_edit_count = len(visible_controls)
            
            if visible_controls:
                print(f"  → 입력창이 이미 열려있습니다 (Edit 컨트롤: {initial_edit_count}개)")
                input_window_open = True
            else:
                print(f"  → 입력창이 닫혀있습니다 (Edit 컨트롤: {initial_edit_count}개). 여는 중...")
        except Exception as e:
            print(f"  → 입력창 상태 확인 실패 ({e}). 여는 중...")
        
        # 입력창이 닫혀있으면 열기 (최대 4회 시도)
        if not input_window_open:
            max_attempts = 4
            for attempt in range(max_attempts):
                print(f"  → Ctrl+Alt+B 시도 {attempt + 1}/{max_attempts}")
                send_keys("^%b")  # Ctrl+Alt+B로 입력창 토글
                time.sleep(1.2)  # 입력창 열리는 시간 충분히 대기 (1초 이상 필요)
                
                # 입력창이 열렸는지 확인 (Edit 컨트롤 개수 변화로 판단)
                try:
                    edit_controls = cursor_window.descendants(control_type="Edit")
                    visible_controls = [ctrl for ctrl in edit_controls if ctrl.is_visible() and ctrl.is_enabled()]
                    current_edit_count = len(visible_controls)
                    
                    # Edit 컨트롤이 증가했거나 존재하면 성공
                    if visible_controls and (current_edit_count > initial_edit_count or current_edit_count > 0):
                        print(f"  → ✓ 입력창 열기 성공! (Edit 컨트롤: {initial_edit_count} → {current_edit_count}개)")
                        input_window_open = True
                        break
                    else:
                        print(f"  → ✗ 입력창 아직 닫혀있음 (Edit 컨트롤: {current_edit_count}개)")
                except Exception as e:
                    print(f"  → ✗ 확인 실패: {e}")
        
        # 입력창이 열리지 않았으면 경고
        if not input_window_open:
            print("  ⚠ 경고: 입력창을 열지 못했습니다. 붙여넣기를 시도합니다...")
        
        # 입력창 준비 완료 후 대기
        time.sleep(0.3)
        
        # Edit 컨트롤에 직접 포커스 시도
        print("  → Edit 컨트롤 포커스 설정...")
        try:
            edit_controls = cursor_window.descendants(control_type="Edit")
            visible_controls = [ctrl for ctrl in edit_controls if ctrl.is_visible() and ctrl.is_enabled()]
            
            if visible_controls:
                # 가장 마지막(가장 아래) Edit 컨트롤에 포커스
                target_control = visible_controls[-1]
                target_control.set_focus()
                time.sleep(0.3)
                print(f"  → Edit 컨트롤 포커스 완료 (인덱스: {len(visible_controls)-1})")
            else:
                print("  ⚠ Edit 컨트롤을 찾을 수 없습니다")
        except Exception as e:
            print(f"  ⚠ Edit 포커스 설정 오류: {e}")
        
        # 전체 선택 + 붙여넣기 + Enter를 연속으로 실행
        print("  → 붙여넣기 실행...")
        try:
            send_keys("^a")  # Ctrl+A (전체 선택)
            time.sleep(0.1)
        except Exception as e:
            print(f"  ⚠ 전체 선택 오류: {e}")
        
        try:
            send_keys("^v")  # Ctrl+V (붙여넣기)
            time.sleep(0.8)  # 붙여넣기 완료 대기 증가
            print("  → 붙여넣기 명령 전송 완료")
        except Exception as e:
            print(f"  ⚠ 붙여넣기 오류: {e}")
            # 붙여넣기 실패해도 계속 진행
        
        # Enter 키 전송
        print("  → Enter 전송...")
        try:
            send_keys("{ENTER}")
            time.sleep(0.2)
        except Exception as e:
            print(f"  ⚠ Enter 전송 오류: {e}")
        
        print("  → ✓ 완료!")
        return True
            
    except Exception as e:
        print(f"✗ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
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
        return True
    except Exception as e:
        print(f"\n✗ 모니터링 오류: {e}")
        import traceback
        traceback.print_exc()
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
