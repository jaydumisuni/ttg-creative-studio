#define MyAppName "TheTechGuy Image Editor"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "TheTechGuy"
#define MyAppExeName "TheTechGuy Image Editor.exe"
#define VCRuntimeRegKey "SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64"

[Setup]
AppId={{B7F0A0C2-7A47-4E45-A2A6-6B918A90AA10}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=installer
OutputBaseFilename=TheTechGuy Image Editor Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
SetupIconFile=build_icon.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "dist\TheTechGuy Image Editor.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\TheTechGuy Image Editor Backend.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "models\*.onnx"; DestDir: "{app}\models"; Flags: ignoreversion
Source: "prereqs\vc_redist.x64.exe"; Flags: dontcopy

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: checkedonce

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent; Check: CanLaunchApp

[Code]
var
  VCRuntimeRestartRequired: Boolean;

function IsVCRuntimeInstalled: Boolean;
var
  Installed: Cardinal;
begin
  Result := False;
  if RegQueryDWordValue(HKLM64, '{#VCRuntimeRegKey}', 'Installed', Installed) then
    Result := Installed = 1;
end;

function InstallVCRuntime(var NeedsRestart: Boolean): String;
var
  ResultCode: Integer;
  InstallerPath: string;
begin
  Result := '';
  ExtractTemporaryFile('vc_redist.x64.exe');
  InstallerPath := ExpandConstant('{tmp}\vc_redist.x64.exe');

  WizardForm.StatusLabel.Caption := 'Installing Microsoft Visual C++ runtime...';
  WizardForm.ProgressGauge.Style := npbstMarquee;

  if not Exec(
    InstallerPath,
    '/install /quiet /norestart',
    '',
    SW_HIDE,
    ewWaitUntilTerminated,
    ResultCode
  ) then
  begin
    Result := 'Could not start the Microsoft Visual C++ runtime installer.';
    Exit;
  end;

  if (ResultCode <> 0) and (ResultCode <> 1638) and (ResultCode <> 1641) and (ResultCode <> 3010) then
  begin
    Result := 'Microsoft Visual C++ runtime installation failed with exit code ' + IntToStr(ResultCode) + '.';
    Exit;
  end;

  if (ResultCode = 1641) or (ResultCode = 3010) then
  begin
    VCRuntimeRestartRequired := True;
    NeedsRestart := True;
  end;

  WizardForm.ProgressGauge.Style := npbstNormal;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  Result := '';

  if not IsVCRuntimeInstalled then
    Result := InstallVCRuntime(NeedsRestart);
end;

function CanLaunchApp: Boolean;
begin
  Result := not VCRuntimeRestartRequired;
end;
