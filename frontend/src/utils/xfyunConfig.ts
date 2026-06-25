import { http } from '../api/http'

const APP_ID_KEY = 'xfyun_app_id'
const API_KEY_KEY = 'xfyun_api_key'
const API_SECRET_KEY = 'xfyun_api_secret'

export function getStoredXfyunConfig() {
  return {
    app_id: String(localStorage.getItem(APP_ID_KEY) || '').trim(),
    api_key: String(localStorage.getItem(API_KEY_KEY) || '').trim(),
    api_secret: String(localStorage.getItem(API_SECRET_KEY) || '').trim()
  }
}

export function storeXfyunConfig(appId: string, apiKey: string, apiSecret: string) {
  try {
    localStorage.setItem(APP_ID_KEY, String(appId || '').trim())
    if (apiKey) localStorage.setItem(API_KEY_KEY, String(apiKey).trim())
    if (apiSecret) localStorage.setItem(API_SECRET_KEY, String(apiSecret).trim())
  } catch {
    // ignore
  }
}

export async function syncXfyunConfigToBackend() {
  const stored = getStoredXfyunConfig()
  if (!stored.app_id || !stored.api_key || !stored.api_secret) {
    return false
  }
  try {
    await http.post('/config/xfyun', stored)
    return true
  } catch {
    return false
  }
}
