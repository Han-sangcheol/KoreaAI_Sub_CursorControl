"""
마우스 포인터 옆에 카운트다운을 표시하는 독립 프로세스
- 다중 모니터 환경 완전 지원
- 마우스를 실시간으로 따라다님
"""
import tkinter as tk
from tkinter import font as tkfont
import win32api
import win32con
import sys


def get_monitor_info():
    """
    모든 모니터의 정보를 가져옴
    """
    monitors = []
    
    def callback(hMonitor, hdcMonitor, lprcMonitor, dwData):
        monitors.append({
            'left': lprcMonitor[0],
            'top': lprcMonitor[1],
            'right': lprcMonitor[2],
            'bottom': lprcMonitor[3],
            'width': lprcMonitor[2] - lprcMonitor[0],
            'height': lprcMonitor[3] - lprcMonitor[1]
        })
        return True
    
    try:
        import ctypes
        # EnumDisplayMonitors 호출
        ctypes.windll.user32.EnumDisplayMonitors(None, None, ctypes.WINFUNCTYPE(
            ctypes.c_int, ctypes.c_ulong, ctypes.c_ulong, ctypes.POINTER(ctypes.c_long), ctypes.c_double
        )(callback), 0)
    except:
        # 실패 시 기본값 사용
        monitors = [{
            'left': 0,
            'top': 0,
            'right': win32api.GetSystemMetrics(0),
            'bottom': win32api.GetSystemMetrics(1),
            'width': win32api.GetSystemMetrics(0),
            'height': win32api.GetSystemMetrics(1)
        }]
    
    return monitors


def find_monitor_for_point(x, y, monitors):
    """
    특정 좌표가 속한 모니터 찾기
    """
    for monitor in monitors:
        if (monitor['left'] <= x < monitor['right'] and 
            monitor['top'] <= y < monitor['bottom']):
            return monitor
    
    # 못 찾으면 첫 번째 모니터 반환
    return monitors[0] if monitors else None


def show_countdown(seconds=3):
    """
    마우스 포인터를 따라다니는 카운트다운 표시 (다중 모니터 지원)
    """
    # 모니터 정보 가져오기
    monitors = get_monitor_info()
    print(f"감지된 모니터: {len(monitors)}개")
    for i, m in enumerate(monitors):
        print(f"  모니터 {i+1}: ({m['left']}, {m['top']}) ~ ({m['right']}, {m['bottom']}) [{m['width']}x{m['height']}]")
    
    # Tkinter 윈도우 생성
    root = tk.Tk()
    
    # 윈도우 설정
    root.attributes('-topmost', True)  # 항상 최상위
    root.overrideredirect(True)  # 타이틀바 제거
    root.attributes('-transparentcolor', 'black')  # 검은색을 투명하게
    root.config(bg='black')  # 배경을 검은색(투명)으로
    
    # 라벨 생성 - 작은 크기, 투명 배경
    label = tk.Label(
        root,
        text=str(seconds),
        font=tkfont.Font(family="Arial", size=10, weight="bold"),  # 20 -> 10
        fg="#FF5722",  # 주황색 글자
        bg='black',  # 투명 배경
        padx=6,
        pady=3
    )
    label.pack()
    
    # 카운트다운 변수
    countdown_value = [seconds]
    stop_flag = [False]
    
    def update_position():
        """마우스 위치를 실시간으로 따라감 (다중 모니터 지원)"""
        if stop_flag[0]:
            return
            
        try:
            cursor_pos = win32api.GetCursorPos()
            
            # 현재 마우스가 있는 모니터 찾기
            current_monitor = find_monitor_for_point(cursor_pos[0], cursor_pos[1], monitors)
            
            if not current_monitor:
                return
            
            # 윈도우 크기 가져오기
            root.update_idletasks()
            window_width = root.winfo_reqwidth()
            window_height = root.winfo_reqheight()
            
            # 마우스 오른쪽에 배치
            x = cursor_pos[0] + 25
            y = cursor_pos[1]
            
            # 현재 모니터 범위 내에서 위치 조정
            if x + window_width > current_monitor['right']:
                x = cursor_pos[0] - window_width - 5  # 마우스 왼쪽으로
            
            if x < current_monitor['left']:
                x = current_monitor['left'] + 5
            
            if y < current_monitor['top']:
                y = current_monitor['top'] + 5
            
            if y + window_height > current_monitor['bottom']:
                y = current_monitor['bottom'] - window_height - 5
            
            root.geometry(f"+{x}+{y}")
            
            # 50ms마다 위치 업데이트
            if not stop_flag[0]:
                root.after(50, update_position)
        except Exception as e:
            print(f"위치 업데이트 오류: {e}")
    
    def update_countdown():
        """카운트다운 값을 1초마다 업데이트"""
        if countdown_value[0] > 0:
            label.config(text=str(countdown_value[0]))
            print(f"  카운트: {countdown_value[0]}")
            countdown_value[0] -= 1
            root.after(1000, update_countdown)
        else:
            print("  카운트다운 완료 - 윈도우 닫기")
            stop_flag[0] = True
            root.after(100, root.destroy)
    
    # 초기 위치 설정
    cursor_pos = win32api.GetCursorPos()
    current_monitor = find_monitor_for_point(cursor_pos[0], cursor_pos[1], monitors)
    
    if current_monitor:
        x = cursor_pos[0] + 25
        y = cursor_pos[1]
        
        # 현재 모니터 범위 내로 제한
        root.update()
        window_width = root.winfo_reqwidth()
        window_height = root.winfo_reqheight()
        
        if x + window_width > current_monitor['right']:
            x = current_monitor['right'] - window_width - 5
        if x < current_monitor['left']:
            x = current_monitor['left'] + 5
        if y < current_monitor['top']:
            y = current_monitor['top'] + 5
        if y + window_height > current_monitor['bottom']:
            y = current_monitor['bottom'] - window_height - 5
        
        # 윈도우 표시
        root.geometry(f"+{x}+{y}")
        root.lift()
        root.focus_force()
        
        print(f"윈도우 생성 완료 - 위치: ({x}, {y}), 크기: {window_width}x{window_height}")
        print(f"현재 모니터: ({current_monitor['left']}, {current_monitor['top']}) ~ ({current_monitor['right']}, {current_monitor['bottom']})")
    
    # 카운트다운 시작
    update_countdown()
    
    # 위치 추적 시작
    update_position()
    
    # 메인 루프 실행
    root.mainloop()


if __name__ == "__main__":
    seconds = 3
    if len(sys.argv) > 1:
        try:
            seconds = int(sys.argv[1])
        except:
            pass
    
    print(f"\n=== 카운트다운 시작: {seconds}초 ===")
    print("마우스를 움직여보세요! (다중 모니터 지원)")
    print("-" * 40)
    show_countdown(seconds)
    print("-" * 40)
    print("=== 카운트다운 종료 ===\n")
