; installer\networkmap_setup.iss
; Beschrijving: Inno Setup installer script
; Applicatie: Networkmap Creator
; Auteur: Barremans / CGK
;
; Gebruik: ISCC.exe /DMyAppVersion=1.2.3 /DMySourceDir="..\dist\Networkmap_Creator_1.2.3" installer\networkmap_setup.iss

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
UninstallDisplayIcon={app}\{#MyAppExeName}
DirExistsWarning=no

[Languages]
Name: "dutch"; MessagesFile: "compiler:Languages\Dutch.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Maak een snelkoppeling op het bureaublad"; GroupDescription: "Extra opties:"

[InstallDelete]
Type: filesandordirs; Name: "{app}\_internal"
Type: filesandordirs; Name: "{app}\__pycache__"

[Files]
Source: "{#MySourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}";           Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\assets\icons\icon.ico"
Name: "{group}\Verwijder {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#MyAppName}";   Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\assets\icons\icon.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Description: "Start {#MyAppName}"; Flags: nowait postinstall skipifsilent
