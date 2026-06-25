import axios from 'axios'

function resolveBaseUrl() {
  // Electron 打包后通过 file:// 打开页面时，使用本地后端地址
  if (typeof window !== 'undefined' && window.location?.protocol === 'file:') {
    const port =
      (window as any).__BACKEND_PORT__ ||
      localStorage.getItem('__BACKEND_PORT__') ||
      new URLSearchParams(window.location.search).get('backendPort')
    if (port) return `http://127.0.0.1:${port}/api`
    return 'http://127.0.0.1:8000/api'
  }
  return '/api'
}

export const http = axios.create({
  timeout: 30000
})

http.interceptors.request.use((config) => {
  // 每次请求动态解析，避免 Electron 启动时 __BACKEND_PORT__ 尚未注入导致连错端口（404）
  config.baseURL = resolveBaseUrl()
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})
