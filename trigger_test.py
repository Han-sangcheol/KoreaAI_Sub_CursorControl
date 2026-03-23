"""
status.json 파일을 수정하여 카운트다운 테스트 트리거
"""
import json
import time

# status.json 파일 수정
with open('status.json', 'w', encoding='utf-8') as f:
    json.dump({
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "test": "카운트다운 테스트"
    }, f, ensure_ascii=False, indent=2)

print("status.json 파일이 수정되었습니다.")
print("이제 3초간 마우스/키보드를 사용하지 마세요!")
print("콘솔에 '>> 3 <<', '>> 2 <<', '>> 1 <<', '>> 시작! <<'이 표시됩니다.")
