; Keep language selection available when an older install saved English.
!define MUI_LANGDLL_ALWAYSSHOW
!define MUI_LANGDLL_ALLLANGUAGES

!macro SAG_STOP_INSTALLED_COMPONENTS
  !insertmacro CheckIfAppIsRunning "$INSTDIR\${MAINBINARYNAME}.exe" "${PRODUCTNAME}"
  ${If} ${FileExists} "$INSTDIR\bin\sag.exe"
    nsExec::ExecToLog /TIMEOUT=15000 '"$INSTDIR\bin\sag.exe" service stop'
    Pop $0
    ${If} $0 != 0
      DetailPrint "SAG service stop returned $0; checking the installed sag.exe for running processes."
    ${EndIf}
    !insertmacro CheckIfAppIsRunning "$INSTDIR\bin\sag.exe" "${PRODUCTNAME} (sag.exe)"
  ${EndIf}
!macroend

!macro NSIS_HOOK_PREINSTALL
  !insertmacro SAG_STOP_INSTALLED_COMPONENTS
!macroend

!macro NSIS_HOOK_PREUNINSTALL
  !insertmacro SAG_STOP_INSTALLED_COMPONENTS
!macroend

; Update only existing shortcuts that point to this installation. Keep their
; target, arguments, working directory and AppUserModelID intact.
!macro SAG_UPDATE_SHORTCUT_ICON shortcut
  Push $0
  Push $1
  Push $2
  Push $3
  !insertmacro IsShortcutTarget "${shortcut}" "$INSTDIR\${MAINBINARYNAME}.exe"
  Pop $0
  ${If} $0 = 1
    !insertmacro ComHlpr_CreateInProcInstance ${CLSID_ShellLink} ${IID_IShellLink} r0 ""
    ${If} $0 P<> 0
      ${IUnknown::QueryInterface} $0 '("${IID_IPersistFile}",.r1)'
      ${If} $1 P<> 0
        ${IPersistFile::Load} $1 '("${shortcut}", ${STGM_READWRITE})i.r2'
        ${If} $2 >= 0
          ${IShellLink::SetIconLocation} $0 '(w "$INSTDIR\icons\sag-rounded-v2.ico", i 0)i.r2'
        ${EndIf}
        ${If} $2 >= 0
          ${IPersistFile::Save} $1 '("${shortcut}",1)i.r2'
        ${EndIf}
        ${IUnknown::Release} $1 ""
      ${Else}
        StrCpy $2 -1
      ${EndIf}
      ${IUnknown::Release} $0 ""
    ${Else}
      StrCpy $2 -1
    ${EndIf}
    ${If} $2 >= 0
      ; SHCNE_UPDATEITEM / SHCNF_PATHW refreshes this shortcut only.
      System::Call 'shell32::SHChangeNotify(i 0x2000, i 0x5, w "${shortcut}", p 0) v'
    ${Else}
      DetailPrint "Could not update shortcut icon: ${shortcut} (HRESULT $2)"
    ${EndIf}
  ${EndIf}
  Pop $3
  Pop $2
  Pop $1
  Pop $0
!macroend

; Rename a legacy shortcut only when it targets this exact installation. Never
; overwrite or delete a same-named shortcut that points somewhere else.
!macro SAG_MIGRATE_OLD_SHORTCUT oldShortcut newShortcut
  Push $0
  Push $1
  !insertmacro IsShortcutTarget "${oldShortcut}" "$INSTDIR\${MAINBINARYNAME}.exe"
  Pop $0
  ${If} $0 = 1
    ${If} ${FileExists} "${newShortcut}"
      !insertmacro IsShortcutTarget "${newShortcut}" "$INSTDIR\${MAINBINARYNAME}.exe"
      Pop $1
      ${If} $1 = 1
        Delete "${oldShortcut}"
      ${Else}
        DetailPrint "Existing Super-SAG shortcut points elsewhere; retaining the old shortcut."
      ${EndIf}
    ${Else}
      Rename "${oldShortcut}" "${newShortcut}"
    ${EndIf}
  ${EndIf}
  Pop $1
  Pop $0
!macroend

!macro NSIS_HOOK_POSTINSTALL
  !insertmacro SAG_MIGRATE_OLD_SHORTCUT "$DESKTOP\SAG Wiki.lnk" "$DESKTOP\${PRODUCTNAME}.lnk"
  !insertmacro SAG_MIGRATE_OLD_SHORTCUT "$SMPROGRAMS\SAG Wiki.lnk" "$SMPROGRAMS\${PRODUCTNAME}.lnk"
  !insertmacro SAG_MIGRATE_OLD_SHORTCUT "$SMPROGRAMS\$AppStartMenuFolder\SAG Wiki.lnk" "$SMPROGRAMS\$AppStartMenuFolder\${PRODUCTNAME}.lnk"
  !insertmacro SAG_UPDATE_SHORTCUT_ICON "$DESKTOP\${PRODUCTNAME}.lnk"
  !insertmacro SAG_UPDATE_SHORTCUT_ICON "$SMPROGRAMS\${PRODUCTNAME}.lnk"
  !insertmacro SAG_UPDATE_SHORTCUT_ICON "$SMPROGRAMS\$AppStartMenuFolder\${PRODUCTNAME}.lnk"
!macroend
