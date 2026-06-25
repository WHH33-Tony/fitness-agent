<template>
  <section class="page qa-page">
    <h1 class="page-title">健身问答</h1>
    <div class="panel qa-panel">
      <el-input v-model="question" class="question-box" type="textarea" :rows="5" placeholder="输入健身问题，例如：我想减脂，每周怎么练？" />
      <div class="qa-actions">
        <el-button type="primary" :loading="loading" @click="ask">提问</el-button>
        <el-button type="primary" :loading="voiceLoading" @click="toggleVoice">{{ recording ? '识别中...' : '语音提问' }}</el-button>
        <el-upload v-if="auth.role === 'admin'" :http-request="uploadKnowledge" :show-file-list="false" accept=".txt,.md,.pdf">
          <el-button>上传知识库文件</el-button>
        </el-upload>
      </div>
      <p v-if="recording || voiceLoading" class="voice-status">{{ recording ? '正在听你说话，请直接说出问题...' : '正在根据识别结果生成回答，请稍等...' }}</p>
    </div>
    <div v-if="auth.role === 'admin'" class="panel qa-panel" style="margin-top: 18px">
      <div style="display: flex; align-items: center; justify-content: space-between; gap: 12px">
        <h3 style="margin: 0">知识库文件管理</h3>
        <el-button size="small" :loading="kbLoading" @click="loadKnowledgeFiles">刷新</el-button>
      </div>
      <el-table v-loading="kbLoading" :data="kbFiles" stripe style="width: 100%; margin-top: 12px">
        <el-table-column prop="filename" label="文件名" min-width="260" />
        <el-table-column prop="size" label="大小" width="120">
          <template #default="{ row }">
            <span>{{ formatBytes(row.size) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="modified_at" label="修改时间" width="170">
          <template #default="{ row }">
            <span>{{ formatKbModifiedTime(row.modified_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button size="small" type="danger" @click.stop="deleteKnowledge(row.filename)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <p v-if="!kbLoading && !kbFiles.length" class="muted" style="margin-top: 10px">暂无知识库文件</p>
    </div>
    <div v-if="answer" class="panel answer-panel current-answer-panel">
      <h3 class="current-answer-title">回答</h3>
      <QAAnswerContent :text="answer" :meal-plan="mealPlan" :weather="weather" />
      <div v-if="answerMode || sources.length" class="sources-panel">
        <div v-if="answerMode === 'llm'" class="sources-mode sources-mode-llm">
          回答模式：大模型（未引用本地知识库）
        </div>
        <template v-else-if="sources.length">
          <div class="sources-mode sources-mode-local">回答模式：本地知识库</div>
          <ul class="sources-list">
            <li v-for="(src, idx) in sources" :key="idx" class="sources-item">{{ src }}</li>
          </ul>
        </template>
      </div>
    </div>
    <div v-if="auth.isLoggedIn" class="history-panel">
      <el-collapse v-model="historySectionOpen" class="history-outer-collapse">
        <el-collapse-item name="history">
          <template #title>
            <span class="history-outer-title">历史问答</span>
          </template>
          <div v-loading="historyLoading" class="history-outer-body">
            <div class="history-toolbar">
              <span class="muted">最近 30 条</span>
              <el-button size="small" link :loading="historyLoading" @click.stop="loadHistory">刷新</el-button>
            </div>
            <p v-if="!historyLoading && !history.length" class="muted history-empty">暂无历史记录</p>
            <el-collapse v-else v-model="expandedHistoryItems" class="history-list-collapse">
              <el-collapse-item v-for="item in history" :key="item.id" :name="item.id">
                <template #title>
                  <div class="history-item-head">
                    <div class="history-item-meta">
                      {{ formatIntentLabel(item.intent) }} {{ formatBeijingDateTime(item.created_at) }}
                    </div>
                    <div class="history-q-line">Q：{{ item.question }}</div>
                  </div>
                </template>
                <div class="history-a-body">
                  <div class="history-a-prefix">A：</div>
                  <QAAnswerContent
                    class="history-answer"
                    :text="item.answer"
                    :meal-plan="item.meal_plan"
                    :weather="item.weather"
                  />
                </div>
              </el-collapse-item>
            </el-collapse>
          </div>
        </el-collapse-item>
      </el-collapse>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import QAAnswerContent from '../../components/QAAnswerContent.vue'
import { formatBeijingDateTime } from '../../utils/datetime'
import { http } from '../../api/http'
import { useAuthStore } from '../../stores/auth'
import { getDisplayAnswerText, parseMealPlanFromAnswer, type MealPlan } from '../../utils/qaAnswer'
import { speakText } from '../../utils/tts'
import { blobToPcm16kMono } from '../../utils/audio'
import { getVoiceType } from '../../utils/voice'

const auth = useAuthStore()
const route = useRoute()
const question = ref('减脂期间应该如何安排力量训练和有氧？')
const answer = ref('')
const mealPlan = ref<MealPlan | null>(null)
const weather = ref<any>(null)
const sources = ref<string[]>([])
const answerMode = ref('')
const loading = ref(false)
const voiceLoading = ref(false)
const recording = ref(false)
const mediaRecorder = ref<MediaRecorder | null>(null)
const recordedChunks = ref<BlobPart[]>([])
const mediaStream = ref<MediaStream | null>(null)
const history = ref<any[]>([])
const historyLoading = ref(false)
const historySectionOpen = ref<string[]>([])
const expandedHistoryItems = ref<Array<string | number>>([])
const kbFiles = ref<any[]>([])
const kbLoading = ref(false)

async function ask() {
  loading.value = true
  try {
    const { data } = await http.post('/qa', { question: question.value, voice_type: getVoiceType() })
    answer.value = data.answer
    mealPlan.value = data.meal_plan || parseMealPlanFromAnswer(data.answer).mealPlan
    weather.value = data.weather || null
    sources.value = data.sources || []
    answerMode.value = data.answer_mode || ''
    await loadHistory()
    await speakText(getDisplayAnswerText(data.answer, Boolean(mealPlan.value)), { voiceType: getVoiceType() })
  } catch (e: any) {
    console.error('QA ask error:', {
      message: e?.message,
      status: e?.response?.status,
      data: e?.response?.data
    })
    ElMessage.error(`提问失败：${e?.response?.data?.detail || e?.message || '未知错误'}`)
  } finally {
    loading.value = false
  }
}

function formatIntentLabel(intent: string) {
  const raw = String(intent || 'unknown').trim()
  if (!raw) return 'Unknown'
  return raw.charAt(0).toUpperCase() + raw.slice(1).toLowerCase()
}

async function loadHistory() {
  if (!auth.isLoggedIn) {
    history.value = []
    return
  }
  historyLoading.value = true
  try {
    const { data } = await http.get('/qa/history', { params: { limit: 30 } })
    history.value = Array.isArray(data) ? data : []
  } catch (e: any) {
    history.value = []
    const status = e?.response?.status
    console.error('QA history error:', {
      status,
      message: e?.message,
      config: e?.config,
      response: e?.response?.data
    })
    if (status === 404 || status === 401) {
      console.log('QA history endpoint returned', status)
    } else {
      ElMessage.warning(`加载历史问答失败：${e?.message || '未知错误'}`)
    }
  } finally {
    historyLoading.value = false
  }
}

function stopMediaStream() {
  try {
    mediaStream.value?.getTracks().forEach((track) => track.stop())
  } catch (_) {
    // ignore
  }
  mediaStream.value = null
}

async function submitVoiceRecording(blob: Blob) {
  if (!blob.size) {
    ElMessage.warning('没有录到音频，请再试一次')
    return
  }
  voiceLoading.value = true
  try {
    const pcmBlob = await blobToPcm16kMono(blob)
    const form = new FormData()
    form.append('audio', pcmBlob, 'voice.pcm')
    const { data } = await http.post('/qa/voice', form, { headers: { 'Content-Type': 'multipart/form-data' } })
    question.value = data.question || question.value
    answer.value = data.answer
    mealPlan.value = data.meal_plan || parseMealPlanFromAnswer(data.answer).mealPlan
    weather.value = data.weather || null
    sources.value = data.sources || []
    answerMode.value = data.answer_mode || ''
    await loadHistory()
    await speakText(getDisplayAnswerText(data.answer, Boolean(mealPlan.value)), { voiceType: getVoiceType() })
  } catch (e: any) {
    const detail = e?.response?.data?.detail
    ElMessage.error(typeof detail === 'string' ? detail : '语音识别失败，请检查管理端讯飞配置或麦克风权限')
  } finally {
    voiceLoading.value = false
  }
}

async function toggleVoice() {
  if (recording.value) {
    if (mediaRecorder.value && mediaRecorder.value.state !== 'inactive') {
      mediaRecorder.value.stop()
    }
    return
  }

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false })
    mediaStream.value = stream
    recordedChunks.value = []
    const mr = new MediaRecorder(stream)
    mediaRecorder.value = mr
    mr.ondataavailable = (e) => {
      if (e.data && e.data.size > 0) recordedChunks.value.push(e.data)
    }
    mr.onstart = () => {
      recording.value = true
    }
    mr.onstop = async () => {
      recording.value = false
      stopMediaStream()
      const blob = new Blob(recordedChunks.value, { type: mr.mimeType || 'audio/webm' })
      await submitVoiceRecording(blob)
    }
    mr.onerror = () => {
      recording.value = false
      stopMediaStream()
      ElMessage.error('录音失败，请检查麦克风设备')
    }
    mr.start()
    ElMessage.info('正在录音，再次点击「识别中...」结束并识别')
  } catch (e: any) {
    stopMediaStream()
    const denied = e?.name === 'NotAllowedError' || e?.name === 'PermissionDeniedError'
    ElMessage.error(denied ? '麦克风权限被拒绝，请在系统设置中允许应用使用麦克风' : '无法启动录音，请检查麦克风设备')
  }
}

async function uploadKnowledge(option: any) {
  const form = new FormData()
  form.append('file', option.file)
  await http.post('/qa/knowledge', form)
  ElMessage.success('知识库文件已上传')
  await loadKnowledgeFiles()
}

function formatKbModifiedTime(timestamp: number | string | null | undefined) {
  const raw = Number(timestamp ?? 0)
  if (!Number.isFinite(raw) || raw <= 0) return ''
  const ms = raw > 1e12 ? raw : raw * 1000
  return formatBeijingDateTime(new Date(ms))
}

function formatBytes(size: any) {
  const n = Number(size ?? 0)
  if (!Number.isFinite(n) || n <= 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let idx = 0
  let value = n
  while (value >= 1024 && idx < units.length - 1) {
    value /= 1024
    idx += 1
  }
  return `${value.toFixed(idx === 0 ? 0 : 1)} ${units[idx]}`
}

async function loadKnowledgeFiles() {
  if (auth.role !== 'admin') return
  kbLoading.value = true
  try {
    const { data } = await http.get('/qa/knowledge')
    kbFiles.value = Array.isArray(data) ? data : []
  } catch (e: any) {
    kbFiles.value = []
    ElMessage.warning(`加载知识库文件失败：${e?.message || '未知错误'}`)
  } finally {
    kbLoading.value = false
  }
}

async function deleteKnowledge(filename: string) {
  if (!filename) return
  try {
    await http.delete(`/qa/knowledge/${encodeURIComponent(filename)}`)
    ElMessage.success('已删除')
    await loadKnowledgeFiles()
  } catch (e: any) {
    ElMessage.error(`删除失败：${e?.response?.data?.detail || e?.message || '未知错误'}`)
  }
}

onMounted(() => {
  const q = String(route.query.q || '')
  if (q) {
    question.value = q
  }
  if (auth.isLoggedIn) {
    loadHistory()
  }
  if (auth.role === 'admin') {
    loadKnowledgeFiles()
  }
})
</script>

<style scoped>
.qa-page {
  overflow-y: auto;
  padding-bottom: 28px;
}

.qa-panel {
  width: 100%;
  margin: 0 auto;
  padding: 42px 70px 50px;
  box-sizing: border-box;
}

.question-box :deep(textarea) {
  min-height: 128px !important;
  border-radius: 18px;
  padding: 28px 34px;
}

.qa-actions {
  display: flex;
  gap: 46px;
  margin-top: 52px;
  padding-left: 18px;
}

.voice-status {
  margin: 18px 0 0 18px;
  color: #2563eb;
  font-weight: 700;
}

.qa-actions :deep(.el-button) {
  width: 120px;
  border-radius: 16px;
  background: #22b8e6;
  border-color: #22b8e6;
}

.answer-panel {
  width: 100%;
  margin: 20px auto 0;
  padding: 28px 42px;
  box-sizing: border-box;
}

.current-answer-panel {
  border-left: 4px solid #22b8e6;
  background: rgba(255, 255, 255, 0.96);
}

.current-answer-title {
  margin: 0 0 14px;
  font-size: 18px;
  font-weight: 700;
  color: #0f172a;
}

.history-panel {
  width: 100%;
  margin: 14px auto 0;
  padding: 0;
  box-sizing: border-box;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 4px;
  box-shadow: 0 1px 4px rgba(15, 23, 42, 0.05);
  font-size: 13px;
  color: #475569;
  overflow: hidden;
}

.history-outer-collapse {
  border: none;
}

.history-outer-collapse :deep(.el-collapse-item__header) {
  height: 42px;
  line-height: 42px;
  padding: 0 16px;
  font-size: 14px;
  font-weight: 400;
  color: #1f2937;
  background: #fff;
  border-bottom: none;
}

.history-outer-collapse :deep(.el-collapse-item.is-active .el-collapse-item__header) {
  border-bottom: 1px solid #e5e7eb;
}

.history-outer-collapse :deep(.el-collapse-item__wrap) {
  background: #fff;
  border-bottom: none;
}

.history-outer-collapse :deep(.el-collapse-item__content) {
  padding: 0;
}

.history-outer-title {
  font-size: 14px;
  color: #1f2937;
}

.history-outer-body {
  padding: 0 16px 12px;
}

.history-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 0 6px;
  font-size: 12px;
}

.history-empty {
  margin: 6px 0 4px;
}

.history-list-collapse {
  border-top: 1px solid #e5e7eb;
  border-bottom: none;
}

.history-list-collapse :deep(.el-collapse-item__header) {
  height: auto;
  min-height: 52px;
  line-height: 1.45;
  padding: 10px 0;
  font-size: 13px;
  background: #fff;
  border-bottom: 1px solid #e5e7eb;
}

.history-list-collapse :deep(.el-collapse-item:last-child .el-collapse-item__header) {
  border-bottom: none;
}

.history-list-collapse :deep(.el-collapse-item__wrap) {
  background: #fff;
  border-bottom: 1px solid #e5e7eb;
}

.history-list-collapse :deep(.el-collapse-item:last-child .el-collapse-item__wrap) {
  border-bottom: none;
}

.history-list-collapse :deep(.el-collapse-item__content) {
  padding: 0 0 12px;
}

.history-item-head {
  width: calc(100% - 28px);
  min-width: 0;
}

.history-item-meta {
  font-size: 12px;
  color: #64748b;
  margin-bottom: 4px;
}

.history-q-line {
  font-size: 13px;
  color: #1f2937;
  word-break: break-word;
}

.history-a-body {
  padding: 4px 0 0;
}

.history-a-prefix {
  font-size: 13px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 6px;
}

.history-answer {
  margin-top: 4px;
}

.history-panel :deep(.history-answer .answer-text) {
  line-height: 1.65;
  font-size: 13px;
  color: #475569;
}

.history-panel :deep(.history-answer .answer-heading) {
  margin-top: 8px;
  margin-bottom: 6px;
  font-size: 13px;
  font-weight: 600;
  color: #334155;
}

.history-panel :deep(.history-answer .answer-line),
.history-panel :deep(.history-answer .answer-list) {
  margin-bottom: 6px;
  font-size: 13px;
}

.history-panel :deep(.history-answer .answer-list) {
  padding-left: 18px;
}

.muted {
  color: rgba(100, 116, 139, 0.95);
}

.sources-panel {
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px dashed #e2e8f0;
}

.sources-mode {
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 8px;
}

.sources-mode-llm {
  color: #7c3aed;
}

.sources-mode-local {
  color: #0d9488;
}

.sources-list {
  margin: 0;
  padding: 0;
  list-style: none;
}

.sources-item {
  font-size: 12px;
  line-height: 1.55;
  color: #64748b;
  padding: 8px 10px;
  margin-bottom: 6px;
  background: #f8fafc;
  border-radius: 6px;
  border-left: 3px solid #14b8a6;
  word-break: break-word;
  white-space: pre-wrap;
}
</style>
