; ============================================================================
;  GrainScan Windows installer (Inno Setup 6.x)
;
;  Build:
;     "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" GrainScan.iss
;  or run build_installer.bat which handles everything end-to-end.
;
;  Output:
;     installer_output\GrainScan-Setup-<version>.exe
;
;  By default the installer drops the application into
;  %LOCALAPPDATA%\Programs\GrainScan, i.e. a per-user, user-writable location
;  (the same pattern used by Discord, GitHub Desktop, VS Code User Setup, …)
;  so that GrainScan can freely create report\, runs\, analytics_exports\
;  and dataset\ folders next to the executable without needing admin rights.
;  The user can override the install directory at the wizard's Select
;  Destination step (e.g. they may pick C:\GrainScan or a portable USB drive).
; ============================================================================

#define MyAppName          "GrainScan"
#define MyAppVersion       "1.0.0"
#define MyAppPublisher     "GrainScan"
#define MyAppExeName       "GrainScan.exe"
#define MyAppExeDescription "Automated Rice Quality Inspection"

; Absolute path to the PyInstaller output. Override via /DBundleDir=... on the
; ISCC command line if you build to a different location.
#ifndef BundleDir
  #define BundleDir "F:\GrainScanBuild\dist\GrainScan"
#endif

; Absolute path to the project source root (used to grab the original GUI
; icons + bundled model weights at full resolution).
#ifndef SourceRoot
  #define SourceRoot "G:\backup\Python\Rice"
#endif

[Setup]
AppId={{8F9C7C72-7E9C-4F7C-B19E-9F1B3C2A8D55}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppMutex=Global\GrainScan.AppInstance
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppExeDescription}

; Per-user install (no admin required) into %LOCALAPPDATA%\Programs\GrainScan
DefaultDirName={userpf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
UsePreviousAppDir=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog commandline

ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

Compression=lzma2/max
SolidCompression=yes
LZMAUseSeparateProcess=yes
LZMANumBlockThreads=4
DiskSpanning=no
WizardStyle=modern
ShowLanguageDialog=no
DisableWelcomePage=no
DisableReadyPage=no
DisableFinishedPage=no
AllowNoIcons=yes
SetupLogging=yes

OutputDir={#SourceRoot}\installer_output
OutputBaseFilename={#MyAppName}-Setup-{#MyAppVersion}
UninstallDisplayName={#MyAppName} {#MyAppVersion}
UninstallDisplayIcon={app}\{#MyAppExeName}
SetupIconFile={#SourceRoot}\GUI\logo4.ico
CloseApplications=force
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon";   Description: "{cm:CreateDesktopIcon}"; \
    GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; \
    GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; --- PyInstaller bundle ---------------------------------------------------
;
; The entire dist\GrainScan\ tree (GrainScan.exe + _internal\) is copied
; verbatim. The recursesubdirs+createallsubdirs flags ensure deeply nested
; _internal\torch\... DLLs land in the right place.
Source: "{#BundleDir}\*"; \
    DestDir: "{app}"; \
    Flags: ignoreversion recursesubdirs createallsubdirs

; --- GUI assets, at the application root ---------------------------------
;
; We deliberately copy the original GUI icons next to GrainScan.exe (instead
; of leaving them only inside _internal\GUI). This is what the GUI's
; relative paths ("GUI/icon2.png", "GUI/logo1.png", "GUI/scan.png", …)
; expect — and avoids depending on the launcher's first-run materialisation
; step.
Source: "{#SourceRoot}\GUI\*"; \
    DestDir: "{app}\GUI"; \
    Flags: ignoreversion recursesubdirs createallsubdirs

; --- Model weights, at the application root ------------------------------
;
; Same story for dataset/ — copy the default models out of _internal so
; test_main.get_model_path()'s relative-path resolution works.
Source: "{#SourceRoot}\dataset\weightsV9.1Object.pt"; \
    DestDir: "{app}\dataset"; Flags: ignoreversion skipifsourcedoesntexist
Source: "{#SourceRoot}\dataset\weightsV9highres.pt"; \
    DestDir: "{app}\dataset"; Flags: ignoreversion skipifsourcedoesntexist

; --- Config template -----------------------------------------------------
;
; We don't ship the developer's config.json verbatim (it has hard-coded
; C:\Users\Neji\... paths). Instead we write a fresh one with relative
; paths during [Code].InitializeSetup / via the launcher's self-heal logic.
Source: "{#SourceRoot}\docs\USER_MANUAL.txt"; \
    DestDir: "{app}"; DestName: "GrainScan_User_Manual.txt"; \
    Flags: ignoreversion skipifsourcedoesntexist

[Dirs]
; Pre-create writable subdirectories next to the executable so any user can
; immediately write scan reports / training runs / analytics CSVs without
; permission issues. The "uninsneveruninstall" flag preserves them — and the
; user's scan history — across upgrades and uninstalls.
Name: "{app}\report";              Permissions: users-modify; Flags: uninsneveruninstall
Name: "{app}\runs";                Permissions: users-modify; Flags: uninsneveruninstall
Name: "{app}\analytics_exports";   Permissions: users-modify; Flags: uninsneveruninstall
Name: "{app}\dataset";             Permissions: users-modify; Flags: uninsneveruninstall

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; \
    WorkingDir: "{app}"; Comment: "{#MyAppExeDescription}"
Name: "{group}\{#MyAppName} User Manual"; Filename: "{app}\GrainScan_User_Manual.txt"; \
    WorkingDir: "{app}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"

Name: "{userdesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; \
    WorkingDir: "{app}"; Comment: "{#MyAppExeDescription}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; \
    Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\{#MyAppExeName}"; \
    Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; \
    Flags: nowait postinstall skipifsilent; \
    WorkingDir: "{app}"

[UninstallDelete]
; Tidy up runtime caches PyInstaller might leave inside _internal\ — without
; touching the user's report\, runs\, analytics_exports\, dataset\ folders,
; which were marked uninsneveruninstall above.
Type: filesandordirs; Name: "{app}\_internal\__pycache__"

[Code]
const
  CONFIG_TEMPLATE =
    '{' + #13#10 +
    '  "model_path": "dataset/weightsV9highres.pt",' + #13#10 +
    '  "default_model_path": "dataset/weightsV9highres.pt"' + #13#10 +
    '}' + #13#10;

procedure CurStepChanged(CurStep: TSetupStep);
var
  CfgPath: String;
begin
  // After files are extracted, drop a fresh config.json with paths that
  // resolve relative to {app}. We do this in [Code] rather than [Files]
  // because we don't want to overwrite a user's existing customised config
  // when they reinstall / upgrade.
  if CurStep = ssPostInstall then
  begin
    CfgPath := ExpandConstant('{app}\config.json');
    if not FileExists(CfgPath) then
    begin
      if not SaveStringToFile(CfgPath, CONFIG_TEMPLATE, False) then
        MsgBox('Warning: could not write config.json. The app will create one on first launch.',
               mbInformation, MB_OK);
    end;
  end;
end;

function InitializeSetup(): Boolean;
begin
  Result := True;
end;
