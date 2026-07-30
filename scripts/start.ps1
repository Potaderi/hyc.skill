[CmdletBinding()]
param(
    [double]$PollInterval = 0.3,
    [switch]$SelfTest,
    [switch]$NoInstall
)

$ErrorActionPreference = "Stop"

if (-not $IsWindows -and $PSVersionTable.PSEdition -eq "Core") {
    throw "HYC requires Windows desktop WeChat."
}

$worker = Join-Path $PSScriptRoot "wechat_auto_reply.py"
if (-not (Test-Path -LiteralPath $worker -PathType Leaf)) {
    throw "Worker script not found: $worker"
}

$pyLauncher = Get-Command "py" -ErrorAction SilentlyContinue
$pythonCommand = Get-Command "python" -ErrorAction SilentlyContinue
if (-not $pyLauncher -and -not $pythonCommand) {
    throw "Python 3.10 or newer is required."
}

if ($pyLauncher) {
    $pythonVersionText = & $pyLauncher.Source -3 -c "import platform; print(platform.python_version())"
}
else {
    $pythonVersionText = & $pythonCommand.Source -c "import platform; print(platform.python_version())"
}
if ($LASTEXITCODE -ne 0 -or [version]$pythonVersionText -lt [version]"3.10") {
    throw "Python 3.10 or newer is required. Found: $pythonVersionText"
}

if ($SelfTest) {
    if ($pyLauncher) {
        & $pyLauncher.Source -3 $worker --self-test
    }
    else {
        & $pythonCommand.Source $worker --self-test
    }
    exit $LASTEXITCODE
}

if ($PollInterval -lt 0.1) {
    throw "PollInterval must be at least 0.1 seconds."
}

$runtimeRoot = Join-Path $env:LOCALAPPDATA "hyc-skill"
$venvRoot = Join-Path $runtimeRoot ".venv"
$venvPython = Join-Path $venvRoot "Scripts\python.exe"

if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
    New-Item -ItemType Directory -Path $runtimeRoot -Force | Out-Null
    Write-Host "Creating the HYC Python environment..."
    if ($pyLauncher) {
        & $pyLauncher.Source -3 -m venv $venvRoot
    }
    else {
        & $pythonCommand.Source -m venv $venvRoot
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Could not create the Python environment."
    }
}

& $venvPython -c "import wxauto" 2>$null
$wxautoAvailable = $LASTEXITCODE -eq 0
if (-not $wxautoAvailable) {
    if ($NoInstall) {
        throw "wxauto is not installed in $venvRoot. Rerun without -NoInstall."
    }
    Write-Host "Installing the desktop WeChat automation dependency..."
    & $venvPython -m pip install --disable-pip-version-check --upgrade "wxauto>=3.9"
    if ($LASTEXITCODE -ne 0) {
        throw "Could not install wxauto. Check access to PyPI and rerun."
    }
}

& $venvPython $worker --poll-interval $PollInterval
exit $LASTEXITCODE
