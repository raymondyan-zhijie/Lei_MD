; NSIS installer script for Lei_MD
; Builds a Windows installer (Lei_MD-0.4.1-Setup.exe) that:
; - Installs Lei_MD-0.4.1.exe to $PROGRAMFILES64\Lei_MD\
; - Adds Start Menu + Desktop shortcuts
; - Adds uninstall entry to "Add/Remove Programs"
; - Detects existing installation and offers upgrade
;
; Build:
;     makensis installer.nsi
;     # → Lei_MD-0.4.1-Setup.exe  (~30 MB)
;
; Or via the build script:
;     pwsh scripts/build-windows.ps1 -WithInstaller

!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "x64.nsh"

; ──────────────────────────────────────────────────────────────────────
; Metadata
; ──────────────────────────────────────────────────────────────────────
!define APP_NAME     "Lei_MD"
!define APP_VERSION  "0.4.1"
!define APP_PUBLISHER "leimengde"
!define APP_EXE      "${APP_NAME}-${APP_VERSION}.exe"
!define APP_DIR      "${APP_NAME}"
!define UNINST_KEY   "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}"

Name "${APP_NAME} ${APP_VERSION}"
OutFile "Lei_MD-${APP_VERSION}-Setup.exe"
InstallDir "$PROGRAMFILES64\${APP_DIR}"
InstallDirRegKey HKLM "Software\${APP_NAME}" "InstallDir"
RequestExecutionLevel highest
ShowInstDetails show
ShowUninstDetails show

; ──────────────────────────────────────────────────────────────────────
; Modern UI
; ──────────────────────────────────────────────────────────────────────
!define MUI_ABORTWARNING
!define MUI_ICON "${NSISDIR}\Contrib\Graphics\Icons\modern-install.ico"
!define MUI_UNICON "${NSISDIR}\Contrib\Graphics\Icons\modern-uninstall.ico"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "LICENSE"  ; if present; skip if missing
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

!insertmacro MUI_LANGUAGE "English"
!insertmacro MUI_LANGUAGE "SimpChinese"

; ──────────────────────────────────────────────────────────────────────
; Installer
; ──────────────────────────────────────────────────────────────────────
Section "Install"
    SetOutPath "$INSTDIR"

    ; The PyInstaller onefile output
    File "..\dist\${APP_EXE}"

    ; Optional: copy README and LICENSE next to the exe
    ; (PyInstaller bundles them too, but having them in the install dir
    ; makes them discoverable for "Browse install location")
    ${If} ${FileExists} "..\README.md"
        File "..\README.md"
    ${EndIf}
    ${If} ${FileExists} "..\LICENSE"
        File "..\LICENSE"
    ${EndIf}

    ; Registry: store install dir
    WriteRegStr HKLM "Software\${APP_NAME}" "InstallDir" "$INSTDIR"
    WriteRegStr HKLM "Software\${APP_NAME}" "Version"    "${APP_VERSION}"

    ; Start Menu shortcut
    CreateDirectory "$SMPROGRAMS\${APP_NAME}"
    CreateShortcut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" \
                   "$INSTDIR\${APP_EXE}"

    ; Desktop shortcut (optional — comment out if not wanted)
    CreateShortcut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}"

    ; Add/Remove Programs entry
    WriteRegStr   HKLM "${UNINST_KEY}" "DisplayName"     "${APP_NAME}"
    WriteRegStr   HKLM "${UNINST_KEY}" "DisplayVersion"  "${APP_VERSION}"
    WriteRegStr   HKLM "${UNINST_KEY}" "Publisher"       "${APP_PUBLISHER}"
    WriteRegStr   HKLM "${UNINST_KEY}" "InstallLocation" "$INSTDIR"
    WriteRegStr   HKLM "${UNINST_KEY}" "UninstallString" "$INSTDIR\Uninstall.exe"
    WriteRegStr   HKLM "${UNINST_KEY}" "QuietUninstallString" "$INSTDIR\Uninstall.exe /S"
    WriteRegDWORD HKLM "${UNINST_KEY}" "NoModify" 1
    WriteRegDWORD HKLM "${UNINST_KEY}" "NoRepair" 1

    ; Generate uninstaller
    WriteUninstaller "$INSTDIR\Uninstall.exe"
SectionEnd

; ──────────────────────────────────────────────────────────────────────
; Uninstaller
; ──────────────────────────────────────────────────────────────────────
Section "Uninstall"
    Delete "$INSTDIR\${APP_EXE}"
    Delete "$INSTDIR\README.md"
    Delete "$INSTDIR\LICENSE"
    Delete "$INSTDIR\Uninstall.exe"
    RMDir "$INSTDIR"

    Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
    RMDir  "$SMPROGRAMS\${APP_NAME}"
    Delete "$DESKTOP\${APP_NAME}.lnk"

    DeleteRegKey HKLM "Software\${APP_NAME}"
    DeleteRegKey HKLM "${UNINST_KEY}"
SectionEnd

; ──────────────────────────────────────────────────────────────────────
; Upgrade logic — if a previous version is installed, detect it and
; suggest uninstall first. NSIS's standard upgrade flow is:
;   1. User runs the new installer
;   2. New installer overwrites the old files in $INSTDIR
;   3. Old "Uninstall.exe" is replaced
; The default behavior is "upgrade in place" — good enough for v0.4.1.
; If you want strict version check, use WordFunc.nsh + VersionCompare.
; ──────────────────────────────────────────────────────────────────────
Function .onInit
    ReadRegStr $0 HKLM "Software\${APP_NAME}" "InstallDir"
    ${If} $0 != ""
        ; Existing install found. MessageBox asks user.
        MessageBox MB_YESNO|MB_ICONQUESTION \
            "An existing ${APP_NAME} installation was detected at $0.$\r$\n$\r$\n\
             The installer will upgrade it in place.$\r$\n$\r$\n\
             Continue?" \
            /SD IDYES IDYES +2
        Abort
    ${EndIf}
FunctionEnd
