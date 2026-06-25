const fs = require('fs')
const path = require('path')

const root = path.join(__dirname, '..', '..')
const frontendDist = path.join(root, 'frontend', 'dist')
const backendDir = path.join(root, 'backend')
const venvPython =
  process.platform === 'win32'
    ? path.join(backendDir, '.venv', 'Scripts', 'python.exe')
    : path.join(backendDir, '.venv', 'bin', 'python')

function fail(message) {
  console.error(`[prepare-package] ${message}`)
  process.exit(1)
}

if (!fs.existsSync(path.join(frontendDist, 'index.html'))) {
  fail('未找到 frontend/dist，请先执行 frontend 构建')
}

if (!fs.existsSync(venvPython)) {
  fail('未找到 backend/.venv，请先在 backend 目录创建虚拟环境并安装 requirements.txt')
}

console.log('[prepare-package] 前端与 Python 环境检查通过，开始打包...')
