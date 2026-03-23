"""
마우스 포인터 옆에 실시간 카운트다운을 표시하는 독립 프로세스
유휴 대기 중 남은 시간을 실시간으로 표시
"""
import tkinter as tk
from tkinter import font as tkfont
import win32api
import sys
import time
import os


def get_monitor_info():
    """모든 모니터의 정보를 가져옴"""
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
        ctypes.windll.user32.EnumDisplayMonitors(None, None, ctypes.WINFUNCTYPE(
            ctypes.c_int, ctypes.c_ulong, ctypes.c_ulong, ctypes.POINTER(ctypes.c_long), ctypes.c_double
        )(callback), 0)
    except:
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
    """특정 좌표가 속한 모니터 찾기"""
    for monitor in monitors:
        if (monitor['left'] <= x < monitor['right'] and 
            monitor['top'] <= y < monitor['bottom']):
            return monitor
    return monitors[0] if monitors else None


def show_realtime_countdown(duration_seconds):
    """
    실시간 카운트다운 표시 (남은 시간을 계속 업데이트)
    """
    monitors = get_monitor_info()
    
    # Tkinter 윈도우 생성
    root = tk.Tk()
    root.attributes('-topmost', True)
    root.overrideredirect(True)
    root.attributes('-transparentcolor', 'black')
    root.config(bg='black')
    
    # 라벨 생성
    label = tk.Label(
        root,
        text=f"{duration_seconds:.1f}",
        font=tkfont.Font(family="Arial", size=10, weight="bold"),
        fg="#FF5722",
        bg='black',
        padx=6,
        pady=3
    )
    label.pack()
    
    # 시작 시간 기록
    start_time = time.time()
    stop_flag = [False]
    
    def update_position():
        """마우스 위치를 따라감"""
        if stop_flag[0]:
            return
        
        try:
            cursor_pos = win32api.GetCursorPos()
            current_monitor = find_monitor_for_point(cursor_pos[0], cursor_pos[1], monitors)
            
            if current_monitor:
                root.update_idletasks()
                window_width = root.winfo_reqwidth()
                window_height = root.winfo_reqheight()
                
                x = cursor_pos[0] + 25
                y = cursor_pos[1]
                
                if x + window_width > current_monitor['right']:
                    x = cursor_pos[0] - window_width - 5
                if x < current_monitor['left']:
                    x = current_monitor['left'] + 5
                if y < current_monitor['top']:
                    y = current_monitor['top'] + 5
                if y + window_height > current_monitor['bottom']:
                    y = current_monitor['bottom'] - window_height - 5
                
                root.geometry(f"+{x}+{y}")
            
            if not stop_flag[0]:
                root.after(50, update_position)
        except:
            pass
    
    def update_countdown():
        """남은 시간을 실시간으로 업데이트"""
        elapsed = time.time() - start_time
        remaining = duration_seconds - elapsed
        
        if remaining > 0:
            label.config(text=f"{remaining:.1f}")
            root.after(100, update_countdown)  # 100ms마다 업데이트
        else:
            stop_flag[0] = True
            root.after(100, root.destroy)
    
    # 초기 위치 설정
    cursor_pos = win32api.GetCursorPos()
    current_monitor = find_monitor_for_point(cursor_pos[0], cursor_pos[1], monitors)
    
    if current_monitor:
        root.update()
        x = cursor_pos[0] + 25
        y = cursor_pos[1]
        root.geometry(f"+{x}+{y}")
        root.lift()
    
    # 업데이트 시작
    update_countdown()
    update_position()
    
    # 메인 루프 실행
    root.mainloop()


if __name__ == "__main__":
    duration = 3.0
    if len(sys.argv) > 1:
        try:
            duration = float(sys.argv[1])
        except:
            pass
    
    show_realtime_countdown(duration)
