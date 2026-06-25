<template>
  <section class="home-stage">
    <div class="home-frame" :class="{ visitor: mode === 'guest' }">
      <div v-if="auth.isLoggedIn && mode === 'home'" class="already-logged-in">
        <p class="hint">您已经登录，可以直接进入系统</p>
        <el-button class="dashboard-entry" @click="router.push('/dashboard')">进入我的训练</el-button>
      </div>

      <div v-else-if="mode === 'home'" class="landing-buttons">
        <el-button class="big-entry login" @click="handleLoginClick">登录</el-button>
        <el-button class="big-entry register" @click="handleRegisterClick">注册</el-button>
        <el-button class="big-entry guest" @click="enterGuest">访客</el-button>
      </div>

      <template v-else-if="mode === 'login' || mode === 'register'">
        <div class="auth-layout">
          <div class="auth-box">
            <el-form label-position="top" @submit.prevent>
              <el-form-item label="手机号/管理员账号">
                <el-input v-model="phone" placeholder="请输入手机号或管理员账号" />
              </el-form-item>
              <el-form-item label="密码">
                <el-input v-model="password" type="password" show-password placeholder="请输入密码" />
              </el-form-item>
            </el-form>
          </div>

          <div class="side-actions">
            <el-button class="small-entry login" :class="{ active: mode === 'login' }" :loading="loading && mode === 'login'" @click="handleLoginClick">登录</el-button>
            <el-button class="small-entry register" :class="{ active: mode === 'register' }" :loading="loading && mode === 'register'" @click="handleRegisterClick">注册</el-button>
            <el-button class="small-entry guest" :class="{ active: mode === 'guest' }" @click="enterGuest">访客</el-button>
          </div>
        </div>
      </template>

      <template v-else>
        <div class="guest-hero">
          <div class="home-copy">
        <h1>面向多角色的智能健身教练系统</h1>
            <p>访客模式仅支持浏览功能介绍，完整训练、姿态分析和问答需要登录后使用。</p>
          </div>
          <div class="side-actions guest-actions">
            <el-button class="small-entry login" @click="handleLoginClick">登录</el-button>
            <el-button class="small-entry register" @click="handleRegisterClick">注册</el-button>
            <el-button class="small-entry guest active" @click="enterGuest">访客</el-button>
          </div>
        </div>

        <div class="guest-tip">当前为访客浏览状态：可以查看功能说明，但不能进入完整训练、姿态分析和健身问答。</div>
        <div class="guest-grid">
          <el-card v-for="item in features" :key="item.title" class="guest-card">
            <h3>{{ item.title }}</h3>
            <p class="muted">{{ item.desc }}</p>
            <el-button disabled>登录后使用</el-button>
          </el-card>
        </div>
      </template>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import { http } from '../../api/http'
import { useAuthStore } from '../../stores/auth'

type HomeMode = 'home' | 'login' | 'register' | 'guest'

const auth = useAuthStore()
const router = useRouter()
const mode = ref<HomeMode>('home')
const loading = ref(false)
const phone = ref('')
const password = ref('')

const features = [
  { title: '多级管理', desc: '支持管理员、普通用户和访客模式。' },
  { title: '个性化推荐', desc: '根据问卷生成训练计划，并保存历史记录。' },
  { title: '姿态分析', desc: '基于MediaPipe关键点进行动作识别、纠错和评分。' },
  { title: '健身问答', desc: '文字或语音提问，结合本地知识库和大模型回答。' }
]

async function handleLoginClick() {
  if (mode.value !== 'login') {
    mode.value = 'login'
    return
  }
  await submit('login')
}

async function handleRegisterClick() {
  if (mode.value !== 'register') {
    mode.value = 'register'
    return
  }
  await submit('register')
}

function enterGuest() {
  mode.value = 'guest'
}

async function submit(action: 'login' | 'register') {
  if (!phone.value || !password.value) {
    ElMessage.warning('请输入账号和密码')
    return
  }
  loading.value = true
  try {
    if (action === 'login') {
      await auth.login(phone.value, password.value)
    } else {
      await http.post('/auth/register', { phone: phone.value, password: password.value, role: 'user' })
      ElMessage.success('注册成功，请登录')
      mode.value = 'login'
      password.value = ''
      return
    }
    ElMessage.success('登录成功')
    router.push('/dashboard')
  } catch (error: any) {
    const status = error?.response?.status
    const detail = error?.response?.data?.detail
    if (status === 403) {
      ElMessage.warning({
        message: detail || '账号已被禁用',
        duration: 5000,
        showClose: true
      })
    } else if (!error?.response) {
      ElMessage.error('无法连接后端服务，请完全退出后重新启动 FitnessCoach')
    } else {
      ElMessage.error(detail || '操作失败')
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.home-stage {
  min-height: calc(100vh - 116px);
  display: flex;
  justify-content: center;
  padding: 48px 16px;
}

.home-frame {
  width: min(1120px, 100%);
  min-height: 600px;
  border: 1px solid rgba(148, 163, 184, 0.5);
  background: var(--bg-gradient);
  box-shadow: var(--shadow);
  position: relative;
}

.landing-buttons {
  position: absolute;
  top: 50%;
  left: 50%;
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 34px;
  transform: translate(-50%, -50%);
}

.big-entry {
  width: 240px;
  height: 64px;
  border: 0;
  border-radius: 0;
  color: #fff;
  font-size: 32px;
  font-weight: 700;
}

.login {
  background: #4774c5;
}

.register {
  background: #70ad47;
}

.guest {
  background: #ffc000;
}

.auth-layout {
  min-height: 520px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 46px;
}

.auth-box {
  width: 460px;
  padding: 34px 52px 14px;
  border: 1px solid #cbd5e1;
  background: rgba(255, 255, 255, 0.78);
}

.side-actions {
  display: flex;
  flex-direction: column;
  gap: 26px;
}

.small-entry {
  width: 160px;
  height: 36px;
  border: 0;
  border-radius: 0;
  color: #fff;
  font-size: 24px;
  font-weight: 700;
  margin-left: 0 !important;
  transition: width 0.2s ease, height 0.2s ease, transform 0.2s ease;
}

.small-entry.active {
  width: 190px;
  height: 44px;
  transform: translateX(-15px);
}

.guest-hero {
  min-height: 320px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 78px 0 30px;
  color: #fff;
  background: linear-gradient(135deg, rgba(63, 111, 198, 0.98), rgba(91, 141, 225, 0.88));
}

.home-copy {
  max-width: 640px;
  font-weight: 700;
}

.guest-tip {
  margin: 20px 22px;
  padding: 14px 18px;
  border: 1px solid #bfdbfe;
  border-radius: 14px;
  color: #1d4ed8;
  background: rgba(239, 246, 255, 0.85);
}

.guest-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 22px;
  padding: 0 22px 28px;
}

.guest-card {
  min-height: 150px;
}

.already-logged-in {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
}

.already-logged-in .hint {
  margin: 0 0 24px;
  font-size: 18px;
  color: #334155;
}

.dashboard-entry {
  width: 280px;
  height: 70px;
  background: linear-gradient(135deg, #4774c5, #5b8de1);
  color: #fff;
  font-size: 28px;
  font-weight: 700;
  border: 0;
  border-radius: 8px;
}
</style>
