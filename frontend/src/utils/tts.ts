import { http } from '../api/http'
import { getVoiceType } from './voice'

let currentAudio: HTMLAudioElement | null = null
let currentBlobUrl: string | null = null
let speaking = false
let pendingSpeak: { text: string; voiceType: string } | null = null

const MALE_VOICE_IDS = new Set([
  'aisjiuxu',
  'xiaoyu',
  'xiaofeng',
  'longxiaocheng',
  'x4_qige',
  'x2_qige',
  'x4_lingfeizhe_emo',
  'x4_lingfeizhe_oral',
  'x4_lingfeizhe_assist',
  'x6_feizheChat_pro'
])

function getBackendPort() {
  if (typeof window === 'undefined') return '8000'
  return (
    String((window as any).__BACKEND_PORT__ || '') ||
    localStorage.getItem('__BACKEND_PORT__') ||
    new URLSearchParams(window.location.search).get('backendPort') ||
    '8000'
  )
}

function resolveAssetUrl(path: string) {
  if (!path) return ''
  if (/^https?:\/\//i.test(path)) {
    if (typeof window !== 'undefined' && window.location?.protocol === 'file:') {
      const port = getBackendPort()
      return path.replace(/^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?/i, `http://127.0.0.1:${port}`)
    }
    return path
  }
  if (typeof window !== 'undefined' && window.location?.protocol === 'file:') {
    const port = getBackendPort()
    return `http://127.0.0.1:${port}${path.startsWith('/') ? path : `/${path}`}`
  }
  return path.startsWith('/') ? path : `/${path}`
}

function revokeCurrentBlobUrl() {
  if (currentBlobUrl) {
    URL.revokeObjectURL(currentBlobUrl)
    currentBlobUrl = null
  }
}

function stopCurrentAudio() {
  currentAudio?.pause()
  currentAudio = null
  revokeCurrentBlobUrl()
}

export function stopTts() {
  stopCurrentAudio()
  window.speechSynthesis?.cancel()
  pendingSpeak = null
}

async function playBlob(blob: Blob): Promise<boolean> {
  stopCurrentAudio()
  window.speechSynthesis?.cancel()
  try {
    const blobUrl = URL.createObjectURL(blob)
    currentBlobUrl = blobUrl
    const audio = new Audio(blobUrl)
    currentAudio = audio
    audio.onended = () => revokeCurrentBlobUrl()
    await audio.play()
    return true
  } catch {
    revokeCurrentBlobUrl()
    return false
  }
}

export async function playAudioBase64(audioBase64: string): Promise<boolean> {
  const raw = String(audioBase64 || '').trim()
  if (!raw) return false
  try {
    const binary = atob(raw)
    const bytes = new Uint8Array(binary.length)
    for (let i = 0; i < binary.length; i += 1) {
      bytes[i] = binary.charCodeAt(i)
    }
    return playBlob(new Blob([bytes], { type: 'audio/mpeg' }))
  } catch {
    return false
  }
}

export async function playAudioUrl(audioUrl: string): Promise<boolean> {
  const src = resolveAssetUrl(audioUrl)
  if (!src) return false
  try {
    const response = await fetch(src)
    if (!response.ok) return false
    return playBlob(await response.blob())
  } catch {
    return false
  }
}

async function playTtsPayload(data: { audio_base64?: string; audio_url?: string }) {
  if (data?.audio_base64 && (await playAudioBase64(data.audio_base64))) {
    return true
  }
  if (data?.audio_url && (await playAudioUrl(data.audio_url))) {
    return true
  }
  return false
}

export async function synthesizeAndPlay(text: string, voiceType?: string) {
  const content = String(text || '').trim()
  if (!content) {
    throw new Error('播报文本为空')
  }
  const voice = voiceType || getVoiceType()
  const { data } = await http.post('/config/xfyun/preview', { text: content, voice_type: voice })
  if (!(await playTtsPayload(data))) {
    throw new Error('音频播放失败，请重试')
  }
  return data
}

function pickBrowserVoice(voiceType: string): SpeechSynthesisVoice | null {
  const voices = window.speechSynthesis?.getVoices() || []
  if (!voices.length) return null

  const zhVoices = voices.filter((voice) => /zh|cmn|chi|yue/i.test(voice.lang))
  const pool = zhVoices.length ? zhVoices : voices
  const wantMale = MALE_VOICE_IDS.has(voiceType)

  const maleHints = /(kangkang|yun|feng|hao|male|男|男声)/i
  const femaleHints = /(huihui|yaoyao|xiao|yan|ting|female|女|女声)/i

  const matched = pool.find((voice) => {
    const label = `${voice.name} ${voice.voiceURI}`
    if (wantMale) return maleHints.test(label)
    return femaleHints.test(label)
  })
  if (matched) return matched

  const fallback = pool.find((voice) => {
    const label = `${voice.name} ${voice.voiceURI}`
    if (wantMale) return !femaleHints.test(label)
    return !maleHints.test(label)
  })
  return fallback || pool[0] || null
}

function speakWithBrowser(text: string, voiceType?: string) {
  if (!window.speechSynthesis) return
  window.speechSynthesis.cancel()

  const speak = () => {
    const utterance = new SpeechSynthesisUtterance(text)
    utterance.lang = 'zh-CN'
    const browserVoice = pickBrowserVoice(voiceType || getVoiceType())
    if (browserVoice) utterance.voice = browserVoice
    window.speechSynthesis.speak(utterance)
  }

  const voices = window.speechSynthesis.getVoices()
  if (voices.length) {
    speak()
    return
  }
  window.speechSynthesis.onvoiceschanged = () => {
    window.speechSynthesis.onvoiceschanged = null
    speak()
  }
}

async function speakTextOnce(text: string, voiceType: string) {
  const content = String(text || '').trim()
  if (!content) return false

  try {
    await synthesizeAndPlay(content, voiceType)
    return true
  } catch {
    speakWithBrowser(content, voiceType)
    return false
  }
}

export async function speakText(text: string, options?: { voiceType?: string }) {
  const content = String(text || '').trim()
  if (!content) return false

  const voiceType = options?.voiceType || getVoiceType()
  if (speaking) {
    pendingSpeak = { text: content, voiceType }
    return false
  }

  speaking = true
  let ok = false
  try {
    ok = await speakTextOnce(content, voiceType)
  } finally {
    speaking = false
    const next = pendingSpeak
    pendingSpeak = null
    if (next) {
      void speakText(next.text, { voiceType: next.voiceType })
    }
  }
  return ok
}
