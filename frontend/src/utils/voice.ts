import { http } from '../api/http'

const VOICE_TYPE_KEY = 'voice_type'
const DEFAULT_VOICE_TYPE = 'xiaoyan'

export function getVoiceType(): string {
  try {
    const value = String(localStorage.getItem(VOICE_TYPE_KEY) || '').trim()
    return value || DEFAULT_VOICE_TYPE
  } catch {
    return DEFAULT_VOICE_TYPE
  }
}

export function setVoiceType(voiceType: string) {
  try {
    const value = String(voiceType || DEFAULT_VOICE_TYPE).trim() || DEFAULT_VOICE_TYPE
    localStorage.setItem(VOICE_TYPE_KEY, value)
  } catch {
    // ignore
  }
}

export async function syncVoiceTypeFromProfile() {
  try {
    if (!localStorage.getItem('token')) return
    const { data } = await http.get('/users/profile')
    if (data?.voice_type) {
      setVoiceType(data.voice_type)
    }
  } catch {
    // ignore
  }
}

