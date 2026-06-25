Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Info($msg) { Write-Host "[start_desktop] $msg" -ForegroundColor Cyan }
function Warn($msg) { Write-Host "[start_desktop] $msg" -ForegroundColor Yellow }

$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
$BACKEND = Join-Path $ROOT "backend"
$FRONTEND = Join-Path $ROOT "frontend"
$ELECTRON = Join-Path $ROOT "electron"

Info "Repo: $ROOT"

if (!(Test-Path $BACKEND)) { throw "缺少 backend 目录：$BACKEND" }
if (!(Test-Path $FRONTEND)) { throw "缺少 frontend 目录：$FRONTEND" }
if (!(Test-Path $ELECTRON)) { throw "缺少 electron 目录：$ELECTRON" }

# 1) Backend venv + deps
$VENV = Join-Path $BACKEND ".venv"
$PY = Join-Path $VENV "Scripts\python.exe"
if (!(Test-Path $PY)) {
  Info "创建 Python 虚拟环境：backend\.venv"
  Push-Location $BACKEND
  python -m venv ".venv"
  Pop-Location
}

Info "安装/更新后端依赖"
Push-Location $BACKEND
& $PY -m pip install -U pip
& $PY -m pip install -r "requirements.txt"
Pop-Location

# 2) Frontend build (only when dist missing)
$DIST = Join-Path $FRONTEND "dist"
if (!(Test-Path $DIST)) {
  Info "前端 dist 不存在，开始构建"
  Push-Location $FRONTEND
  npm install
  npm run build
  Pop-Location
} else {
  Info "前端 dist 已存在，跳过构建（如需重建可删 frontend\dist）"
}

# 3) Start MCP server in a new window (optional but recommended)
Info "启动 MCP 网关（新窗口，端口 9001）"
if (!(Test-Path (Join-Path $ROOT "start_mcp.ps1"))) {
  throw "缺少 MCP 启动脚本：$(Join-Path $ROOT 'start_mcp.ps1')"
}
Start-Process -FilePath "powershell.exe" -ArgumentList @(
  "-NoExit",
  "-ExecutionPolicy", "Bypass",
  "-File", (Join-Path $ROOT "start_mcp.ps1")
)

# 4) Start Electron (it will spawn backend itself)
Info "启动 Electron（会自动拉起后端 FastAPI，端口自动选择）"
Push-Location $ELECTRON
$env:PYTHON_EXECUTABLE = $PY
npm install
npm run start
Pop-Location

