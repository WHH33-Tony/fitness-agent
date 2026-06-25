<template>
  <div class="feedback-view">
    <el-card>
      <template #header>
        <div class="header">
          <span>我的反馈</span>
          <el-button type="primary" @click="showCreateDialog = true">新建反馈</el-button>
        </div>
      </template>

      <el-table :data="feedbacks" @row-click="openDetail">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)">{{ statusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" />
        <el-table-column prop="updated_at" label="最后更新" />
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button v-if="row.status !== 'closed'" size="small" type="danger" @click.stop="closeFeedback(row)">
              关闭
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="showCreateDialog" title="新建反馈" width="600px">
      <el-input
        v-model="newContent"
        type="textarea"
        :rows="6"
        placeholder="请描述您的问题或建议..."
        maxlength="2000"
        show-word-limit
      />
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="createFeedback">提交</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showDetailDialog" title="反馈详情" width="800px">
      <div class="messages">
        <div v-for="msg in messages" :key="msg.id" :class="['message', msg.sender_type === 'admin' ? 'admin' : 'user']">
          <div class="message-header">
            <span class="sender">{{ msg.sender_type === 'admin' ? '管理员' : '我' }}</span>
            <span class="time">{{ msg.created_at }}</span>
          </div>
          <div class="message-content">{{ msg.content }}</div>
        </div>
      </div>

      <div v-if="currentFeedback?.status !== 'closed'" class="reply-box">
        <el-input v-model="replyContent" type="textarea" :rows="3" placeholder="继续反馈..." maxlength="2000" />
        <el-button type="primary" @click="sendReply" style="margin-top: 10px">发送</el-button>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'

import { http } from '../../api/http'

type FeedbackItem = {
  id: number
  user_id: number
  status: string
  created_at?: string
  updated_at?: string
}

type FeedbackMessageItem = {
  id: number
  feedback_id: number
  sender_type: 'user' | 'admin'
  sender_id: number
  content: string
  created_at?: string
}

const feedbacks = ref<FeedbackItem[]>([])
const messages = ref<FeedbackMessageItem[]>([])
const currentFeedback = ref<FeedbackItem | null>(null)
const showCreateDialog = ref(false)
const showDetailDialog = ref(false)
const newContent = ref('')
const replyContent = ref('')

async function loadFeedbacks() {
  feedbacks.value = (await http.get('/feedback/my')).data
}

async function createFeedback() {
  if (!newContent.value.trim()) {
    ElMessage.warning('请输入反馈内容')
    return
  }

  await http.post('/feedback', { content: newContent.value })
  ElMessage.success('反馈已提交')
  showCreateDialog.value = false
  newContent.value = ''
  await loadFeedbacks()
}

async function openDetail(row: FeedbackItem) {
  const { data } = await http.get(`/feedback/${row.id}`)
  currentFeedback.value = data.feedback
  messages.value = data.messages
  showDetailDialog.value = true
  replyContent.value = ''
}

async function sendReply() {
  if (!currentFeedback.value) return
  if (!replyContent.value.trim()) {
    ElMessage.warning('请输入回复内容')
    return
  }

  await http.post(`/feedback/${currentFeedback.value.id}/reply`, { content: replyContent.value })
  ElMessage.success('已发送')
  replyContent.value = ''
  await openDetail(currentFeedback.value)
  await loadFeedbacks()
}

async function closeFeedback(row: FeedbackItem) {
  if (!row?.id) return
  await http.patch(`/feedback/${row.id}/close`)
  ElMessage.success('已关闭')
  if (currentFeedback.value?.id === row.id) {
    await openDetail(row)
  }
  await loadFeedbacks()
}

function statusType(status: string) {
  return ({ pending: 'warning', replied: 'success', closed: 'info' } as Record<string, any>)[status] || 'info'
}

function statusText(status: string) {
  return ({ pending: '待处理', replied: '已回复', closed: '已关闭' } as Record<string, string>)[status] || status
}

onMounted(loadFeedbacks)
</script>

<style scoped>
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.messages {
  max-height: 400px;
  overflow-y: auto;
  margin-bottom: 20px;
}

.message {
  margin-bottom: 16px;
  padding: 12px;
  border-radius: 8px;
}

.message.user {
  background: #f0f0f0;
  margin-left: 20%;
}

.message.admin {
  background: #e6f7ff;
  margin-right: 20%;
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

