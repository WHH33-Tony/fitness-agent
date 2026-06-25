<template>
  <el-container class="app-shell">
    <el-header class="topbar">
      <div class="brand" @click="backHome">智能健身教练系统</div>
      <el-menu v-if="auth.isLoggedIn" mode="horizontal" router :ellipsis="false" class="nav">
        <el-menu-item index="/dashboard">我的训练</el-menu-item>
        <el-menu-item index="/pose">姿态分析</el-menu-item>
        <el-menu-item index="/qa">健身问答</el-menu-item>
        <el-menu-item index="/exercise">运动消耗</el-menu-item>
        <el-menu-item index="/nutrition">营养计算</el-menu-item>
        <el-menu-item index="/movements">动作列表</el-menu-item>
        <el-menu-item index="/profile">个人中心</el-menu-item>
        <el-menu-item v-if="auth.role !== 'admin'" index="/feedback">我的反馈</el-menu-item>
        <el-menu-item v-if="auth.role === 'admin'" index="/admin">管理控制台</el-menu-item>
      </el-menu>
      <div v-else class="nav-spacer"></div>
      <el-button v-if="auth.isLoggedIn" @click="logout">退出</el-button>
    </el-header>
    <el-main>
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'

import { http } from './api/http'
import { useAuthStore } from './stores/auth'
import { syncXfyunConfigToBackend } from './utils/xfyunConfig'
import { syncVoiceTypeFromProfile } from './utils/voice'

const auth = useAuthStore()
const router = useRouter()

onMounted(async () => {
  if (auth.isLoggedIn) {
    void syncVoiceTypeFromProfile()
  }

  try {
    await syncXfyunConfigToBackend()
  } catch {
    // 后端尚未就绪时忽略
  }

  const key = String(localStorage.getItem('dashscope_api_key') || '').trim()
  if (!key) return
  try {
    await http.post('/config/apikey', { dashscope_api_key: key })
  } catch {
    // 后端尚未就绪时忽略，管理员保存后也会写入
  }
})

function logout() {
  auth.logout()
  router.push('/')
}

function backHome() {
  auth.logout()
  router.push('/')
}
</script>
