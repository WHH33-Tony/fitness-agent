const fs = require('fs')
const path = require('path')

const root = path.join(__dirname, '..', '..')
const unpacked = path.join(__dirname, '..', 'dist', 'win-unpacked', 'resources')
const frontendSrc = path.join(root, 'frontend', 'dist')
const backendSrc = path.join(root, 'backend')
const frontendDst = path.join(unpacked, 'frontend', 'dist')
const backendDst = path.join(unpacked, 'backend')

function shouldSkip(relPath) {
  const parts = relPath.split(path.sep)
  if (parts.includes('__pycache__')) return true
  if (parts.includes('.venv')) return true
  if (relPath.endsWith('.pyc') || relPath.endsWith('.pyo')) return true
  return false
}

function linkBackendVenv(srcBackend, dstBackend) {
  const srcVenv = path.join(srcBackend, '.venv')
  const dstVenv = path.join(dstBackend, '.venv')
  if (!fs.existsSync(srcVenv)) {
    console.warn('未找到 backend/.venv，打包版将回退到系统 python')
    return
  }
  try {
    if (fs.existsSync(dstVenv)) {
      const stat = fs.lstatSync(dstVenv)
      if (stat.isSymbolicLink() || stat.isJunction?.()) return
    } else {
      const type = process.platform === 'win32' ? 'junction' : 'dir'
      fs.symlinkSync(srcVenv, dstVenv, type)
      console.log('已链接 backend/.venv 到测试包')
    }
  } catch (err) {
    console.warn('链接 backend/.venv 失败，请手动确保测试包可访问 Python 虚拟环境', err)
  }
}

function copyDir(src, dst) {
  if (!fs.existsSync(src)) {
    throw new Error(`源目录不存在: ${src}`)
  }
  fs.mkdirSync(dst, { recursive: true })

  for (const entry of fs.readdirSync(src, { withFileTypes: true })) {
    const rel = entry.name
    if (shouldSkip(rel)) continue
    const from = path.join(src, rel)
    const to = path.join(dst, rel)
    if (entry.isDirectory()) {
      copyDir(from, to)
      continue
    }
    fs.mkdirSync(path.dirname(to), { recursive: true })
    fs.copyFileSync(from, to)
  }
}

if (!fs.existsSync(unpacked)) {
  console.error('未找到测试版目录，请先执行 npm run build')
  process.exit(1)
}

copyDir(frontendSrc, frontendDst)
copyDir(backendSrc, backendDst)
linkBackendVenv(backendSrc, backendDst)

const mainDst = path.join(__dirname, '..', 'dist', 'win-unpacked', 'main.cjs')
fs.copyFileSync(path.join(__dirname, '..', 'main.cjs'), mainDst)

console.log('已同步 frontend/dist、backend 与 main.cjs 到 dist/win-unpacked')
