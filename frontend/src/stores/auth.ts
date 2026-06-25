import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { http } from '../api/http'
import { syncXfyunConfigToBackend } from '../utils/xfyunConfig'
import { syncVoiceTypeFromProfile } from '../utils/voice'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const role = ref(localStorage.getItem('role') || 'guest')

  const isLoggedIn = computed(() => Boolean(token.value))

  async function login(phone: string, password: string) {
    const { data } = await http.post('/auth/login', { phone, password })
    token.value = data.access_token
    role.value = data.role
    localStorage.setItem('token', token.value)
    localStorage.setItem('role', role.value)
    await syncVoiceTypeFromProfile()
    await syncXfyunConfigToBackend()
  }

  async function register(phone: string, password: string, userRole = 'user') {
    const { data } = await http.post('/auth/register', { phone, password, role: userRole })
    token.value = data.access_token
    role.value = data.role
    localStorage.setItem('token', token.value)
    localStorage.setItem('role', role.value)
    await syncVoiceTypeFromProfile()
    await syncXfyunConfigToBackend()
  }

  function logout() {
    token.value = ''
    role.value = 'guest'
    localStorage.removeItem('token')
    localStorage.removeItem('role')
  }

  return { token, role, isLoggedIn, login, register, logout }
})
