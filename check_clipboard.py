# -*- coding: utf-8 -*-
"""
클립보드 내용 확인 및 초기화
"""
import win32clipboard
import win32con

print("="*60)
print("클립보드 내용 확인 중...")
print("="*60)

try:
    win32clipboard.OpenClipboard()
    
    # 사용 가능한 모든 포맷 확인
    formats = []
    format_id = 0
    while True:
        format_id = win32clipboard.EnumClipboardFormats(format_id)
        if format_id == 0:
            break
        try:
            format_name = win32clipboard.GetClipboardFormatName(format_id)
            formats.append((format_id, format_name))
        except:
            formats.append((format_id, f"[표준 포맷: {format_id}]"))
    
    print(f"\n현재 클립보드에 있는 데이터 포맷:")
    for fmt_id, fmt_name in formats:
        print(f"  - {fmt_name} (ID: {fmt_id})")
    
    # 파일 목록이 있는지 확인 (CF_HDROP = 15)
    if win32clipboard.IsClipboardFormatAvailable(win32con.CF_HDROP):
        print("\n[경고] 클립보드에 파일 목록이 저장되어 있습니다!")
        try:
            files = win32clipboard.GetClipboardData(win32con.CF_HDROP)
            print(f"  파일 개수: {len(files)}")
            for i, file in enumerate(files, 1):
                print(f"  {i}. {file}")
        except:
            pass
    
    # 텍스트 확인
    if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
        text = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
        print(f"\n[정보] 클립보드 텍스트 내용:")
        print(f"  {text[:200]}...")
    
    win32clipboard.CloseClipboard()
    
    # 클립보드를 텍스트로 초기화
    print("\n" + "="*60)
    print("클립보드를 텍스트로 초기화합니다...")
    print("="*60)
    
    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    
    # 간단한 텍스트만 설정
    simple_text = "복사 테스트"
    win32clipboard.SetClipboardText(simple_text, win32con.CF_UNICODETEXT)
    
    win32clipboard.CloseClipboard()
    
    print(f"[완료] 클립보드를 초기화했습니다: '{simple_text}'")
    print("이제 Ctrl+V를 눌러보세요. 텍스트만 붙여넣기 됩니다.")
    print("="*60)
    
except Exception as e:
    print(f"\n[오류] {e}")
    import traceback
    traceback.print_exc()
    try:
        win32clipboard.CloseClipboard()
    except:
        pass
