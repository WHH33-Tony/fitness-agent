<template>
  <section class="page profile-page">
    <h1 class="page-title">我的信息</h1>
    <div class="panel profile-panel">
      <el-form label-position="top">
        <el-form-item label="昵称"><el-input v-model="profile.nickname" /></el-form-item>
        <el-form-item label="身高(cm)"><el-input-number v-model="profile.height" :min="80" /></el-form-item>
        <el-form-item label="体重(kg)"><el-input-number v-model="profile.weight" :min="20" /></el-form-item>
        <el-form-item label="年龄"><el-input-number v-model="profile.age" :min="1" /></el-form-item>
        <el-form-item label="性别">
          <el-select v-model="profile.gender">
            <el-option label="未知" value="unknown" />
            <el-option label="男" value="male" />
            <el-option label="女" value="female" />
          </el-select>
        </el-form-item>
        <el-form-item label="语音播报音色（讯飞）">
          <div class="voice-row">
            <el-select v-model="profile.voice_type" style="width: 100%; max-width: 420px">
              <el-option-group label="基础发音人">
                <el-option
                  v-for="v in basicVoices"
                  :key="v.id"
                  :label="`${v.name}（${v.desc}）`"
                  :value="v.id"
                />
              </el-option-group>
              <el-option-group label="特色发音人">
                <el-option
                  v-for="v in specialVoices"
                  :key="v.id"
                  :label="`${v.name}（${v.desc}）`"
                  :value="v.id"
                />
              </el-option-group>
            </el-select>
            <el-button :loading="previewing" @click="previewVoice">试听音色</el-button>
          </div>
        </el-form-item>
        <el-button type="primary" @click="saveProfile">保存信息</el-button>
      </el-form>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { computed, onMounted, reactive, ref } from 'vue'

import { DEFAULT_VOICES, type VoiceOption } from '../../constants/voices'
import { http } from '../../api/http'
import { synthesizeAndPlay } from '../../utils/tts'
import { setVoiceType } from '../../utils/voice'

const voices = ref<VoiceOption[]>(DEFAULT_VOICES)
const previewing = ref(false)
const basicVoices = computed(() => voices.value.filter((v) => v.tier !== 'special'))
const specialVoices = computed(() => voices.value.filter((v) => v.tier === 'special'))
const profile = reactive({ nickname: '', height: 170, weight: 65, gender: 'unknown', age: 22, voice_type: 'xiaoyan' })

async function loadProfile() {
  Object.assign(profile, (await http.get('/users/profile')).data)
  setVoiceType(profile.voice_type)
  await importProfileFromLatestPlan()
}

async function saveProfile() {
  await http.put('/users/profile', profile)
  setVoiceType(profile.voice_type)
  ElMessage.success('已保存')
}

async function previewVoice() {
  previewing.value = true
  try {
    const data = await synthesizeAndPlay('您好，这是您当前选择的语音播报音色。', profile.voice_type)
    ElMessage.success(`讯飞音色播放成功（${data?.vcn || profile.voice_type}）`)
  } catch (e: any) {
    ElMessage.error(`讯飞试听失败：${e?.response?.data?.detail || e?.message || '未知错误'}`)
  } finally {
    previewing.value = false
  }
}

async function importProfileFromLatestPlan() {
  const plans = (await http.get('/plans')).data
  const extraInfo = plans[0]?.plan_data?.extra_info
  if (!extraInfo) {
    return
  }
  if (!profile.height || profile.height === 170) {
    profile.height = extraInfo.height ?? profile.height
  }
  if (!profile.weight || profile.weight === 65) {
    profile.weight = extraInfo.weight ?? profile.weight
  }
  if (!profile.age || profile.age === 22) {
    profile.age = extraInfo.age ?? profile.age
  }
  if (!profile.gender || profile.gender === 'unknown') {
    profile.gender = normalizeGender(extraInfo.gender)
  }
}

function normalizeGender(gender: string) {
  if (gender === '男' || gender === 'male') {
    return 'male'
  }
  if (gender === '女' || gender === 'female') {
    return 'female'
  }
  return 'unknown'
}

async function loadVoices() {
  try {
    const { data } = await http.get('/config/xfyun/voices')
    if (Array.isArray(data) && data.length) voices.value = data
  } catch (_) {
    voices.value = DEFAULT_VOICES
  }
}

onMounted(async () => {
  await Promise.all([loadProfile(), loadVoices()])
})
</script>

<style scoped>
.profile-panel {
  width: 100%;
  margin: 0 auto;
  padding: 28px 40px 42px;
  box-sizing: border-box;
}

.profile-panel :deep(.el-input),
.profile-panel :deep(.el-select) {
  max-width: 900px;
}

.profile-panel :deep(.el-input-number) {
  width: 220px;
}

.voice-row {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
  width: 100%;
  max-width: 560px;
}
</style>
