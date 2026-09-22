; OpenObstrator Windows 安装包脚本 (Inno Setup 6)
;
; 编译:  scripts\build_installer.bat
; 或:    "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" scripts\installer.iss
;
; 先决条件: 先跑 build.bat（或 pyinstaller --clean -y build.spec）生成
;           dist\OpenObstrator.exe（onefile 产物）

#define MyAppName "OpenObstrator"
#define MyAppExeName "OpenObstrator.exe"
#define MyAppVersion Trim(FileRead(FileOpen("..\VERSION")))
#define MyBuildDir "..\dist"
#define MyOutputDir "..\dist\installer"

[Setup]
; AppId 是升级识别的唯一标识，一旦发布不要再改，否则旧版本不会被覆盖安装
AppId={{3E9A1C74-6B25-4D8F-A0C3-8F7B2E5D41A9}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppName}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
; 默认按用户安装（不弹 UAC），用户仍可在安装界面切成全机器安装
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir={#MyOutputDir}
OutputBaseFilename=OpenObstratorSetup-{#MyAppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
; 升级时自动关闭正在运行的程序（走 Restart Manager），否则 exe 被占用会覆盖失败
CloseApplications=yes
RestartApplications=no
; 有 icon 就用（需要真正的 .ico，不是 .png）
#ifexist "openobstrator.ico"
SetupIconFile=openobstrator.ico
#endif

; 中文语言包（MIT，非官方翻译）。文件缺失时自动回退到英文，不会编译失败。
#ifexist "ChineseSimplified.isl"
[Languages]
Name: "chinesesimplified"; MessagesFile: "ChineseSimplified.isl"
#endif

[Files]
; onefile 产物
Source: "{#MyBuildDir}\OpenObstrator.exe"; DestDir: "{app}"; Flags: ignoreversion
; 默认配置：只在首次安装时落；升级不覆盖用户改过的
Source: "config.default.yaml"; DestDir: "{app}\data"; DestName: "config.yaml"; Flags: onlyifdoesntexist
; 说明文档
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\卸载 {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加任务:"

[Run]
; 去掉 skipifsilent：自更新是静默安装，装完必须由安装器把新版本拉起来 ——
; 这正是「更新完自动重启」那一步。交互安装时它同时是完成页的"立即启动"勾选框。
Filename: "{app}\{#MyAppExeName}"; Description: "立即启动 {#MyAppName}"; Flags: nowait postinstall

; 说明：运行期数据（data\ 下的 registry.json、downloads\ 等）不由安装程序创建，
; 卸载时不会被动；只有本安装包落下去的 config.yaml(onlyifdoesntexist) 会随卸载移除。
