#ifndef AppVersion
  #error AppVersion must be supplied by the release build
#endif
#ifndef BundleDir
  #error BundleDir must be supplied by the release build
#endif
#ifndef WindowsAssets
  #error WindowsAssets must be supplied by the release build
#endif
#ifndef OutputDir
  #error OutputDir must be supplied by the release build
#endif
#ifndef AppVersionMajor
  #error AppVersionMajor must be supplied by the release build
#endif
#ifndef AppVersionMinor
  #error AppVersionMinor must be supplied by the release build
#endif
#ifndef AppVersionPatch
  #error AppVersionPatch must be supplied by the release build
#endif

#define AppGuid "A6B2A61D-05B0-4CE7-85A3-C443B36D703B"

[Setup]
AppId={{{#AppGuid}}
AppName=PHASENØX
AppVerName=PHASENØX Desktop Core {#AppVersion}
AppVersion={#AppVersion}
AppMutex=PHASENOX.Desktop
DefaultDirName={localappdata}\Programs\PHASENOX
DefaultGroupName=PHASENØX
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UsePreviousAppDir=yes
UsePreviousGroup=yes
CloseApplications=yes
RestartApplications=no
ChangesEnvironment=no
UninstallDisplayIcon={app}\PHASENOX.exe
SetupIconFile={#WindowsAssets}\PHASENOX.ico
OutputDir={#OutputDir}
OutputBaseFilename=PHASENOX-Setup-{#AppVersion}-win-x64
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern dynamic
VersionInfoDescription=PHASENØX Desktop Core Installer
VersionInfoProductName=PHASENØX
VersionInfoProductVersion={#AppVersion}
VersionInfoVersion={#AppVersion}.0
VersionInfoOriginalFileName=PHASENOX-Setup-{#AppVersion}-win-x64.exe
SignedUninstaller=no

[Files]
Source: "{#BundleDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\PHASENØX"; Filename: "{app}\PHASENOX.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\PHASENØX"; Filename: "{app}\PHASENOX.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Run]
Filename: "{app}\PHASENOX.exe"; Description: "Launch PHASENØX"; Flags: nowait postinstall skipifsilent

[Code]
var
  DataDirPage: TInputDirWizardPage;
  ExistingPointerPage: TInputOptionWizardPage;
  SameDriveCheck: TNewCheckBox;
  ExistingPointer: Boolean;

function CanonicalStateDir(): String;
begin
  Result := ExpandConstant('{localappdata}\PHASENOX\phasenox.desktop\state');
end;

function PointerPath(): String;
begin
  Result := CanonicalStateDir() + '\data-root.json';
end;

function HandoffPath(): String;
begin
  Result := CanonicalStateDir() + '\installer-data-root.json';
end;

function JsonEscape(Value: String): String;
begin
  Result := Value;
  StringChangeEx(Result, '\', '\\', True);
  StringChangeEx(Result, '"', '\"', True);
end;

procedure SameDriveChanged(Sender: TObject);
var
  Drive: String;
begin
  if SameDriveCheck.Checked then
  begin
    Drive := ExtractFileDrive(WizardDirValue());
    if Drive <> '' then
      DataDirPage.Values[0] := AddBackslash(Drive) + 'PHASENOX Data';
  end;
end;

procedure InitializeWizard();
begin
  ExistingPointer := FileExists(PointerPath());
  ExistingPointerPage := CreateInputOptionPage(
    wpSelectDir,
    'Existing PHASENOX Data Location',
    'Preserve the current Data Root pointer by default.',
    'The installer never edits data-root.json. Choose whether to keep the existing pointer ' +
      'or send a new proposal to PHASENOX Desktop for explicit confirmation.',
    True,
    False
  );
  ExistingPointerPage.Add('Keep the existing Data Root pointer (recommended)');
  ExistingPointerPage.Add('Propose a different Data Location for Desktop confirmation');
  ExistingPointerPage.SelectedValueIndex := 0;

  DataDirPage := CreateInputDirPage(
    ExistingPointerPage.ID,
    'PHASENOX Data Location',
    'Select an independent location for large and persistent data.',
    'This is a proposal only. PHASENOX Desktop validates and asks you to confirm it before ' +
      'persistent services start. The folder is not created or migrated by Setup.',
    False,
    ''
  );
  DataDirPage.Add('');
  DataDirPage.Values[0] := ExpandConstant('{userdocs}\PHASENOX Data');
  SameDriveCheck := TNewCheckBox.Create(DataDirPage);
  SameDriveCheck.Parent := DataDirPage.Surface;
  SameDriveCheck.Caption := 'Suggest the same drive as the application installation';
  SameDriveCheck.Left := DataDirPage.Edits[0].Left;
  SameDriveCheck.Top := DataDirPage.Edits[0].Top + DataDirPage.Edits[0].Height + ScaleY(12);
  SameDriveCheck.Width := DataDirPage.Surface.Width;
  SameDriveCheck.OnClick := @SameDriveChanged;
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := False;
  if (PageID = ExistingPointerPage.ID) and (not ExistingPointer) then
    Result := True
  else if (PageID = DataDirPage.ID) and ExistingPointer and
          (ExistingPointerPage.SelectedValueIndex = 0) then
    Result := True;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if (CurPageID = DataDirPage.ID) and (Trim(DataDirPage.Values[0]) = '') then
  begin
    SuppressibleMsgBox('Select a Data Location proposal or go back to keep the existing pointer.',
      mbError, MB_OK, IDOK);
    Result := False;
  end;
end;

function ShouldWriteHandoff(): Boolean;
begin
  Result := (not ExistingPointer) or (ExistingPointerPage.SelectedValueIndex = 1);
end;

procedure WritePendingHandoff();
var
  Payload: String;
  Timestamp: String;
begin
  if not ShouldWriteHandoff() then
    exit;
  if not ForceDirectories(CanonicalStateDir()) then
    RaiseException('Unable to create canonical PHASENOX small-state directory.');
  Timestamp := GetDateTimeString('yyyy-mm-dd"T"hh:nn:ss"Z"', '-', ':');
  Payload := '{"schema_version":1,"candidate_path":"' +
    JsonEscape(DataDirPage.Values[0]) + '","installer_version":"{#AppVersion}",' +
    '"created_at":"' + Timestamp + '"}' + #13#10;
  if not SaveStringToFile(HandoffPath(), Payload, False) then
    RaiseException('Unable to write the pending PHASENOX Data Location handoff.');
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
    WritePendingHandoff();
end;

function InitializeSetup(): Boolean;
var
  InstallLocation: String;
  InstalledExe: String;
  InstalledMS, InstalledLS: Cardinal;
  CandidateMS, CandidateLS: Cardinal;
begin
  Result := True;
  if RegQueryStringValue(HKCU,
      'Software\Microsoft\Windows\CurrentVersion\Uninstall\{{#AppGuid}_is1',
      'InstallLocation', InstallLocation) then
  begin
    InstalledExe := AddBackslash(RemoveQuotes(InstallLocation)) + 'PHASENOX.exe';
    if GetVersionNumbers(InstalledExe, InstalledMS, InstalledLS) then
    begin
      CandidateMS := (StrToInt('{#AppVersionMajor}') shl 16) or StrToInt('{#AppVersionMinor}');
      CandidateLS := (StrToInt('{#AppVersionPatch}') shl 16);
      if (InstalledMS > CandidateMS) or
         ((InstalledMS = CandidateMS) and (InstalledLS > CandidateLS)) then
      begin
        SuppressibleMsgBox(
          'A newer PHASENØX version is installed. Downgrade is blocked to protect compatibility.',
          mbError, MB_OK, IDOK);
        Result := False;
      end;
    end;
  end;
end;
