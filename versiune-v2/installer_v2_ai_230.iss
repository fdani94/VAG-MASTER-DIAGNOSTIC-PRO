#define MyAppName "KID Diagnostic V2"
#define MyAppVersion "2.3.0"
#define MyAppPublisher "KID Diagnostic"
#define MyAppExeName "KID-Diagnostic-V2-AI.exe"
#define MyAppIconName "kid_diagnostic_v2.ico"

[Setup]
AppId={{6EB61A75-797C-46EE-B377-8063AB0D80DA}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\KID Diagnostic V2
DefaultGroupName=KID Diagnostic V2
DisableProgramGroupPage=yes
OutputDir=dist-v2-installer
OutputBaseFilename=KID-Diagnostic-V2-AI-v2.3.0-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
SetupIconFile=..\kid_diagnostic_v2.ico
UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppIconName}
CloseApplications=yes
RestartApplications=no

[Files]
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\kid_diagnostic_v2.ico"; DestDir: "{app}"; DestName: "{#MyAppIconName}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\KID Diagnostic V2"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppIconName}"
Name: "{autodesktop}\KID Diagnostic V2"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppIconName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Creează scurtătură KID Diagnostic V2 pe Desktop"; GroupDescription: "Scurtături suplimentare:"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Pornește KID Diagnostic V2 v2.3.0"; Flags: nowait postinstall skipifsilent
