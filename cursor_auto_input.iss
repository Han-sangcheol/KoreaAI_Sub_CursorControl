; [파일 기능] Inno Setup 6용 설치 스크립트
; - PyInstaller 산출물(dist\cursor_auto_input\) 전체 + 설정용 파일을 설치
; - 시작 메뉴/선택 시 바탕 화면 바로가기, 작업 디렉터리 = 설치 폴더(콘솔·파일 경로 일치)
; 사전 조건: 프로젝트 루트에서 pyinstaller --noconfirm cursor_auto_input.spec 실행 후 ISCC로 컴파일

#define MyAppName "Cursor 프롬프트 자동 입력"
#define MyAppNameEn "CursorAutoInput"
#define MyAppVersion "1.0.0"
#define MyAppExeName "cursor_auto_input.exe"

[Setup]
AppId={{8F3E2B1A-5C4D-4E6F-9A0B-1C2D3E4F5A6B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
DefaultDirName={autopf64}\{#MyAppNameEn}
DefaultGroupName={#MyAppName}
OutputDir=installer_output
OutputBaseFilename=CursorAutoInput_Setup_{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"

[Tasks]
Name: "desktopicon"; Description: "바탕 화면에 바로가기 만들기"; GroupDescription: "추가 작업:"; Flags: unchecked

[Files]
Source: "dist\cursor_auto_input\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "roll.txt"; DestDir: "{app}"; Flags: onlyifdoesntexist
Source: "status.template.json"; DestDir: "{app}"; DestName: "status.json"; Flags: onlyifdoesntexist
Source: "input_example.txt"; DestDir: "{app}"; Flags: onlyifdoesntexist

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "설치 후 프로그램 실행"; Flags: nowait postinstall skipifsilent

[Code]
function InitializeSetup: Boolean;
begin
  Result := DirExists(ExpandConstant('{src}\dist\cursor_auto_input'));
  if not Result then
    MsgBox('dist\cursor_auto_input 폴더가 없습니다.'#13#10'먼저 프로젝트 루트에서 다음을 실행하세요:'#13#10'  pyinstaller --noconfirm cursor_auto_input.spec', mbError, MB_OK);
end;
