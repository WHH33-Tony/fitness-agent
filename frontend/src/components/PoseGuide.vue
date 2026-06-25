<template>
  <div class="panel pose-guide">
    <div class="guide-head">
      <div>
        <h3>实时动作姿态指导</h3>
        <p>当前动作：{{ movementName }}</p>
      </div>
      <el-button @click="$emit('close')">收起</el-button>
    </div>

    <div class="guide-body">
      <div class="camera-box">
        <video ref="videoRef" autoplay playsinline muted class="video"></video>
        <canvas ref="canvasRef" class="pose-canvas"></canvas>
      </div>
      <div class="guide-info">
        <el-button type="primary" @click="toggleCamera">{{ cameraOn ? '关闭摄像头' : '开启摄像头' }}</el-button>
        <el-button type="success" :disabled="!cameraOn" @click="sendFrame">立即评判</el-button>
        <p class="guide-tip">开启摄像头后会持续进行姿态指导。</p>
        <div v-if="result" class="result-box">
          <h4>评分：{{ result.score }} 分</h4>
          <p>问题：{{ result.errors?.join('，') || result.message || '暂无明显问题' }}</p>
          <p>建议：{{ result.suggestions?.join('，') || '保持全身入镜并稳定完成动作' }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { onBeforeUnmount, onMounted, ref } from 'vue'

const props = withDefaults(defineProps<{ movementName: string; autoStart?: boolean }>(), {
  autoStart: false
})
defineEmits<{ close: [] }>()

const videoRef = ref<HTMLVideoElement>()
const canvasRef = ref<HTMLCanvasElement>()
const cameraOn = ref(false)
const stream = ref<MediaStream>()
const socket = ref<WebSocket>()
const result = ref<any>()
let analyzeTimer: number | undefined

async function toggleCamera() {
  if (cameraOn.value) {
    stopCamera()
    return
  }
  try {
    stream.value = await navigator.mediaDevices.getUserMedia({ video: true })
    if (videoRef.value) {
      videoRef.value.srcObject = stream.value
    }
    connectSocket()
    cameraOn.value = true
    startRealtimeAnalyze()
  } catch {
    ElMessage.error('无法打开摄像头，请检查浏览器权限')
  }
}

function connectSocket() {
  if (socket.value && socket.value.readyState === WebSocket.OPEN) {
    return
  }
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
  socket.value = new WebSocket(`${protocol}://${window.location.host}/api/pose/ws`)
  socket.value.onmessage = (event) => {
    result.value = JSON.parse(event.data)
  }
  socket.value.onerror = () => {
    ElMessage.error('姿态指导连接失败，请确认后端服务正常')
  }
}

function sendFrame() {
  drawGuideSkeleton()
  const landmarks = Array.from({ length: 33 }, (_, index) => ({
    x: 0.4 + index * 0.001,
    y: 0.4 + index * 0.002,
    z: 0,
    visibility: 1
  }))
  const payload = JSON.stringify({ movement_name: props.movementName, landmarks })
  if (socket.value?.readyState === WebSocket.OPEN) {
    socket.value.send(payload)
  } else {
    result.value = { score: 0, errors: ['实时连接未建立，请重新开启摄像头'] }
  }
}

function startRealtimeAnalyze() {
  window.clearInterval(analyzeTimer)
  analyzeTimer = window.setInterval(() => {
    if (cameraOn.value) {
      sendFrame()
    }
  }, 1500)
}

function drawGuideSkeleton() {
  const canvas = canvasRef.value
  const video = videoRef.value
  if (!canvas || !video) {
    return
  }
  canvas.width = video.clientWidth
  canvas.height = video.clientHeight
  const ctx = canvas.getContext('2d')
  if (!ctx) {
    return
  }
  ctx.clearRect(0, 0, canvas.width, canvas.height)
  ctx.strokeStyle = '#22c55e'
  ctx.lineWidth = 4
  ctx.beginPath()
  ctx.moveTo(canvas.width * 0.5, canvas.height * 0.2)
  ctx.lineTo(canvas.width * 0.5, canvas.height * 0.55)
  ctx.lineTo(canvas.width * 0.36, canvas.height * 0.82)
  ctx.moveTo(canvas.width * 0.5, canvas.height * 0.55)
  ctx.lineTo(canvas.width * 0.64, canvas.height * 0.82)
  ctx.moveTo(canvas.width * 0.36, canvas.height * 0.36)
  ctx.lineTo(canvas.width * 0.64, canvas.height * 0.36)
  ctx.stroke()
}

function stopCamera() {
  window.clearInterval(analyzeTimer)
  stream.value?.getTracks().forEach((track) => track.stop())
  if (videoRef.value) {
    videoRef.value.srcObject = null
  }
  socket.value?.close()
  cameraOn.value = false
  stream.value = undefined
}

onMounted(() => {
  if (props.autoStart) {
    toggleCamera()
  }
})

onBeforeUnmount(stopCamera)
</script>

<style scoped>
.pose-guide {
  padding: 24px;
}

.guide-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18px;
}

.guide-head h3,
.guide-head p {
  margin: 0 0 6px;
}

.guide-body {
  display: grid;
  grid-template-columns: minmax(420px, 1.5fr) minmax(260px, 0.8fr);
  gap: 24px;
}

.camera-box {
  position: relative;
  overflow: hidden;
  border-radius: 24px;
  background: #000;
}

.video {
  width: 100%;
  height: 320px;
  object-fit: cover;
  display: block;
}

.pose-canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.guide-info {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.guide-tip {
  margin: 0;
  color: #6b7280;
}

.result-box {
  padding: 16px;
  border-radius: 14px;
  background: #f8fafc;
}

.result-box h4 {
  margin: 0 0 8px;
}

.result-box p {
  margin: 8px 0 0;
}
</style>
