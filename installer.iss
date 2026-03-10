; ============================================================
; Cracker's Toolkit — Inno Setup Installer Script
; ============================================================
; Build: iscc installer.iss
; Requires: Inno Setup 6.x (https://jrsoftware.org/isinfo.php)
; ============================================================

#define MyAppName "Cracker's Toolkit"
#define MyAppVersion "1.0"
#define MyAppPublisher "Cracker's Toolkit"
#define MyAppExeName "CrackersToolkit.exe"

; --- Adjust this to your actual build output path ---
#define BuildRoot "D:\Crackers_toolkit"

[Setup]
AppId={{A3F8C1D2-7E4B-4A9F-B6C3-D5E8F0A1B2C4}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\CrackersToolkit
DefaultGroupName={#MyAppName}
OutputDir={#BuildRoot}\installer_output
OutputBaseFilename=CrackersToolkit_Setup
SetupIconFile={#BuildRoot}\icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
DisableProgramGroupPage=yes
LicenseFile=
UninstallDisplayIcon={app}\CrackersToolkit\{#MyAppExeName}
; Approximate disk space — adjust after first build
ExtraDiskSpaceRequired=0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Types]
Name: "full"; Description: "Full installation (all tools)"
Name: "minimal"; Description: "Minimal (GUI + hashcat only)"
Name: "custom"; Description: "Custom"; Flags: iscustom

[Components]
Name: "core";        Description: "Cracker's Toolkit GUI";                Types: full minimal custom; Flags: fixed
Name: "hashcat";     Description: "hashcat 7.1.2 (password cracker)";     Types: full minimal custom; Flags: fixed
Name: "jtr";         Description: "John the Ripper 1.9.0 Jumbo 1";       Types: full custom
Name: "pcfg";        Description: "PCFG Cracker suite (guesser, trainer, scorer, PRINCE-LING)"; Types: full custom
Name: "demeuk";      Description: "demeuk wordlist cleaner";              Types: full custom
Name: "prince";      Description: "PRINCE Processor";                     Types: full custom
Name: "python";      Description: "Portable Python 3.12 (for external script tools)"; Types: full custom

[Files]
; --- Core application (PyInstaller output) ---
Source: "{#BuildRoot}\dist\CrackersToolkit\*";     DestDir: "{app}\CrackersToolkit"; Components: core;    Flags: ignoreversion recursesubdirs createallsubdirs

; --- hashcat ---
Source: "{#BuildRoot}\hashcat-7.1.2\*";             DestDir: "{app}\hashcat-7.1.2";   Components: hashcat; Flags: ignoreversion recursesubdirs createallsubdirs

; --- John the Ripper ---
Source: "{#BuildRoot}\john-1.9.0-jumbo-1-win64\*";  DestDir: "{app}\john-1.9.0-jumbo-1-win64"; Components: jtr; Flags: ignoreversion recursesubdirs createallsubdirs

; --- PCFG Cracker ---
Source: "{#BuildRoot}\Scripts_to_use\pcfg_cracker-master\*"; DestDir: "{app}\Scripts_to_use\pcfg_cracker-master"; Components: pcfg; Flags: ignoreversion recursesubdirs createallsubdirs

; --- demeuk ---
Source: "{#BuildRoot}\Scripts_to_use\demeuk-master\*"; DestDir: "{app}\Scripts_to_use\demeuk-master"; Components: demeuk; Flags: ignoreversion recursesubdirs createallsubdirs

; --- PRINCE Processor ---
Source: "{#BuildRoot}\Scripts_to_use\princeprocessor-master\*"; DestDir: "{app}\Scripts_to_use\princeprocessor-master"; Components: prince; Flags: ignoreversion recursesubdirs createallsubdirs

; --- Output directory (empty, but needs to exist) ---
Source: "{#BuildRoot}\output\*";  DestDir: "{app}\output";  Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist onlyifdoesntexist

; --- Portable Python 3.12 embeddable (optional) ---
; To use: download python-3.12.x-embed-amd64.zip, extract to {#BuildRoot}\python-3.12-embed,
; then uncomment the line below. If absent, installer will skip this component.
; Source: "{#BuildRoot}\python-3.12-embed\*"; DestDir: "{app}\python-3.12"; Components: python; Flags: ignoreversion recursesubdirs createallsubdirs

[Dirs]
Name: "{app}\output"; Flags: uninsneveruninstall

[Icons]
Name: "{group}\{#MyAppName}";                Filename: "{app}\CrackersToolkit\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{group}\Uninstall {#MyAppName}";      Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}";          Filename: "{app}\CrackersToolkit\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: checkedonce

[Run]
Filename: "{app}\CrackersToolkit\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\output\*"

[Code]
// Show a note about Python and Perl after installation
procedure CurStepChanged(CurStep: TSetupStep);
var
  Msg: String;
begin
  if CurStep = ssPostInstall then
  begin
    // Check if portable python was installed
    if not DirExists(ExpandConstant('{app}\python-3.12')) then
    begin
      if not FileExists('C:\Windows\py.exe') then
      begin
        // No portable Python bundled and no system Python launcher found
        Msg := 'Note: Some tools (PCFG Guesser, demeuk, etc.) require Python 3 to be installed.' + #13#10 +
               'You can install it from https://www.python.org/downloads/' + #13#10 + #13#10 +
               'The application will show a dependency checker on first run to help you set up anything missing.';
        MsgBox(Msg, mbInformation, MB_OK);
      end;
    end;
  end;
end;
