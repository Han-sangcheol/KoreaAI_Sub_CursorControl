# Cursor 프롬프트 입력창 자동화

Cursor IDE의 프롬프트 입력창에 `status.json`과 `roll.txt` 파일의 내용을 자동으로 합쳐서 입력하고 엔터를 치는 프로그램입니다.

## 특징

- **백그라운드 입력**: Windows 메시지를 사용하여 사용자가 다른 작업을 하고 있어도 방해받지 않음
- **안전한 동작**: 지정된 Cursor 윈도우에만 입력하므로 다른 프로그램에 영향 없음
- **사용자 입력 감지**: 키보드나 마우스 입력이 3초간 없을 때까지 자동 대기하여 안정적인 붙여넣기 실행
- `status.json`과 `roll.txt` 파일을 모니터링
- 두 파일 중 하나라도 변경되면 자동으로 두 파일의 내용을 합쳐서 Cursor에 입력
- 입력 후 자동으로 엔터 키 전송
- **여러 개의 Cursor 인스턴스가 실행 중일 때 선택하여 입력 가능**
- PyWinAuto와 Windows API를 사용한 안정적인 자동화

## 설치 방법

```bash
pip install -r requirements.txt
```

## 사용 방법

1. Cursor IDE를 실행합니다 (여러 개 실행 가능)
2. 프로그램을 실행합니다:

```bash
python cursor_auto_input.py
```

3. 여러 개의 Cursor 인스턴스가 실행 중이면 목록이 표시됩니다
4. 입력할 Cursor 윈도우를 선택합니다
5. 프로그램이 `status.json`과 `roll.txt` 파일을 모니터링합니다
6. 두 파일 중 하나라도 수정하면 자동으로 두 파일의 내용이 합쳐져서 Cursor에 입력됩니다

## 동작 원리

1. 프로그램 시작 시 현재 디렉토리의 `status.json`과 `roll.txt` 파일을 모니터링 대상으로 설정
2. 실행 중인 모든 Cursor 윈도우를 검색합니다
3. 여러 개가 있으면 사용자가 선택할 수 있도록 목록을 표시합니다
4. 선택된 Cursor 윈도우를 기억합니다
5. 두 파일을 주기적으로 모니터링합니다 (1초 간격)
6. 두 파일 중 하나라도 변경되면:
   - 사용자의 키보드/마우스 입력이 3초간 없을 때까지 대기합니다 (붙여넣기 실패 방지)
   - `status.json`의 내용을 읽어옵니다
   - `roll.txt`의 내용을 읽어옵니다
   - 두 내용을 합쳐서 하나의 텍스트로 만듭니다
   - 텍스트를 클립보드에 복사합니다
7. 선택된 Cursor 윈도우를 활성화하고 프롬프트 입력창에 텍스트를 붙여넣습니다
8. 엔터 키를 자동으로 전송합니다

## 입력 형식

두 파일의 내용은 다음과 같은 형식으로 합쳐집니다:

```
=== status.json ===
{status.json 파일의 내용}

=== roll.txt ===
{roll.txt 파일의 내용}
```

## 테스트 방법

### 방법 1: 자동 테스트

```bash
# 터미널 1: 메인 프로그램 실행
python cursor_auto_input.py

# 터미널 2: 테스트 스크립트 실행 (안내에 따라 진행)
python test_input.py
```

### 방법 2: 수동 테스트

```bash
# 1. 프로그램 실행
python cursor_auto_input.py

# 2. 다른 터미널이나 에디터에서 status.json 또는 roll.txt 파일 수정
# 3. 파일을 저장하면 자동으로 Cursor에 입력됨
```

### 테스트 예시

1. `status.json` 수정:

```json
{
  "status": "작업중",
  "progress": 50
}
```

2. `roll.txt` 수정:

```
코드 리뷰를 진행해주세요.
```

3. 두 파일 중 하나를 저장하면 자동으로 Cursor에 다음과 같이 입력됩니다:

```
=== status.json ===
{
  "status": "작업중",
  "progress": 50
}

=== roll.txt ===
코드 리뷰를 진행해주세요.
```

## 주의사항

- Cursor IDE가 실행 중이어야 합니다
- 여러 개의 Cursor 인스턴스가 있을 경우 프로그램 시작 시 선택합니다
- 프로그램은 백그라운드에서 계속 실행되며 `status.json`과 `roll.txt` 파일 변경을 감지합니다
- 파일 변경 감지 시 사용자가 키보드나 마우스를 사용 중이면 3초간 유휴 상태가 될 때까지 자동으로 대기합니다
- 종료하려면 `Ctrl+C`를 누르세요
- 두 파일 모두 UTF-8 인코딩을 권장합니다
- 프로그램을 실행한 디렉토리에 `status.json`과 `roll.txt` 파일이 있어야 합니다


## 빌드 및 설치 패키지 (Windows)

### 1) 실행 파일 폴더 만들기 (PyInstaller)

프로젝트 루트에서:

```powershell
Set-Location d:\my_project\cursor_control
pip install pyinstaller
pyinstaller --noconfirm cursor_auto_input.spec
```

산출물: `dist\cursor_auto_input\` (exe, `_internal` 포함 — 이 폴더는 분리하지 마세요.)

### 2) 설치형 Setup.exe 만들기 (Inno Setup 6)

1. [Inno Setup](https://jrsoftware.org/isdl.php) 6을 설치합니다.
2. 프로젝트 루트의 `cursor_auto_input.iss`를 **Inno Setup Compiler**로 열고 Compile(F9)합니다.
3. 결과: `installer_output\CursorAutoInput_Setup_1.0.0.exe` (버전은 `.iss`의 `MyAppVersion`과 동일)

설치 시 `Program Files` 아래 `CursorAutoInput`에 복사되며, 처음 설치할 때만 `status.json`(템플릿), `roll.txt`, `input_example.txt`가 없을 때만 배치됩니다. 이후 재설치 시 사용자가 수정한 파일은 덮어쓰지 않습니다.

시작 메뉴·(선택) 바탕 화면 바로가기의 **작업 폴더는 설치 디렉터리**로 지정되어 있어, `status.json`·`roll.txt`는 설치 폴더에서 편집하면 됩니다.
