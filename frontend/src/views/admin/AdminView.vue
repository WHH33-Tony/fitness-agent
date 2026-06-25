<template>
  <section class="page admin-page">
    <h2>管理员控制台</h2>
    <el-tabs v-model="activeTab" class="admin-tabs">
      <el-tab-pane label="用户管理" name="users">
        <el-card>
          <el-table :data="users" stripe>
            <el-table-column prop="id" label="ID" width="80" />
            <el-table-column prop="phone" label="账号" />
            <el-table-column prop="role" label="角色" />
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="row.is_active ? 'success' : 'danger'">
                  {{ row.is_active ? '启用' : '禁用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="380">
              <template #default="{ row }">
                <el-select v-model="row.role" size="small" style="width: 120px">
                  <el-option label="管理员" value="admin" />
                  <el-option label="用户" value="user" />
                </el-select>
                <el-switch
                  v-model="row.is_active"
                  size="small"
                  active-text="启用"
                  inactive-text="禁用"
                  style="margin: 0 8px"
                />
                <el-button size="small" @click="openProfile(row)">详情</el-button>
                <el-button size="small" type="primary" @click="save(row)">保存</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="系统设置" name="settings">
        <el-card>
          <h3 style="margin: 0 0 12px">大模型 API Key</h3>
          <p style="margin: 0 0 10px; color: #64748b">全站共用：健身问题走知识库，非健身问题走此外部大模型。保存后会写入本地并持久化，所有用户账号均可使用。</p>
          <div style="display: flex; gap: 10px; flex-wrap: wrap; align-items: center">
            <el-input v-model="dashscopeKey" placeholder="请输入 DASHSCOPE_API_KEY" show-password style="width: min(520px, 100%)" />
            <el-button type="primary" :loading="keySaving" @click="saveApiKey">保存并生效</el-button>
          </div>
        </el-card>
        <el-card style="margin-top: 16px">
          <h3 style="margin: 0 0 12px">讯飞语音合成</h3>
          <div style="display: grid; gap: 10px; max-width: 520px">
            <el-input v-model="xfyunAppId" placeholder="APPID" />
            <el-input
              v-model="xfyunApiKey"
              :placeholder="xfyunApiKeySet ? '已保存（留空则不修改）' : 'APIKey'"
              show-password
            />
            <el-input
              v-model="xfyunApiSecret"
              :placeholder="xfyunApiSecretSet ? '已保存（留空则不修改）' : 'APISecret'"
              show-password
            />
          </div>
          <div style="margin-top: 12px">
            <el-button type="primary" :loading="xfyunSaving" @click="saveXfyunConfig">保存讯飞配置</el-button>
            <el-tag style="margin-left: 10px" :type="xfyunConfigured ? 'success' : 'warning'">
              {{ xfyunConfigured ? '已配置' : '未配置' }}
            </el-tag>
          </div>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="用户反馈" name="feedback">
        <el-card>
          <el-radio-group v-model="feedbackStatus" @change="loadFeedbacks" style="margin-bottom: 16px">
            <el-radio-button label="">全部</el-radio-button>
            <el-radio-button label="pending">待处理</el-radio-button>
            <el-radio-button label="replied">已回复</el-radio-button>
            <el-radio-button label="closed">已关闭</el-radio-button>
          </el-radio-group>

          <el-table :data="feedbacks" @row-click="openFeedbackDetail" stripe>
            <el-table-column prop="id" label="ID" width="80" />
            <el-table-column prop="user_phone" label="用户" />
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="feedbackStatusType(row.status)">{{ feedbackStatusText(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="创建时间" />
            <el-table-column prop="updated_at" label="最后更新" />
            <el-table-column label="操作" width="120">
              <template #default="{ row }">
                <el-button
                  v-if="row.status !== 'closed'"
                  size="small"
                  type="danger"
                  @click.stop="closeFeedback(row.id)"
                >
                  关闭
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="MCP工具" name="mcp">
        <el-card>
          <div class="mcp-actions">
            <el-button type="primary" @click="loadMcpTools">刷新工具</el-button>
            <el-select
              v-model="selectedTool"
              clearable
              placeholder="筛选工具日志"
              style="width: 220px"
              @change="loadMcpLogs"
            >
              <el-option v-for="item in mcpTools" :key="item.tool_name" :label="item.tool_name" :value="item.tool_name" />
            </el-select>
            <el-button @click="loadMcpLogs">刷新日志</el-button>
          </div>

          <el-table :data="mcpTools" stripe>
            <el-table-column prop="tool_name" label="工具名" width="160" />
            <el-table-column prop="description" label="描述" />
            <el-table-column prop="is_enabled" label="启用" width="90">
              <template #default="{ row }">
                <el-tag :type="row.is_enabled ? 'success' : 'info'">{{ row.is_enabled ? '启用' : '停用' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="call_count" label="调用次数" width="110" />
            <el-table-column prop="avg_latency_ms" label="平均耗时(ms)" width="140" />
            <el-table-column label="操作" width="220">
              <template #default="{ row }">
                <el-button size="small" @click="toggleTool(row)">{{ row.is_enabled ? '停用' : '启用' }}</el-button>
                <el-button size="small" type="primary" @click.stop="viewLogs(row.tool_name)">查看日志</el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-divider />

          <div ref="mcpLogSectionRef" class="mcp-log-section">
            <h3 class="mcp-log-title">
              工具调用日志
              <el-tag v-if="selectedTool" type="primary" size="small" style="margin-left: 8px">
                已筛选：{{ selectedTool }}
              </el-tag>
              <span v-if="mcpLogs.length" class="mcp-log-count muted">共 {{ mcpLogs.length }} 条</span>
              <span class="mcp-log-hint muted">点击行首箭头展开详情</span>
            </h3>
            <div class="mcp-log-scroll">
              <el-table
                v-loading="mcpLogsLoading"
                :data="mcpLogs"
                stripe
                empty-text="暂无调用日志"
                class="mcp-log-table"
              >
            <el-table-column type="expand" width="48">
              <template #default="{ row }">
                <div class="mcp-log-expand">
                  <ul v-if="formatLogExpandItems(row).length" class="mcp-log-lines">
                    <li v-for="item in formatLogExpandItems(row)" :key="item.label">
                      <span class="mcp-log-label">{{ item.label }}</span>
                      <span class="mcp-log-value">{{ item.value }}</span>
                    </li>
                  </ul>
                  <el-collapse class="mcp-log-raw-collapse">
                    <el-collapse-item title="原始参数与结果（JSON）" name="raw">
                      <div class="mcp-log-raw-block"><strong>参数</strong>：{{ formatMcpLogJson(row.params) }}</div>
                      <div class="mcp-log-raw-block"><strong>结果</strong>：{{ formatMcpLogJson(row.result) }}</div>
                    </el-collapse-item>
                  </el-collapse>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="call_id" label="ID" width="80" />
            <el-table-column prop="tool_name" label="工具名" width="140" />
            <el-table-column label="摘要" min-width="280" show-overflow-tooltip>
              <template #default="{ row }">
                <span class="mcp-log-brief">{{ formatMcpLogBrief(row) }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="mcpLogStatusType(row.status)" size="small">{{ mcpLogStatusText(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="latency_ms" label="耗时(ms)" width="120" />
            <el-table-column prop="created_at" label="时间" min-width="170">
              <template #default="{ row }">
                <span>{{ formatBeijingDateTime(row.created_at) }}</span>
              </template>
            </el-table-column>
              </el-table>
            </div>
          </div>
        </el-card>
      </el-tab-pane>
    </el-tabs>
    <el-dialog v-model="profileVisible" title="用户资料" width="520px">
      <el-form v-if="profileForm" label-position="top">
        <el-form-item label="昵称"><el-input v-model="profileForm.nickname" /></el-form-item>
        <el-form-item label="身高(cm)"><el-input-number v-model="profileForm.height" :min="80" /></el-form-item>
        <el-form-item label="体重(kg)"><el-input-number v-model="profileForm.weight" :min="20" /></el-form-item>
        <el-form-item label="年龄"><el-input-number v-model="profileForm.age" :min="1" /></el-form-item>
        <el-form-item label="性别">
          <el-select v-model="profileForm.gender">
            <el-option label="未知" value="unknown" />
            <el-option label="男" value="male" />
            <el-option label="女" value="female" />
          </el-select>
        </el-form-item>
        <el-form-item label="语音播报音色（讯飞）">
          <el-select v-model="profileForm.voice_type">
            <el-option-group label="基础发音人">
              <el-option
                v-for="v in voices.filter((item) => item.tier !== 'special')"
                :key="v.id"
                :label="`${v.name}（${v.desc}）`"
                :value="v.id"
              />
            </el-option-group>
            <el-option-group label="特色发音人">
              <el-option
                v-for="v in voices.filter((item) => item.tier === 'special')"
                :key="v.id"
                :label="`${v.name}（${v.desc}）`"
                :value="v.id"
              />
            </el-option-group>
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="profileVisible = false">取消</el-button>
        <el-button type="primary" :loading="profileSaving" @click="saveProfile">保存资料</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="feedbackVisible" title="反馈详情" width="820px">
      <div class="messages">
        <div
          v-for="msg in feedbackMessages"
          :key="msg.id"
          :class="['message', msg.sender_type === 'admin' ? 'admin' : 'user']"
        >
          <div class="message-header">
            <span class="sender">{{ msg.sender_type === 'admin' ? '管理员' : '用户' }}</span>
            <span class="time">{{ msg.created_at }}</span>
          </div>
          <div class="message-content">{{ msg.content }}</div>
        </div>
      </div>

      <div v-if="feedbackDetail?.feedback?.status !== 'closed'" class="reply-box">
        <el-input
          v-model="feedbackReplyContent"
          type="textarea"
          :rows="3"
          placeholder="回复用户..."
          maxlength="2000"
          show-word-limit
        />
        <el-button type="primary" @click="sendFeedbackReply" style="margin-top: 10px">发送回复</el-button>
      </div>
    </el-dialog>
  </section>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { nextTick, onMounted, ref, watch } from 'vue'

import { DEFAULT_VOICES } from '../../constants/voices'
import { http } from '../../api/http'
import { playAudioBase64 } from '../../utils/tts'
import { formatBeijingDateTime } from '../../utils/datetime'
import { getStoredXfyunConfig, storeXfyunConfig } from '../../utils/xfyunConfig'

const voices = ref(DEFAULT_VOICES)
const users = ref<any[]>([])
const activeTab = ref<'users' | 'feedback' | 'mcp' | 'settings'>('users')
const mcpTools = ref<any[]>([])
const mcpLogs = ref<any[]>([])
const selectedTool = ref<string>('')
const mcpLogSectionRef = ref<HTMLElement | null>(null)
const mcpLogsLoading = ref(false)
const profileVisible = ref(false)
const profileSaving = ref(false)
const profileUserId = ref<number | null>(null)
const profileForm = ref<any>(null)

const feedbacks = ref<any[]>([])
const feedbackStatus = ref<string>('')
const feedbackVisible = ref(false)
const feedbackDetail = ref<any>(null)
const feedbackMessages = ref<any[]>([])
const feedbackReplyContent = ref('')

const dashscopeKey = ref(localStorage.getItem('dashscope_api_key') || '')
const keySaving = ref(false)
const xfyunAppId = ref('')
const xfyunApiKey = ref('')
const xfyunApiSecret = ref('')
const xfyunSaving = ref(false)
const xfyunConfigured = ref(false)
const xfyunApiKeySet = ref(false)
const xfyunApiSecretSet = ref(false)

async function saveApiKey() {
  keySaving.value = true
  try {
    const key = String(dashscopeKey.value || '').trim()
    localStorage.setItem('dashscope_api_key', key)
    await http.post('/config/apikey', { dashscope_api_key: key })
    ElMessage.success(key ? '已保存并生效' : '已清空（将使用本地知识库回答）')
  } finally {
    keySaving.value = false
  }
}

async function loadVoices() {
  try {
    const { data } = await http.get('/config/xfyun/voices')
    if (Array.isArray(data) && data.length) voices.value = data
  } catch (_) {
    voices.value = DEFAULT_VOICES
  }
}

async function loadXfyunStatus() {
  const stored = getStoredXfyunConfig()
  try {
    const { data } = await http.get('/config/xfyun/status')
    xfyunConfigured.value = Boolean(data?.xfyun_configured)
    xfyunAppId.value = String(data?.app_id || stored.app_id || '')
    xfyunApiKeySet.value = Boolean(data?.api_key_set || stored.api_key)
    xfyunApiSecretSet.value = Boolean(data?.api_secret_set || stored.api_secret)
  } catch (_) {
    xfyunConfigured.value = Boolean(stored.app_id && stored.api_key && stored.api_secret)
    xfyunAppId.value = stored.app_id
    xfyunApiKeySet.value = Boolean(stored.api_key)
    xfyunApiSecretSet.value = Boolean(stored.api_secret)
  }
}

async function saveXfyunConfig() {
  const appId = String(xfyunAppId.value || '').trim()
  const apiKey = String(xfyunApiKey.value || '').trim()
  const apiSecret = String(xfyunApiSecret.value || '').trim()
  if (!appId) {
    ElMessage.warning('请填写 APPID')
    return
  }
  if (!xfyunConfigured.value && (!apiKey || !apiSecret)) {
    ElMessage.warning('首次配置请填写完整的 APPID、APIKey、APISecret')
    return
  }

  xfyunSaving.value = true
  try {
    const stored = getStoredXfyunConfig()
    const payload = {
      app_id: appId,
      api_key: apiKey || stored.api_key,
      api_secret: apiSecret || stored.api_secret
    }
    await http.post('/config/xfyun', payload)
    storeXfyunConfig(payload.app_id, payload.api_key, payload.api_secret)
    await loadXfyunStatus()
    xfyunApiKey.value = ''
    xfyunApiSecret.value = ''

    try {
      const { data: testData } = await http.post('/config/xfyun/test')
      const played = await playAudioBase64(String(testData?.audio_base64 || ''))
      if (played) {
        ElMessage.success('讯飞配置已保存（基础发音人测试通过）。特色发音人需在讯飞控制台单独开通')
      } else {
        ElMessage.warning('讯飞合成成功，但本地播放失败，请在我的信息中点击试听音色')
      }
    } catch (testErr: any) {
      ElMessage.warning(
        `配置已保存，但语音合成测试失败：${testErr?.response?.data?.detail || testErr?.message || '请检查密钥是否正确'}`
      )
    }
  } catch (e: any) {
    ElMessage.error(`保存失败：${e?.response?.data?.detail || e?.message || '未知错误'}`)
  } finally {
    xfyunSaving.value = false
  }
}

async function loadUsers() {
  users.value = (await http.get('/users')).data
}

async function save(row: any) {
  await http.patch(`/users/${row.id}`, null, { params: { role: row.role, is_active: row.is_active } })
  ElMessage.success('用户已更新')
  await loadUsers()
}

async function openProfile(row: any) {
  profileUserId.value = Number(row.id)
  profileVisible.value = true
  profileForm.value = (await http.get(`/users/${row.id}/profile`)).data
}

async function saveProfile() {
  if (!profileUserId.value) {
    return
  }
  profileSaving.value = true
  try {
    await http.put(`/users/${profileUserId.value}/profile`, profileForm.value)
    ElMessage.success('资料已保存')
    profileVisible.value = false
  } finally {
    profileSaving.value = false
  }
}

async function loadMcpTools() {
  mcpTools.value = (await http.get('/mcp/tools')).data
}

async function loadFeedbacks() {
  feedbacks.value = (await http.get('/feedback', { params: { status: feedbackStatus.value || undefined } })).data
}

async function openFeedbackDetail(row: any) {
  const { data } = await http.get(`/feedback/${row.id}`)
  feedbackDetail.value = data
  feedbackMessages.value = data.messages || []
  feedbackReplyContent.value = ''
  feedbackVisible.value = true
}

async function sendFeedbackReply() {
  if (!feedbackDetail.value?.feedback?.id) return
  if (!feedbackReplyContent.value.trim()) {
    ElMessage.warning('请输入回复内容')
    return
  }
  await http.post(`/feedback/${feedbackDetail.value.feedback.id}/reply`, { content: feedbackReplyContent.value })
  ElMessage.success('已回复')
  await openFeedbackDetail({ id: feedbackDetail.value.feedback.id })
  await loadFeedbacks()
}

async function closeFeedback(id: number) {
  await http.patch(`/feedback/${id}/close`)
  ElMessage.success('已关闭')
  await loadFeedbacks()
}

function feedbackStatusType(status: string) {
  return ({ pending: 'warning', replied: 'success', closed: 'info' } as Record<string, any>)[status] || 'info'
}

function feedbackStatusText(status: string) {
  return ({ pending: '待处理', replied: '已回复', closed: '已关闭' } as Record<string, string>)[status] || status
}

async function toggleTool(row: any) {
  try {
    if (row.is_enabled) {
      await http.post(`/mcp/tools/${row.tool_name}/disable`)
      ElMessage.success(`已停用工具「${row.tool_name}」`)
    } else {
      await http.post(`/mcp/tools/${row.tool_name}/enable`)
      ElMessage.success(`已启用工具「${row.tool_name}」`)
    }
    await loadMcpTools()
    await loadMcpLogs()
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '操作失败，请稍后重试')
  }
}

function formatMcpLogJson(value: unknown) {
  if (value == null) return '—'
  try {
    return JSON.stringify(value)
  } catch (_) {
    return String(value)
  }
}

function formatKnowledgeMode(mode: string, sourcesCount?: number) {
  if (mode === 'llm') return '大模型（未注入知识库）'
  if (mode === 'local_kb') return `本地知识库（${Number(sourcesCount ?? 0)} 条）`
  if (mode === '未调用') return '未调用（泛化问答不走健身知识库分支）'
  if (mode === 'Agent已停用') return 'Agent 已停用'
  return mode
}

function truncateText(text: string, max = 40) {
  const raw = String(text || '').trim()
  if (!raw) return ''
  return raw.length > max ? `${raw.slice(0, max)}…` : raw
}

function formatMcpLogBrief(row: any) {
  const result = row?.result || {}
  const params = row?.params || {}
  if (row.status === 'fail') {
    const question = truncateText(result.question || params.question || row.summary, 36)
    const err = truncateText(result.error || row.summary || '调用失败', 28)
    return question ? `${question} · ${err}` : err
  }
  if (row.tool_name === 'qa_agent') {
    const question = truncateText(result.question || params.question, 42)
    const parts = [question || '—']
    if (result.intent) parts.push(String(result.intent))
    if (result.knowledge_switch) parts.push(`knowledge${result.knowledge_switch}`)
    if (result.knowledge_mode === 'llm') parts.push('大模型')
    else if (result.knowledge_mode === 'local_kb') parts.push('本地库')
    else if (result.knowledge_mode) parts.push(String(result.knowledge_mode))
    return parts.join(' · ')
  }
  if (row.tool_name === 'knowledge') {
    const question = truncateText(params.question, 36)
    const mode = formatKnowledgeMode(result.mode, result.snippets?.length)
    return question ? `${question} · ${mode}` : mode
  }
  return truncateText(row.summary || '—', 80)
}

function formatLogExpandItems(row: any) {
  const result = row?.result || {}
  const params = row?.params || {}
  const items: Array<{ label: string; value: string }> = []
  const push = (label: string, value: unknown) => {
    const text = value == null || value === '' ? '' : String(value)
    if (text) items.push({ label, value: text })
  }

  if (row.tool_name === 'qa_agent') {
    push('问题', result.question || params.question)
    push('意图', result.intent)
    push('路由', result.route_note)
    push('knowledge 开关', result.knowledge_switch)
    push('本次 knowledge', formatKnowledgeMode(result.knowledge_mode, result.sources_count))
    push('回答来源', result.answer_mode)
    push('子工具', Array.isArray(result.tools_invoked) ? result.tools_invoked.join('、') : '')
    push('引用条数', result.sources_count)
    push('回答摘要', result.answer_preview)
    push('错误', result.error)
    return items
  }

  if (row.tool_name === 'knowledge') {
    push('问题', params.question)
    push('模式', formatKnowledgeMode(result.mode, result.snippets?.length))
    push('命中片段数', Array.isArray(result.snippets) ? result.snippets.length : '')
    return items
  }

  push('摘要', row.summary)
  return items
}

async function loadMcpLogs() {
  mcpLogsLoading.value = true
  try {
    const { data } = await http.get('/mcp/logs', {
      params: { tool_name: selectedTool.value || undefined, limit: 50 },
    })
    mcpLogs.value = Array.isArray(data) ? data : []
  } catch (err: any) {
    mcpLogs.value = []
    ElMessage.error(err?.response?.data?.detail || '加载日志失败')
  } finally {
    mcpLogsLoading.value = false
  }
}

async function scrollToMcpLogs() {
  await nextTick()
  mcpLogSectionRef.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

async function viewLogs(toolName: string) {
  selectedTool.value = toolName
  await loadMcpLogs()
  await scrollToMcpLogs()
  const count = mcpLogs.value.length
  ElMessage.info(count ? `已筛选「${toolName}」的 ${count} 条日志` : `「${toolName}」暂无调用日志`)
}

function mcpLogStatusType(status: string) {
  return ({ success: 'success', fail: 'danger', timeout: 'warning' } as Record<string, string>)[status] || 'info'
}

function mcpLogStatusText(status: string) {
  return ({ success: '成功', fail: '失败', timeout: '超时' } as Record<string, string>)[status] || status
}

watch(activeTab, (tab) => {
  if (tab === 'settings') {
    void loadXfyunStatus()
  }
  if (tab === 'mcp') {
    void loadMcpTools()
    void loadMcpLogs()
  }
})

onMounted(async () => {
  const key = String(dashscopeKey.value || '').trim()
  if (key) {
    try {
      await http.post('/config/apikey', { dashscope_api_key: key })
    } catch {
      // 后端未就绪时忽略
    }
  }
  await Promise.all([loadUsers(), loadFeedbacks(), loadMcpTools(), loadVoices(), loadXfyunStatus()])
  await loadMcpLogs()
})
</script>

<style scoped>
.admin-page {
  overflow-x: hidden;
  overflow-y: auto;
}

.admin-tabs :deep(.el-tabs__header) {
  margin-bottom: 16px;
}

.mcp-log-section {
  margin-top: 4px;
}

.mcp-log-title {
  margin: 0 0 12px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.mcp-log-count,
.mcp-log-hint {
  font-size: 12px;
  font-weight: 400;
}

.mcp-log-brief {
  font-size: 12px;
  color: #334155;
  line-height: 1.45;
}

.mcp-log-scroll {
  max-height: min(58vh, 640px);
  overflow-y: auto;
  overflow-x: hidden;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  background: #fff;
}

.mcp-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  margin-bottom: 16px;
}

.mcp-log-expand {
  padding: 8px 12px 12px;
  font-size: 12px;
  line-height: 1.6;
  color: #475569;
  word-break: break-all;
}

.mcp-log-expand div + div {
  margin-top: 8px;
}

.mcp-log-table :deep(.el-table__row td) {
  vertical-align: middle;
  padding-top: 8px;
  padding-bottom: 8px;
}

.mcp-log-table :deep(.el-table .cell) {
  line-height: 1.45;
}

.mcp-log-raw-collapse {
  margin-top: 10px;
  border-top: 1px dashed #e2e8f0;
}

.mcp-log-raw-collapse :deep(.el-collapse-item__header) {
  height: 36px;
  font-size: 12px;
  color: #64748b;
}

.mcp-log-raw-block {
  margin-bottom: 8px;
  font-size: 12px;
  line-height: 1.55;
  word-break: break-all;
}

.mcp-log-lines {
  margin: 0;
  padding: 0;
  list-style: none;
}

.mcp-log-lines li {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  margin-bottom: 4px;
  font-size: 12px;
  line-height: 1.55;
}

.mcp-log-lines li:last-child {
  margin-bottom: 0;
}

.mcp-log-label {
  flex: 0 0 92px;
  color: #64748b;
}

.mcp-log-value {
  flex: 1;
  min-width: 0;
  color: #1f2937;
  word-break: break-word;
  white-space: pre-wrap;
}

.mcp-log-answer {
  color: #334155;
}

.mcp-log-plain {
  font-size: 12px;
  color: #475569;
  white-space: pre-wrap;
  word-break: break-word;
}

.messages {
  max-height: 420px;
  overflow-y: auto;
  margin-bottom: 16px;
}

.message {
  margin-bottom: 12px;
  padding: 12px;
  border-radius: 8px;
}

.message.user {
  background: #f0f0f0;
}

.message.admin {
  background: #e6f7ff;
}

.message-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 12px;
  color: #666;
}

.message-content {
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
