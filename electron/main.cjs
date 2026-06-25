const { app, BrowserWindow, session } = require('electron')

app.commandLine.appendSwitch('autoplay-policy', 'no-user-gesture-required')
const path = require('path')
const fs = require('fs')
const net = require('net')
const http = require('http')

let backendProcess = null
let mcpProcess = null
let backendPort = 8000
let mcpPort = 9001

function loadDotEnv(envPath) {
  try {
    if (!envPath || !fs.existsSync(envPath)) return {}
    const raw = fs.readFileSync(envPath, 'utf8')
    const out = {}
    for (const line of raw.split(/\r?\n/)) {
      const trimmed = String(line || '').trim()
      if (!trimmed || trimmed.startsWith('#')) continue
      const idx = trimmed.indexOf('=')
      if (idx <= 0) continue
      const k = trimmed.slice(0, idx).trim()
      let v = trimmed.slice(idx + 1).trim()
      if ((v.startsWith('"') && v.endsWith('"')) || (v.startsWith("'") && v.endsWith("'"))) {
        v = v.slice(1, -1)
      }
      out[k] = v
    }
    return out
  } catch (_) {
    return {}
  }
}

async function findFreePort(preferredPort) {
  function tryListen(port) {
    return new Promise((resolve) => {
      const server = net.createServer()
      server.unref()
      server.on('error', () => resolve(null))
      server.listen({ port, host: '127.0.0.1' }, () => {
        const addr = server.address()
        const p = addr && typeof addr === 'object' ? addr.port : port
        server.close(() => resolve(p))
      })
    })
  }

  const preferred = await tryListen(preferredPort)
  if (preferred) return preferred
  // let OS pick an available port
  const any = await tryListen(0)
  return any || preferredPort
}

function waitForHttpReady(port, healthPath, timeoutMs = 20000) {
  const started = Date.now()
  return new Promise((resolve) => {
    const attempt = () => {
      const req = http.request(
        { hostname: '127.0.0.1', port, path: healthPath, method: 'GET', timeout: 1500 },
        (res) => {
          res.resume()
          if (res.statusCode && res.statusCode >= 200 && res.statusCode < 500) {
            resolve(true)
          } else {
            if (Date.now() - started > timeoutMs) return resolve(false)
            setTimeout(attempt, 500)
          }
        }
      )
      req.on('timeout', () => {
        req.destroy()
        if (Date.now() - started > timeoutMs) return resolve(false)
        setTimeout(attempt, 500)
      })
      req.on('error', () => {
        if (Date.now() - started > timeoutMs) return resolve(false)
        setTimeout(attempt, 500)
      })
      req.end()
    }
    attempt()
  })
}

function resolvePythonExec(backendDir) {
  const pythonFromEnv = (process.env.PYTHON_EXECUTABLE || '').trim()
  if (pythonFromEnv) return pythonFromEnv

  const bundled =
    process.platform === 'win32'
      ? path.join(backendDir, '.venv', 'Scripts', 'python.exe')
      : path.join(backendDir, '.venv', 'bin', 'python')
  try {
    if (fs.existsSync(bundled)) return bundled
  } catch (_) {}

  return 'python'
}

function buildChildEnv(backendDir, backendPortValue, mcpPortValue) {
  const envFilePath = path.join(backendDir, '.env')
  const dotenv = loadDotEnv(envFilePath)
  const dataDir = app.getPath('userData')
  const dbDir = path.join(dataDir, 'db')
  const uploadDir = path.join(dataDir, 'uploads')
  try {
    fs.mkdirSync(dbDir, { recursive: true })
  } catch (_) {}
  try {
    fs.mkdirSync(uploadDir, { recursive: true })
  } catch (_) {}
  const usersDbPath = path.join(dbDir, 'users.sqlite3')
  const sportsDbPath = path.join(dbDir, 'sports.sqlite3')
  const runtimeConfigPath = path.join(dataDir, 'runtime_config.json')
  const bundledRuntimeConfigPath = path.join(backendDir, 'data/runtime_config.json')
  try {
    if (!fs.existsSync(runtimeConfigPath)) {
      fs.mkdirSync(path.dirname(runtimeConfigPath), { recursive: true })
      const seed = { dashscope_api_key: '', xfyun_app_id: '', xfyun_api_key: '', xfyun_api_secret: '' }
      if (fs.existsSync(bundledRuntimeConfigPath)) {
        const bundled = JSON.parse(fs.readFileSync(bundledRuntimeConfigPath, 'utf8'))
        Object.assign(seed, bundled)
      }
      fs.writeFileSync(runtimeConfigPath, JSON.stringify(seed, null, 2), 'utf8')
    }
  } catch (err) {
    console.warn('[backend] runtime config seed failed', err)
  }
  return {
    ...process.env,
    ...dotenv,
    USERS_DATABASE_URL: `sqlite:///${usersDbPath.replace(/\\/g, '/')}`,
    SPORTS_DATABASE_URL: `sqlite:///${sportsDbPath.replace(/\\/g, '/')}`,
    REDIS_URL: 'memory://',
    UPLOAD_DIR: uploadDir,
    RUNTIME_CONFIG_PATH: runtimeConfigPath,
    PUBLIC_BASE_URL: `http://127.0.0.1:${backendPortValue}`,
    MCP_SERVER_URL: `http://127.0.0.1:${mcpPortValue}`
  }
}

function spawnPythonService(label, pythonExec, backendDir, childEnv, module, port) {
  const { spawn } = require('child_process')
  const child = spawn(
    pythonExec,
    ['-m', 'uvicorn', module, '--host', '127.0.0.1', '--port', String(port)],
    { cwd: backendDir, shell: false, stdio: 'pipe', env: childEnv }
  )
  child.on('error', (err) => {
    console.error(`[${label}] spawn error`, err)
  })
  child.stdout.on('data', (data) => {
    console.log(`[${label}] ${String(data || '')}`)
  })
  child.stderr.on('data', (data) => {
    console.error(`[${label}] ${String(data || '')}`)
  })
  child.on('exit', (code) => {
    console.log(`[${label}] exit ${code}`)
  })
  return child
}

function startServices() {
  const backendDir = app.isPackaged
    ? path.join(process.resourcesPath, 'backend')
    : path.join(__dirname, '../backend')
  const pythonExec = resolvePythonExec(backendDir)
  const childEnv = buildChildEnv(backendDir, backendPort, mcpPort)

  mcpProcess = spawnPythonService('mcp', pythonExec, backendDir, childEnv, 'app.mcp.server:app', mcpPort)
  backendProcess = spawnPythonService('backend', pythonExec, backendDir, childEnv, 'app.main:app', backendPort)
}

const CSP_HEADER =
  "default-src 'self'; script-src 'self' 'unsafe-eval' 'unsafe-inline' 'wasm-unsafe-eval' https://cdn.jsdelivr.net; connect-src 'self' http://127.0.0.1:* ws://127.0.0.1:* https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob: http://127.0.0.1:* https://static.exercisedb.dev; media-src 'self' blob: http://127.0.0.1:*; worker-src 'self' blob:;"

function setupContentSecurityPolicy() {
  session.defaultSession.webRequest.onHeadersReceived((details, callback) => {
    const headers = { ...details.responseHeaders }
    headers['Content-Security-Policy'] = [CSP_HEADER]
    callback({ responseHeaders: headers })
  })
}

async function injectRendererBootstrap(win) {
  await win.webContents.executeJavaScript(
    `
    (function () {
      window.__BACKEND_PORT__ = ${JSON.stringify(backendPort)};
      try { localStorage.setItem('__BACKEND_PORT__', ${JSON.stringify(String(backendPort))}); } catch (_) {}
      if (!location.hash || location.hash === '#') {
        location.hash = '#/';
      }
      return true;
    })();
    `,
    true
  )
}

async function createWindow() {
  const win = new BrowserWindow({
    width: 1280,
    height: 800,
    show: false,
    backgroundColor: '#111827',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true
    }
  })

  // packaged: ui is placed under resources/frontend/dist via extraResources
  const uiPath = app.isPackaged
    ? path.join(process.resourcesPath, 'frontend/dist/index.html')
    : path.join(__dirname, '../frontend/dist/index.html')

  try {
    await win.loadFile(uiPath, { query: { backendPort: String(backendPort) } })
    await injectRendererBootstrap(win)
    await new Promise((resolve) => setTimeout(resolve, 500))
    win.show()
    win.focus()
  } catch (err) {
    console.error('[electron] loadFile failed', err)
    win.show()
  }
}

app.whenReady().then(() => {
  setupContentSecurityPolicy()
  Promise.all([findFreePort(8000), findFreePort(9001)]).then(([apiPort, toolPort]) => {
    backendPort = apiPort
    mcpPort = toolPort
    startServices()
    Promise.all([
      waitForHttpReady(mcpPort, '/tools'),
      waitForHttpReady(backendPort, '/api/health', 45000)
    ]).then(([mcpReady, backendReady]) => {
      if (!backendReady) {
        console.error('[electron] backend failed to start, login/API will be unavailable')
      }
      if (!mcpReady) {
        console.warn('[electron] MCP service not ready, tool features may be limited')
      }
      createWindow()
    })
  })
})

app.on('window-all-closed', () => {
  if (backendProcess) {
    backendProcess.kill()
    backendProcess = null
  }
  if (mcpProcess) {
    mcpProcess.kill()
    mcpProcess = null
  }
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

