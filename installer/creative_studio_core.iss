#define MyAppName "TTG Creative Studio"
#define MyAppVersion "0.1.0-alpha"
#define MyAppPublisher "THETECHGUY DIGITAL SOLUTIONS"
#define MyAppExeName "TTG Creative Studio.exe"

[Setup]
AppId={{A4F4D8B6-9D72-4C72-8C4E-TTGCREATIVESTUDIO}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\TTG Creative Studio
DefaultGroupName={#MyAppName}
OutputDir=dist\installer
OutputBaseFilename=TTG-Creative-Studio-Core-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64

[Files]
Source: "..\dist\TTG Creative Studio\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
