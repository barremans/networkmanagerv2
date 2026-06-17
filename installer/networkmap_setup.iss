; installer\networkmap_setup.iss
; Beschrijving: Inno Setup installer script
; Applicatie: Networkmap Creator
; Auteur: Barremans / CGK
;
; Gebruik:
;   ISCC.exe /DMyAppVersion=1.2.3 /DMySourceDir="..\dist\Networkmap_Creator_1.2.3" installer\networkmap_setup.iss
;
; Optioneel met signing via compiler define:
;   ISCC.exe /DMyAppVersion=1.2.3 /DMySourceDir="..\dist\Networkmap_Creator_1.2.3" /DSignCmd="signtool sign /fd SHA256 /td SHA256 /tr http://timestamp.digicert.com /a $f" installer\networkmap_setup.iss

#ifndef MyAppVersion
  #define MyAppVersion "1.0.0"
#endif

#ifndef MySourceDir
  #define MySourceDir "..\dist\Networkmap_Creator_" + MyAppVersion
#endif

#define MyAppName "Networkmap Creator"
#define MyAppPublisher "CGK / Barremans"
#define MyAppExeName "Networkmap_Creator.exe"
#define MyAppId "{{B7C4D2E1-F3A5-48B9-A012-CDEF56789ABC}"

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=no
OutputDir=..\dist
OutputBaseFilename=Networkmap_Creator_setup_{#MyAppVersion}
SetupIconFile={#MySourceDir}\assets\icons\icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64
ArchitecturesAllowed=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
DirExistsWarning=no
ChangesAssociations=no
DisableDirPage=no
DisableReadyMemo=no

#ifdef SignCmd
SignTool={#SignCmd}
SignedUninstaller=yes
#endif

[Languages]
Name: "dutch"; MessagesFile: "compiler:Languages\Dutch.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Maak een snelkoppeling op het bureaublad"; GroupDescription: "Extra opties:"

[InstallDelete]
Type: filesandordirs; Name: "{app}\_internal"
Type: filesandordirs; Name: "{app}\__pycache__"

[Files]
; Alle programmabestanden — databestanden uitgesloten
Source: "{#MySourceDir}\*"; DestDir: "{app}"; \
    Flags: ignoreversion recursesubdirs createallsubdirs; \
    Excludes: "\data\settings.json,\data\network_data.json"

; Databestanden — ALLEEN bij eerste installatie, nooit overschrijven
Source: "{#MySourceDir}\data\settings.json"; \
    DestDir: "{app}\data"; \
    Flags: onlyifdoesntexist uninsneveruninstall

Source: "{#MySourceDir}\data\network_data.json"; \
    DestDir: "{app}\data"; \
    Flags: onlyifdoesntexist uninsneveruninstall

[Icons]
Name: "{group}\{#MyAppName}";           Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\assets\icons\icon.ico"
Name: "{group}\Verwijder {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#MyAppName}";   Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\assets\icons\icon.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Description: "Start {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Code]
// =============================================================================
// S6 - Azure AD configuratie migratie
// Bij update op bestaande installatie: azure_ad sectie toevoegen aan
// settings.json als tenant_id nog niet ingevuld is.
// =============================================================================

const
  AD_TENANT_ID      = '526b32fa-8cb1-4d6a-9e2b-fd48e2a0e296';
  AD_CLIENT_ID      = '58e2dacc-6e4c-4fd0-9166-03b467aeacd8';
  AD_GROUP_ADMIN    = 'CGK-APP-L6';
  AD_GROUP_READONLY = '';

function ReadFileAsString(const FileName: String): String;
var
  Lines    : TArrayOfString;
  I        : Integer;
  Result2  : String;
begin
  Result := '';
  if not LoadStringsFromFile(FileName, Lines) then
    exit;
  Result2 := '';
  for I := 0 to GetArrayLength(Lines) - 1 do
  begin
    if I > 0 then
      Result2 := Result2 + #13#10;
    Result2 := Result2 + Lines[I];
  end;
  Result := Result2;
end;

procedure WriteFileAsString(const FileName: String; const Content: String);
var
  Lines : TArrayOfString;
  Parts : TArrayOfString;
  I     : Integer;
  S     : String;
  Pos1  : Integer;
begin
  // Splits op #13#10 en schrijft terug
  S := Content;
  SetArrayLength(Lines, 0);
  I := 0;
  repeat
    Pos1 := Pos(#13#10, S);
    SetArrayLength(Lines, I + 1);
    if Pos1 > 0 then
    begin
      Lines[I] := Copy(S, 1, Pos1 - 1);
      S := Copy(S, Pos1 + 2, Length(S));
    end else
    begin
      Lines[I] := S;
      S := '';
    end;
    I := I + 1;
  until S = '';
  SaveStringsToFile(FileName, Lines, False);
end;

procedure PatchAzureAdInSettings();
var
  SettingsPath  : String;
  Content       : String;
  AzureAdBlock  : String;
  InsertPos     : Integer;
begin
  SettingsPath := ExpandConstant('{app}\data\settings.json');

  if not FileExists(SettingsPath) then
    exit;

  Content := ReadFileAsString(SettingsPath);
  if Content = '' then
    exit;

  // Tenant al correct ingevuld - niets te doen
  if Pos(AD_TENANT_ID, Content) > 0 then
    exit;

  // Azure AD blok samenstellen
  AzureAdBlock :=
    ',' + #13#10 +
    '  "azure_ad": {' + #13#10 +
    '    "enabled": true,' + #13#10 +
    '    "tenant_id": "' + AD_TENANT_ID + '",' + #13#10 +
    '    "client_id": "' + AD_CLIENT_ID + '",' + #13#10 +
    '    "group_admin": "' + AD_GROUP_ADMIN + '",' + #13#10 +
    '    "group_readonly": "' + AD_GROUP_READONLY + '"' + #13#10 +
    '  }';

  // Verwijder bestaand leeg azure_ad blok indien aanwezig
  if Pos('"azure_ad"', Content) > 0 then
  begin
    InsertPos := Pos('"azure_ad"', Content);
    if InsertPos > 2 then
    begin
      InsertPos := InsertPos - 1;
      while (InsertPos > 0) and
            ((Content[InsertPos] = ' ') or (Content[InsertPos] = #13) or
             (Content[InsertPos] = #10)) do
        InsertPos := InsertPos - 1;
      if (InsertPos > 0) and (Content[InsertPos] = ',') then
        InsertPos := InsertPos - 1;
      Content := Copy(Content, 1, InsertPos) + #13#10 + '}';
    end;
  end;

  // Voeg azure_ad in voor de laatste sluitende }
  InsertPos := Length(Content);
  while (InsertPos > 0) and (Content[InsertPos] <> '}') do
    InsertPos := InsertPos - 1;

  if InsertPos > 0 then
  begin
    Content := Copy(Content, 1, InsertPos - 1) + AzureAdBlock + #13#10 + '}';
    WriteFileAsString(SettingsPath, Content);
    Log('S6 migratie: azure_ad sectie toegevoegd aan settings.json');
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
    PatchAzureAdInSettings();
end;