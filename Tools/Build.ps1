# Tools/Build.ps1 — the ONLY sanctioned build command for this project.
#
# Skips the VS Build menu / MSBuild SetEnv trap (CLAUDE.md gotcha #29). UE C++ projects
# with engine modules + plugins generate $(IncludePath) > 32 KB; MSBuild's SetEnv task on
# line 116 of Microsoft.Cpp.Current.targets tries to push that into the Windows INCLUDE
# env var and dies with "Environment variable name or value is too long" before any
# compile runs. Nothing's wrong with the machine -- it's a generic UE+VS toolchain
# pothole that hits every machine that tries to use the VS Build menu on this project.
#
# This script calls Build.bat -> UnrealBuildTool -> cl.exe directly. UBT passes include
# paths as command-line args (/I "...") instead of stuffing them into a Windows env var,
# so the SetEnv ceiling isn't in the code path at all. Same toolchain, different driver.
#
# Edit C++ in whatever IDE you like; just always COMPILE through this. After a successful
# build the editor's "rebuild outdated modules?" prompt is the only other working path,
# because that prompt also goes through UBT (not MSBuild).
#
# Usage from the repo root:
#   .\Tools\Build.ps1
#   .\Tools\Build.ps1 -Config Debug
#   .\Tools\Build.ps1 -Target ModularHexMap          # game target instead of editor
#   .\Tools\Build.ps1 -UEPath "D:\UE_5.7"            # non-default engine install

param(
    [string]$Target = "ModularHexMapEditor",
    [string]$Config = "Development",
    [string]$UEPath = "C:\Program Files\Epic Games\UE_5.7"
)

$ErrorActionPreference = "Stop"

$repo  = Split-Path -Parent $PSScriptRoot
$uproj = Join-Path $repo "ModularHexMap.uproject"
$bat   = Join-Path $UEPath "Engine\Build\BatchFiles\Build.bat"

if (-not (Test-Path $uproj)) { throw "Can't find ModularHexMap.uproject at $uproj." }
if (-not (Test-Path $bat))   { throw "Can't find Build.bat at $bat. Pass -UEPath if UE is installed elsewhere." }

Write-Host ""
Write-Host ">>> Build.ps1: $Target | $Config | Win64" -ForegroundColor Cyan
Write-Host ">>> Project:   $uproj"                    -ForegroundColor DarkGray
Write-Host ">>> Engine:    $UEPath"                   -ForegroundColor DarkGray
Write-Host ""

& $bat $Target Win64 $Config -Project="$uproj" -WaitMutex

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host ">>> Build OK. Launch the editor and click Yes if it prompts to rebuild outdated modules." -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host ">>> Build FAILED (exit $LASTEXITCODE). Read the lines above for the actual compile error -- if it's an env var error, you're hitting MSBuild's SetEnv trap and somehow ended up not going through UBT. Check that UE is installed at -UEPath and that Build.bat itself ran." -ForegroundColor Red
    exit $LASTEXITCODE
}
