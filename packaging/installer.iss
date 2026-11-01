; Inno Setup script for the YT-DLP Studio Windows installer.
;
; Build (CI does this after PyInstaller and the bundle check):
;   ISCC.exe /DAppVersion=0.3.0 /DAppVersionNumeric=0.3.0.0 packaging\installer.iss
; Output: dist\YT-DLP-Studio-Setup-<version>.exe
;
; Design rules:
; - One payload. The installer installs the same one-file dist\yt-dlp-studio.exe
;   that the portable ZIP ships, so the two downloads cannot drift.
; - Per user, no admin: PrivilegesRequired=lowest and an install folder under
;   %LOCALAPPDATA%\Programs. No UAC prompt.
; - AppId is the identity Windows upgrades against. NEVER change it, or the next
;   version installs beside the old one instead of over it.
; - Uninstall never removes user data. Settings, history, logs and crash reports
;   live in %APPDATA%\YT-DLP Studio, outside {app}. Deleting them is opt-in: a
;   Yes/No box that defaults to No, or /PURGEDATA=yes for unattended use.
; - In-place update: the app's updater runs this installer with
;   /SILENT /LAUNCH=yes; it upgrades over the running copy and starts the app
;   again when it is done.

#ifndef AppVersion
  #error Pass the version: ISCC /DAppVersion=x.y.z /DAppVersionNumeric=x.y.z.0
#endif
#ifndef AppVersionNumeric
  #error Pass the numeric version: ISCC /DAppVersionNumeric=x.y.z.0
#endif
#ifndef SourceExe
  #define SourceExe "..\dist\yt-dlp-studio.exe"
#endif

#define AppName "YT-DLP Studio"
#define AppExeName "yt-dlp-studio.exe"
; Must match SetCurrentProcessExplicitAppUserModelID in src/app.py, or the
; taskbar shows a second, ungrouped button.
#define AppUserModelID "NX1X.YTDLPStudio"

[Setup]
AppId={{A55A4BB4-4BB7-48A4-970B-C0A9E9545BC2}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=NX1X
AppPublisherURL=https://github.com/NX1X/yt-dlp-studio
AppSupportURL=https://github.com/NX1X/yt-dlp-studio/issues
AppUpdatesURL=https://github.com/NX1X/yt-dlp-studio/releases
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
DisableDirPage=auto
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=..\dist
OutputBaseFilename=YT-DLP-Studio-Setup-{#AppVersion}
SetupIconFile=..\src\resources\icons\favicon.ico
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; Close a running copy so the update can replace the EXE. The app is started
; again by the [Run] entry below, not by the Restart Manager.
CloseApplications=force
RestartApplications=no
VersionInfoVersion={#AppVersionNumeric}
VersionInfoProductVersion={#AppVersionNumeric}
VersionInfoProductTextVersion={#AppVersion}
VersionInfoCompany=NX1X
VersionInfoDescription={#AppName} Setup

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "hebrew"; MessagesFile: "compiler:Languages\Hebrew.isl"

[CustomMessages]
english.PurgeDataPrompt=Also delete your YT-DLP Studio settings, download history and logs?%n%n%1%n%nYour downloaded videos are never deleted.
hebrew.PurgeDataPrompt=למחוק גם את ההגדרות, היסטוריית ההורדות והיומנים של YT-DLP Studio?%n%n%1%n%nהסרטונים שהורדת לא יימחקו לעולם.

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#SourceExe}"; DestDir: "{app}"; DestName: "{#AppExeName}"; Flags: ignoreversion

[INI]
; Marker the app reads to know it runs from an installed copy, so its updater
; uses this installer instead of downloading a second portable EXE.
Filename: "{app}\install.ini"; Section: "install"; Key: "kind"; String: "inno"; Flags: uninsdeletesection
Filename: "{app}\install.ini"; Section: "install"; Key: "version"; String: "{#AppVersion}"; Flags: uninsdeletesection

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExeName}"; AppUserModelID: "{#AppUserModelID}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; AppUserModelID: "{#AppUserModelID}"; Tasks: desktopicon

[Run]
; Interactive install: offer to start the app on the last page.
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
; Silent in-place update from the app (/SILENT /LAUNCH=yes): start it again.
Filename: "{app}\{#AppExeName}"; Flags: nowait; Check: LaunchAfterSilentUpdate

[UninstallDelete]
; Only files this installer created. User data in %APPDATA% is handled in
; CurUninstallStepChanged below and is kept unless the user asks.
Type: files; Name: "{app}\install.ini"
Type: dirifempty; Name: "{app}"

[Code]
function SetEnvironmentVariable(lpName, lpValue: String): Boolean;
  external 'SetEnvironmentVariableW@kernel32.dll stdcall';

function InitializeSetup: Boolean;
begin
  // An update started from the app (0.3.0 and 0.3.1 included) inherits the
  // app's PyInstaller variables, which point at its deleted temp folder. The
  // app this installer starts would then fail with "Failed to load Python
  // DLL". This variable makes it ignore them.
  SetEnvironmentVariable('PYINSTALLER_RESET_ENVIRONMENT', '1');
  Result := True;
end;

function LaunchAfterSilentUpdate: Boolean;
begin
  Result := WizardSilent and (ExpandConstant('{param:LAUNCH|no}') = 'yes');
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DataDir: String;
  Purge: Boolean;
begin
  if CurUninstallStep <> usPostUninstall then
    exit;
  DataDir := ExpandConstant('{userappdata}\{#AppName}');
  if not DirExists(DataDir) then
    exit;
  Purge := ExpandConstant('{param:PURGEDATA|no}') = 'yes';
  if (not Purge) and (not UninstallSilent) then
    Purge := MsgBox(FmtMessage(CustomMessage('PurgeDataPrompt'), [DataDir]),
      mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES;
  if Purge then
    DelTree(DataDir, True, True, True);
end;
