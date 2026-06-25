<template>
  <section class="pose-view">
    <div class="picker-bar">
      <div class="picker-title">
        <span class="picker-label">选择动作</span>
        <span class="picker-hint">开启摄像头或上传视频后开始分析</span>
      </div>
      <div class="picker-actions">
        <el-select v-model="selectedMovement" filterable placeholder="请选择动作">
          <el-option v-for="item in movementOptions" :key="item" :label="item" :value="item" />
        </el-select>
        <el-button :loading="historyLoading" @click="openHistory">历史记录</el-button>
      </div>
    </div>
    <div class="analyzer-wrap">
      <PoseAnalyzer :movement-name="selectedMovement" @session-saved="loadHistory" />
    </div>
    <el-dialog v-model="historyVisible" title="姿态分析历史记录" width="760px">
      <div class="history-toolbar">
        <el-button size="small" :loading="historyLoading" @click="loadHistory">刷新</el-button>
      </div>
      <el-table v-loading="historyLoading" :data="history" stripe style="width: 100%">
        <el-table-column type="expand" width="48">
          <template #default="{ row }">
            <div class="history-expand">
              <div class="history-expand-row">
                <strong>指标</strong>
                <span>{{ formatMetrics(row.metrics) }}</span>
              </div>
              <div class="history-expand-row">
                <strong>问题</strong>
                <span>{{ formatList(row.errors) }}</span>
              </div>
              <div class="history-expand-row">
                <strong>建议</strong>
                <span>{{ formatList(row.suggestions) }}</span>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="时间" width="170">
          <template #default="{ row }">
            <span>{{ formatBeijingDateTime(row.created_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="movement_name" label="动作" min-width="220" />
        <el-table-column prop="score" label="评分" width="100">
          <template #default="{ row }">
            <el-tag :type="scoreTagType(row.score)">{{ row.score }}</el-tag>
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="historyVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import PoseAnalyzer from '../../components/PoseAnalyzer.vue'
import { http } from '../../api/http'
import { formatBeijingDateTime } from '../../utils/datetime'

const route = useRoute()
const router = useRouter()
const movementOptions = ref(['徒手深蹲', '俯卧撑', '箭步蹲', '臀桥', '开合跳', '登山跑', '卷腹', '平板支撑', '引体向上', '俯身划船'])
const selectedMovement = ref('徒手深蹲')
const historyVisible = ref(false)
const historyLoading = ref(false)
const history = ref<any[]>([])

function ensureMovementOption(movement: string) {
  if (!movement) {
    return
  }
  if (!movementOptions.value.includes(movement)) {
    movementOptions.value.unshift(movement)
  }
}

function syncMovementFromRoute() {
  const queryMovement = String(route.query.movement || '')
  if (!queryMovement) {
    return
  }
  ensureMovementOption(queryMovement)
  selectedMovement.value = queryMovement
}

onMounted(syncMovementFromRoute)

watch(
  () => route.query.movement,
  () => {
    syncMovementFromRoute()
  }
)

watch(selectedMovement, (movement) => {
  if (movement === String(route.query.movement || '')) {
    return
  }
  router.replace({ path: '/pose', query: { ...route.query, movement } })
})

function scoreTagType(score: any) {
  const value = Number(score ?? 0)
  if (value >= 80) return 'success'
  if (value >= 60) return 'warning'
  return 'danger'
}


function formatList(value: any) {
  if (!value) return '—'
  if (Array.isArray(value)) {
    return value.length ? value.join('；') : '—'
  }
  return String(value)
}

function formatMetrics(value: any) {
  if (!value) return '—'
  const m = value || {}
  const picks: Array<[string, string]> = []
  const add = (key: string, label: string) => {
    const v = m[key]
    if (v === undefined || v === null) return
    picks.push([label, String(v)])
  }
  add('average_score', '平均得分')
  add('frames_analyzed', '抽帧数')
  add('knee_angle', '膝角')
  add('elbow_angle', '肘角(后端)')
  add('average_elbow', '肘角(前端均值)')
  add('average_shoulder', '肩角(前端均值)')
  add('average_torso', '躯干(前端均值)')
  add('symmetry', '对称(%)')
  if (!picks.length) return '—'
  return picks.map(([k, v]) => `${k}=${v}`).join('，')
}

async function loadHistory() {
  historyLoading.value = true
  try {
    const { data } = await http.get('/pose/history', { params: { limit: 20 } })
    history.value = Array.isArray(data) ? data : []
    if (history.value.length === 0 && historyVisible.value) {
      ElMessage.info('暂无姿态分析历史记录')
    }
  } catch (e: any) {
    history.value = []
    const status = e?.response?.status
    if (status === 404 || status === 401) {
      console.log('History endpoint returned', status)
    } else {
      ElMessage.warning(`加载姿态分析历史失败：${e?.message || '未知错误'}`)
    }
  } finally {
    historyLoading.value = false
  }
}

function openHistory() {
  historyVisible.value = true
  if (!history.value.length) {
    loadHistory()
  }
}

onMounted(() => {
  syncMovementFromRoute()
  loadHistory()
})
</script>

<style scoped>
.pose-view {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 68px);
  overflow: hidden;
  background: #000;
}

.picker-bar {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 12px 28px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.22);
  background: linear-gradient(90deg, #07111f, #111827);
  color: #fff;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.28);
}

.picker-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.history-toolbar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 12px;
}

.picker-title {
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 0;
}

.picker-label {
  font-size: 18px;
  font-weight: 800;
}

.picker-hint {
  color: #cbd5e1;
  font-size: 14px;
}

.picker-bar :deep(.el-select) {
  width: 220px;
}

.analyzer-wrap {
  flex: 1;
  min-height: 0;
}
</style>
