"""
카운트다운 오버레이 기능 테스트 스크립트
- 마우스 포인터 옆에 3-2-1 카운트다운이 표시되는지 확인
"""

import time
import tkinter as tk
from tkinter import font as tkfont
import win32api
import threading
import sys
import io

# UTF-8 출력 설정
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


class CountdownOverlay:
    """
    마우스 포인터 옆에 카운트다운을 표시하는 투명 오버레이 윈도우
    """
    def __init__(self):
        self.window = None
        self.label = None
        self.countdown_value = 3
        
    def show_countdown(self, seconds=3):
        """
        카운트다운을 표시 (메인 스레드에서 실행)
        
        Args:
            seconds: 카운트다운 시작 숫자 (기본 3)
        """
        try:
            self.countdown_value = seconds
            
            # tkinter 윈도우 생성
            self.window = tk.Tk()
            
            # 윈도우 설정: 투명도, 항상 위, 타이틀바 없음
            self.window.attributes('-alpha', 0.85)
            self.window.attributes('-topmost', True)
            self.window.overrideredirect(True)
            
            # 라벨 생성
            self.label = tk.Label(
                self.window,
                text=str(self.countdown_value),
                font=tkfont.Font(family="Arial", size=48, weight="bold"),
                fg="white",
                bg="#FF5722",
                padx=20,
                pady=10
            )
            self.label.pack()
            
            # 마우스 위치 가져오기
            cursor_pos = win32api.GetCursorPos()
            x, y = cursor_pos[0] + 30, cursor_pos[1] + 30
            
            # 윈도우 크기 업데이트
            self.window.update_idletasks()
            width = self.window.winfo_width()
            height = self.window.winfo_height()
            
            # 화면 경계 체크
            screen_width = self.window.winfo_screenwidth()
            screen_height = self.window.winfo_screenheight()
            
            if x + width > screen_width:
                x = screen_width - width - 10
            if y + height > screen_height:
                y = screen_height - height - 10
            
            # 윈도우 위치 설정
            self.window.geometry(f"+{x}+{y}")
            
            # 카운트다운 업데이트 시작
            self._update_countdown()
            
            # 메인 루프 실행
            self.window.mainloop()
            
        except Exception as e:
            print(f"  [WARNING] 카운트다운 오버레이 오류: {e}")
            if self.window:
                try:
                    self.window.destroy()
                except:
                    pass
    
    def _update_countdown(self):
        """
        카운트다운 값을 1초마다 업데이트
        """
        if self.countdown_value > 0:
            self.label.config(text=str(self.countdown_value))
            self.countdown_value -= 1
            self.window.after(1000, self._update_countdown)
        else:
            self.window.destroy()
    
    def hide(self):
        """
        카운트다운 윈도우 강제 닫기
        """
        if self.window:
            try:
                self.window.destroy()
            except:
                pass


def test_countdown():
    """
    카운트다운 오버레이 테스트
    """
    print("=" * 60)
    print("카운트다운 오버레이 테스트")
    print("=" * 60)
    print("\n테스트 시나리오:")
    print("1. 5초 후 마우스 포인터 옆에 3-2-1 카운트다운 표시")
    print("2. 카운트다운이 끝나면 자동으로 사라짐")
    print("\n준비: 마우스를 원하는 위치에 놓으세요...")
    
    # 5초 대기
    for i in range(5, 0, -1):
        print(f"  {i}초 후 카운트다운 시작...", end='\r')
        time.sleep(1)
    
    print("\n\n[OK] 카운트다운 시작!")
    print("     (마우스 포인터 옆에 3-2-1 카운트다운이 표시됩니다)")
    
    # 카운트다운 표시
    overlay = CountdownOverlay()
    overlay.show_countdown(seconds=3)
    
    print("\n[OK] 카운트다운 완료!")
    print("\n" + "=" * 60)
    print("테스트 완료!")
    print("=" * 60)


if __name__ == "__main__":
    test_countdown()
