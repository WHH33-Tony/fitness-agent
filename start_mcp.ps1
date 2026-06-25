Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
$BACKEND = Join-Path $ROOT "backend"
$PY = Join-Path $BACKEND ".venv\Scripts\python.exe"

if (!(Test-Path $PY)) {
  throw "未找到 Python 虚拟环境：$PY"
}

Set-Location $BACKEND
& $PY -m uvicorn app.mcp.server:app --host 127.0.0.1 --port 9001
