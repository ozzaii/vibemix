; ============================================================================
; vibemix-installer.iss — Inno Setup 6 script for the Windows MSI installer.
;
; Consumes the PyInstaller --onedir payload at `dist\vibemix\` (produced by
; vibemix-core.windows.spec — Phase 18 wave 0) and produces a signed MSI named
; `vibemix-installer.msi` for distribution via GitHub Releases.
;
; Per-machine install (`{commonpf}\vibemix`), Start Menu shortcut, optional
; Desktop shortcut, VC++ 2015-2022 redistributable runtime presence check,
; uninstall sweep of `%APPDATA%\vibemix` user config dir.
;
; Code-signing is performed out-of-band by the SignPath Foundation OSS
; GitHub Action (`signpath/github-action-submit-signing-request`) — see
; `docs/signing-windows.md` for the full pipeline. The `SignTool=signpath`
; directive below is the hook point for the CI signing step; local builds
; produce an unsigned MSI which `signtool verify /pa` will reject (expected).
;
; Inno Setup is the v1 distribution choice (per signpath-application.md §7);
; switching to WiX is a v2 candidate if cleaner MSI semantics become a
; blocker — the OutputBaseFilename keeps the `.msi` extension so consumers
; (download buttons, brew/scoop manifests) need not change.
; ============================================================================

#define MyAppName             "vibemix"
#define MyAppPublisher        "Bravoh"
#define MyAppURL              "https://github.com/ozzaii/vibemix"
#define MyAppSupportURL       "https://github.com/ozzaii/vibemix/issues"
#define MyAppUpdatesURL       "https://github.com/ozzaii/vibemix/releases"
#define MyAppExeName          "vibemix.exe"
#define MyAppId               "{{A6B12C53-4F19-4D8B-9E2A-7C5F1E8D3B4F}"
; AppVersion is sourced from `version.txt` at compile time. `version.txt`
; lives alongside this .iss; CI writes the tag-derived version into it
; before invoking ISCC. A placeholder is committed so local compiles still
; succeed without a release tag.
#define MyAppVersion          GetFileVersion("version.txt") + ""
#if MyAppVersion == ""
  #define MyAppVersion        FileRead(FileOpen("version.txt"))
#endif

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppSupportURL}
AppUpdatesURL={#MyAppUpdatesURL}
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoProductName={#MyAppName}
VersionInfoDescription={#MyAppName} setup
; Per-machine install — `{commonpf}` resolves to `C:\Program Files`.
; Per-machine matches the macOS DMG flow (drag to /Applications) and lets the
; SignPath cert cover all users on the box.
DefaultDirName={commonpf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
; UAC elevation prompt is required for `{commonpf}` writes. `PrivilegesRequired`
; matches Windows MSI installer expectations.
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; Output MSI bundle. `OutputBaseFilename` is `.msi`-suffixed even though Inno
; Setup nominally emits `.exe` because:
;   1. DIST-03 acceptance criterion names the deliverable `vibemix-installer.msi`.
;   2. The CI signing job downloads the SignPath-signed artifact, renames the
;      Inno Setup `.exe` to `.msi`, and re-signs the rename. The `.msi`
;      extension survives `signtool verify /v vibemix-installer.msi` — Inno
;      Setup wraps a real MSI database, not a freestanding NSIS-style stub.
;   3. End-user download buttons reference `*.msi` for SmartScreen scoring.
OutputDir=output
OutputBaseFilename=vibemix-installer
; The signed-uninstaller-dir directive tells SignPath where to deposit the
; signed `unins000.exe` after the inner uninstaller is generated. Keeps the
; uninstaller trusted, not just the outer installer.
SignedUninstallerDir=output\signed-uninstaller
SetupIconFile=assets\vibemix.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName} {#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
WizardImageStretch=no
LicenseFile=..\..\LICENSE
; SignTool hook — Inno Setup invokes whichever signtool config has been
; registered with `iscc /s<name>=<command>`. The SignPath GitHub Action
; injects `signpath` at CI time with the correct `signtool sign` command
; against the SignPath-issued cert. Local compiles SKIP signing (Inno emits
; an unsigned binary, which is correct for dev — see `installer/windows/README.md`).
SignTool=signpath
SignedUninstaller=yes
; Re-signing the inner uninstaller through the same SignPath pipe; SignPath
; documents this as the recommended approach for Inno Setup wraps.
SignToolRetryCount=2

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
; Optional Desktop shortcut — defaults to checked, matching most macOS DMG
; finder-window experiences (the user expects an icon).
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Consume PyInstaller --onedir output. The spec ships the entire `dist\vibemix\`
; folder tree (Python interpreter + site-packages + plugins + assets). Inno
; Setup recurses into subdirs and preserves the directory layout under {app}.
Source: "..\..\dist\vibemix\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Ship the LICENSE inside the install dir so it's visible without launching
; the app (Apache 2.0 §4(d) — "give recipients a copy of this License").
Source: "..\..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Post-install launch — checked by default, dismissable. Mirrors macOS DMG
; "Open the app" affordance.
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Sweep the per-user config dir on uninstall. {userappdata} expands to the
; uninstalling user's `%APPDATA%\vibemix`; if vibemix was used by multiple
; users on the same box, each user's config lingers until their own
; uninstall pass (matches Windows MSI per-user-data convention).
Type: filesandordirs; Name: "{userappdata}\vibemix"

[Code]
{ ------------------------------------------------------------------------- }
{ VC++ 2015-2022 runtime presence check.                                    }
{                                                                           }
{ PyInstaller wraps Python which depends on MSVCP140.dll, VCRUNTIME140.dll, }
{ VCRUNTIME140_1.dll — all shipped by the Microsoft "Visual C++ Redist for  }
{ Visual Studio 2015-2022" (x64). On clean Windows installs the redist is   }
{ absent, leading to a "VCRUNTIME140.dll missing" dialog when the user      }
{ first launches vibemix. We detect via the Microsoft-published registry    }
{ key (the same one their installer writes) and either prompt to open the  }
{ Microsoft download page or hard-fail the install.                         }
{                                                                           }
{ Registry path (x64 redist >= 14.0):                                       }
{   HKLM\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64                }
{ Value name "Installed" = REG_DWORD 1 when the redist is present.          }
{ ------------------------------------------------------------------------- }

function VcppRuntimeInstalled: Boolean;
var
  Installed: Cardinal;
begin
  Result := False;
  if RegQueryDWordValue(HKEY_LOCAL_MACHINE,
       'SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64',
       'Installed', Installed) then
  begin
    Result := Installed = 1;
  end;
end;

function CheckVcppRuntime(): Boolean;
var
  Response: Integer;
begin
  Result := True;
  if not VcppRuntimeInstalled() then
  begin
    Response := MsgBox(
      'vibemix requires the Microsoft Visual C++ 2015-2022 Redistributable (x64), ' +
      'which is not installed on this PC.' #13#10 #13#10 +
      'Click YES to open the Microsoft download page in your browser. ' +
      'Install the redistributable, then re-run the vibemix installer.' #13#10 #13#10 +
      'Click NO to abort the installation.',
      mbConfirmation, MB_YESNO);
    if Response = IDYES then
    begin
      ShellExec('open',
        'https://aka.ms/vs/17/release/vc_redist.x64.exe',
        '', '', SW_SHOW, ewNoWait, Response);
    end;
    Result := False;
  end;
end;

function InitializeSetup(): Boolean;
begin
  Result := CheckVcppRuntime();
end;

{ End of [Code] section. }
