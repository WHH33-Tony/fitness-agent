<template>
  <section class="page auth-page">
    <el-card class="auth-card">
      <h2>{{ isRegister ? '注册账号' : '登录系统' }}</h2>
      <el-form label-position="top">
        <el-form-item label="手机号/管理员账号">
          <el-input v-model="phone" placeholder="例如 18800000002 或 admin" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="password" type="password" show-password />
        </el-form-item>
        <el-form-item v-if="isRegister" label="角色">
          <el-radio-group v-model="role">
            <el-radio-button label="user">普通用户</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-button type="primary" :loading="loading" @click="submit">{{ isRegister ? '注册并登录' : '登录' }}</el-button>
        <el-button text @click="isRegister = !isRegister">{{ isRegister ? '已有账号，去登录' : '没有账号，去注册' }}</el-button>
      </el-form>
    </el-card>
  </section>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import { useAuthStore } from '../../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const isRegister = ref(false)
const loading = ref(false)
const phone = ref('')
const password = ref('')
const role = ref('user')

async function submit() {
  loading.value = true
  try {
    if (isRegister.value) {
      await auth.register(phone.value, password.value, role.value)
    } else {
      await auth.login(phone.value, password.value)
    }
    ElMessage.success('登录成功')
    router.push(auth.role === 'admin' ? '/admin' : '/dashboard')
  } catch (error: any) {
    const status = error?.response?.status
    const detail = error?.response?.data?.detail
    if (status === 403) {
      ElMessage.warning({
        message: detail || '账号已被禁用',
        duration: 5000,
        showClose: true
      })
    } else {
      ElMessage.error(detail || '操作失败')
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-page {
  display: flex;
  justify-content: center;
  padding-top: 48px;
}

.auth-card {
  width: 460px;
}
</style>
