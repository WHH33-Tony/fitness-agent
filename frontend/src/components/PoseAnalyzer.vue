<template>
  <section class="pose-analyzer" :class="{ embedded }">
    <div v-if="!embedded" class="pose-stage">
      <video
        ref="videoRef"
        class="pose-video"
        :class="{ 'mirror-view': shouldMirrorView }"
        autoplay
        playsinline
        muted
        @loadedmetadata="syncCanvasSize"
      ></video>
      <canvas ref="canvasRef" class="pose-canvas" :class="{ 'mirror-view': shouldMirrorView }"></canvas>

      <div v-if="!cameraOn && !videoUploaded" class="no-camera-hint">
        <h2>运动姿态分析</h2>
        <p>开启摄像头或上传视频后，系统会实时绘制骨骼关键点并计算动作数据。</p>
      </div>

      <aside class="overlay-panel info-card">
        <div class="movement-head">
          <strong>{{ movementInfo.name }}</strong>
          <span>{{ movementInfo.level }}</span>
        </div>
        <p class="movement-desc">{{ movementInfo.muscles }}</p>
        <ul>
          <li v-for="step in movementInfo.steps" :key="step">{{ step }}</li>
        </ul>
      </aside>

      <aside class="overlay-panel data-panel">
        <div class="angle-row">
          <span>肘</span>
          <strong :class="angleClass(metrics.elbow)">{{ metrics.elbow }}°</strong>
        </div>
        <div class="angle-row">
          <span>肩</span>
          <strong :class="angleClass(metrics.shoulder)">{{ metrics.shoulder }}°</strong>
        </div>
        <div class="score-box">
          <span>得分</span>
          <strong>{{ metrics.score }}</strong>
        </div>
        <div class="angle-row">
          <span>对称</span>
          <strong :class="percentClass(metrics.symmetry)">{{ metrics.symmetry }}%</strong>
        </div>
        <div class="angle-row">
          <span>躯干</span>
          <strong :class="angleClass(metrics.torso)">{{ metrics.torso }}°</strong>
        </div>
        <div class="feedback-box">
          <span>实时建议</span>
          <p>{{ feedbackText }}</p>
        </div>
      </aside>

      <div class="bottom-controls">
        <el-button type="primary" @click="toggleCamera">{{ cameraOn ? '关闭摄像头' : '开启摄像头' }}</el-button>
        <el-upload :http-request="uploadVideo" :show-file-list="false" accept="video/*">
          <el-button>上传视频</el-button>
        </el-upload>
        <el-button class="report-btn" @click="openReport">AI 深度分析报告</el-button>
      </div>
    </div>

    <div v-else class="embedded-layout">
      <div class="embed-video-col">
        <div class="embed-video-box">
          <video
            ref="videoRef"
            class="pose-video"
            :class="{ 'mirror-view': shouldMirrorView }"
            autoplay
            playsinline
            muted
            @loadedmetadata="syncCanvasSize"
          ></video>
          <canvas ref="canvasRef" class="pose-canvas" :class="{ 'mirror-view': shouldMirrorView }"></canvas>
          <div v-if="!cameraOn && !videoUploaded" class="embed-hint">
            <h3>准备开始姿态分析</h3>
            <p>请打开摄像头或上传视频，保持全身入镜。</p>
          </div>
        </div>
        <div class="embed-controls">
          <el-button type="primary" @click="toggleCamera">{{ cameraOn ? '关闭摄像头' : '开启摄像头' }}</el-button>
          <el-upload :http-request="uploadVideo" :show-file-list="false" accept="video/*">
            <el-button>上传视频</el-button>
          </el-upload>
        </div>
      </div>

      <div class="embed-info-card">
        <div class="movement-head">
          <strong>{{ movementInfo.name }}</strong>
          <span>{{ movementInfo.level }}</span>
        </div>
        <p class="movement-desc">{{ movementInfo.muscles }}</p>
        <ul>
          <li v-for="step in movementInfo.steps" :key="step">{{ step }}</li>
        </ul>
      </div>

      <div class="embed-metrics-card">
        <div class="angle-row">
          <span>肘</span>
          <strong :class="angleClass(metrics.elbow)">{{ metrics.elbow }}°</strong>
        </div>
        <div class="angle-row">
          <span>肩</span>
          <strong :class="angleClass(metrics.shoulder)">{{ metrics.shoulder }}°</strong>
        </div>
        <div class="score-box">
          <span>得分</span>
          <strong>{{ metrics.score }}</strong>
        </div>
        <div class="angle-row">
          <span>对称</span>
          <strong :class="percentClass(metrics.symmetry)">{{ metrics.symmetry }}%</strong>
        </div>
        <div class="angle-row">
          <span>躯干</span>
          <strong :class="angleClass(metrics.torso)">{{ metrics.torso }}°</strong>
        </div>
        <div class="feedback-box">
          <span>实时建议</span>
          <p>{{ feedbackText }}</p>
        </div>
        <el-button class="report-btn embed-report-btn" @click="openReport">AI 深度分析报告</el-button>
        <el-button class="complete-btn" type="success" :disabled="!canComplete" @click="markCompleted">完成并记录消耗</el-button>
      </div>
    </div>

    <el-dialog v-model="reportVisible" title="AI 深度分析报告" width="560px">
      <div class="report-content">
        <p>动作：{{ movementInfo.name }}</p>
        <p>平均得分：{{ reportSnapshot.averageScore }} 分</p>
        <p>平均肘角：{{ reportSnapshot.elbow }}°</p>
        <p>平均肩角：{{ reportSnapshot.shoulder }}°</p>
        <p>平均躯干：{{ reportSnapshot.torso }}°</p>
        <p style="white-space: pre-line">建议：{{ reportSnapshot.suggestion }}</p>
        <template v-if="reportSnapshot.highlights.length">
          <p style="margin-top: 10px"><strong>关键问题</strong></p>
          <ul>
            <li v-for="item in reportSnapshot.highlights" :key="item">{{ item }}</li>
          </ul>
        </template>
      </div>
    </el-dialog>
  </section>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'

import { http } from '../api/http'
import { speakText, stopTts } from '../utils/tts'
import { getVoiceType } from '../utils/voice'

const emit = defineEmits<{
  (e: 'analysis-completed', payload: { movement_name: string; score: number; average_score: number }): void
  (e: 'session-saved'): void
}>()

type Landmark = {
  x: number
  y: number
  z?: number
  visibility?: number
}

type PoseResult = {
  image?: CanvasImageSource
  poseLandmarks?: Landmark[]
}

type MovementInfo = {
  name: string
  level: string
  muscles: string
  steps: string[]
}

const props = withDefaults(
  defineProps<{
    movementName: string
    embedded?: boolean
    showMovementPicker?: boolean
  }>(),
  {
    embedded: false,
    showMovementPicker: false
  }
)

const videoRef = ref<HTMLVideoElement>()
const canvasRef = ref<HTMLCanvasElement>()
const cameraOn = ref(false)
const videoUploaded = ref(false)
const facingMode = ref<'user' | 'environment'>('user')
const reportVisible = ref(false)
const reportSnapshot = reactive({
  averageScore: 0,
  elbow: 0,
  shoulder: 0,
  torso: 0,
  suggestion: '',
  highlights: [] as string[]
})
const feedbackText = ref('请保持全身入镜，动作稳定后系统会给出实时建议。')
const lastSpoken = ref('')
const lastSpokenAt = ref(0)
const history = ref<Array<{ elbow: number; shoulder: number; torso: number; score: number }>>([])
const lastLandmarks = ref<Landmark[] | null>(null)
const cameraWasOpened = ref(false)
const metrics = reactive({
  elbow: 0,
  shoulder: 0,
  torso: 0,
  score: 0,
  symmetry: 0
})

let stream: MediaStream | undefined
let pose: any
let animationId = 0
let sending = false
let uploadedUrl = ''
let pageClosing = false

const movementDb: Record<string, MovementInfo> = {
  徒手深蹲: {
    name: '徒手深蹲',
    level: '标准',
    muscles: '主要锻炼臀腿与核心稳定能力。',
    steps: ['双脚与肩同宽', '髋部向后坐', '膝盖对准脚尖', '背部保持挺直', '缓慢起身回到站立']
  },
  俯卧撑: {
    name: '俯卧撑',
    level: '标准',
    muscles: '主要锻炼胸部、肩部、肱三头肌和核心。',
    steps: ['双手略宽于肩', '身体保持一条直线', '下降至胸部接近地面', '肘部不要过度外展', '推起时核心收紧']
  },
  箭步蹲: {
    name: '箭步蹲',
    level: '标准',
    muscles: '主要锻炼股四头肌、臀大肌和身体平衡能力。',
    steps: ['一脚向前迈步', '身体垂直下沉', '前膝对准脚尖', '后膝接近地面', '发力回到起始位置']
  },
  臀桥: {
    name: '臀桥',
    level: '标准',
    muscles: '主要锻炼臀大肌和后侧链稳定性。',
    steps: ['仰卧屈膝', '脚跟靠近臀部', '臀部发力抬髋', '顶端保持躯干平直', '缓慢下放']
  },
  开合跳: {
    name: '开合跳',
    level: '标准',
    muscles: '主要提升心肺能力和全身协调性。',
    steps: ['站立收紧核心', '跳起同时打开双腿', '双手上举', '落地缓冲', '保持稳定节奏']
  },
  平板支撑: {
    name: '平板支撑',
    level: '标准',
    muscles: '主要锻炼核心稳定和肩部支撑能力。',
    steps: ['肘部位于肩下方', '核心收紧', '身体保持一条直线', '臀部不要塌陷', '保持稳定呼吸']
  },
  卷腹: {
    name: '卷腹',
    level: '标准',
    muscles: '主要锻炼腹直肌和核心控制。',
    steps: ['下背贴近地面', '腹部发力卷起', '颈部保持自然', '不要借助手臂拉头', '缓慢下放']
  },
  默认: {
    name: '智能动作分析',
    level: '标准',
    muscles: '根据训练计划动作实时识别关节角度、对称度和动作质量。',
    steps: ['全身入镜', '保持光线充足', '动作过程稳定', '优先保证动作标准', '疼痛时立即停止']
  }
}

const movementInfo = computed(() => movementDb[props.movementName] || { ...movementDb.默认, name: props.movementName })
const averageScore = computed(() => averageBy('score'))
const canComplete = computed(() => history.value.length > 0 && (cameraOn.value || videoUploaded.value))
/** 前置摄像头使用镜像预览，与照镜子一致：本人左手在画面左侧 */
const shouldMirrorView = computed(() => cameraOn.value && !videoUploaded.value && facingMode.value === 'user')

function openReport() {
  if (!history.value.length) {
    ElMessage.warning('请先开启摄像头识别一段时间再生成报告')
    reportSnapshot.averageScore = 0
    reportSnapshot.elbow = 0
    reportSnapshot.shoulder = 0
    reportSnapshot.torso = 0
    reportSnapshot.suggestion = '请先完成一次实时分析，系统会根据关节角度和得分生成建议。'
    reportSnapshot.highlights = []
    reportVisible.value = true
    return
  }
  reportSnapshot.averageScore = averageBy('score')
  reportSnapshot.elbow = averageBy('elbow')
  reportSnapshot.shoulder = averageBy('shoulder')
  reportSnapshot.torso = averageBy('torso')
  const { suggestion, highlights } = buildProfessionalSuggestion({
    movementName: props.movementName,
    avgScore: reportSnapshot.averageScore,
    elbow: reportSnapshot.elbow,
    shoulder: reportSnapshot.shoulder,
    torso: reportSnapshot.torso,
    symmetry: metrics.symmetry
  })
  reportSnapshot.suggestion = suggestion
  reportSnapshot.highlights = highlights
  reportVisible.value = true
}

async function setupPose() {
  if (pose) {
    return
  }
  const win = window as any
  if (!win.Pose) {
    ElMessage.error('MediaPipe 加载失败，请检查网络或刷新页面')
    return
  }
  pose = new win.Pose({
    locateFile: (file: string) => `https://cdn.jsdelivr.net/npm/@mediapipe/pose@0.5.1675469404/${file}`
  })
  pose.setOptions({
    modelComplexity: 1,
    smoothLandmarks: true,
    minDetectionConfidence: 0.5,
    minTrackingConfidence: 0.5
  })
  pose.onResults(onPoseResults)
}

async function toggleCamera() {
  if (cameraOn.value) {
    await stopCamera()
    return
  }
  await startCamera()
}

async function startCamera() {
  await setupPose()
  if (!pose) {
    return
  }
  await stopCamera()
  stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: facingMode.value }, audio: false })
  if (!videoRef.value) {
    return
  }
  videoUploaded.value = false
  videoRef.value.srcObject = stream
  await videoRef.value.play()
  cameraOn.value = true
  cameraWasOpened.value = true
  await nextTick()
  syncCanvasSize()
  startAnalyzeLoop()
}

async function switchCamera() {
  facingMode.value = facingMode.value === 'user' ? 'environment' : 'user'
  if (cameraOn.value) {
    await startCamera()
  }
}

async function stopCamera() {
  if (cameraOn.value) {
    await persistSessionIfNeeded('camera_off')
  }
  cancelAnimationFrame(animationId)
  stream?.getTracks().forEach((track) => track.stop())
  stream = undefined
  cameraOn.value = false
  if (videoRef.value && !videoUploaded.value) {
    videoRef.value.srcObject = null
  }
}

function startAnalyzeLoop() {
  cancelAnimationFrame(animationId)
  const tick = async () => {
    const video = videoRef.value
    if (pose && video && video.readyState >= 2 && !sending) {
      sending = true
      await pose.send({ image: video })
      sending = false
    }
    if (cameraOn.value || videoUploaded.value) {
      animationId = requestAnimationFrame(tick)
    }
  }
  animationId = requestAnimationFrame(tick)
}

function onPoseResults(results: PoseResult) {
  syncCanvasSize()
  const canvas = canvasRef.value
  const video = videoRef.value
  if (!canvas || !video) {
    return
  }
  const ctx = canvas.getContext('2d')
  if (!ctx) {
    return
  }
  ctx.clearRect(0, 0, canvas.width, canvas.height)
  if (!results.poseLandmarks?.length) {
    feedbackText.value = '没有检测到完整人体，请后退一步并保持全身入镜。'
    speakFeedback(feedbackText.value)
    return
  }
  lastLandmarks.value = results.poseLandmarks
  const win = window as any
  win.drawConnectors?.(ctx, results.poseLandmarks, win.POSE_CONNECTIONS, { color: 'rgba(255,255,255,0.65)', lineWidth: 4 })
  win.drawLandmarks?.(ctx, results.poseLandmarks, { color: '#39ff14', fillColor: '#39ff14', lineWidth: 2, radius: 4 })
  updateMetrics(results.poseLandmarks)
}

function updateMetrics(landmarks: Landmark[]) {
  const leftElbow = calcAngle(landmarks[11], landmarks[13], landmarks[15])
  const rightElbow = calcAngle(landmarks[12], landmarks[14], landmarks[16])
  const leftShoulder = calcAngle(landmarks[23], landmarks[11], landmarks[13])
  const rightShoulder = calcAngle(landmarks[24], landmarks[12], landmarks[14])
  const torso = calcTorsoAngle(landmarks[12], landmarks[24])
  metrics.elbow = Math.round((leftElbow + rightElbow) / 2)
  metrics.shoulder = Math.round((leftShoulder + rightShoulder) / 2)
  metrics.torso = Math.round(torso)
  metrics.symmetry = clamp(Math.round(100 - Math.abs(leftElbow - rightElbow) - Math.abs(leftShoulder - rightShoulder) / 2), 0, 100)
  metrics.score = clamp(Math.round(100 - Math.abs(metrics.elbow - 90) * 0.35 - Math.abs(metrics.shoulder - 90) * 0.25 - Math.abs(metrics.torso - 165) * 0.2), 0, 100)
  history.value.push({ elbow: metrics.elbow, shoulder: metrics.shoulder, torso: metrics.torso, score: metrics.score })
  history.value = history.value.slice(-120)
  feedbackText.value = buildFeedback()
  speakFeedback(feedbackText.value)
}

function buildFeedback() {
  const name = props.movementName
  if (metrics.symmetry < 75) {
    return '左右动作不对称，请让两侧肩、肘和膝盖保持同一节奏。'
  }
  if (name.includes('深蹲')) {
    if (metrics.torso < 145) {
      return '背部需要更挺直，核心收紧，膝盖方向保持和脚尖一致。'
    }
    if (metrics.score < 80) {
      return '下蹲幅度和节奏还可以调整，保持背部挺直并让膝盖对准脚尖。'
    }
    return '深蹲姿态较稳定，继续保持背部挺直和核心收紧。'
  }
  if (name.includes('俯卧撑')) {
    if (metrics.elbow > 125) {
      return '肘部弯曲还不够，下降时胸部靠近地面，核心保持收紧。'
    }
    return '俯卧撑时身体保持一条直线，肘部不要过度外展。'
  }
  if (name.includes('箭步蹲')) {
    return '前膝保持对准脚尖，躯干保持直立，核心收紧不要左右晃动。'
  }
  if (name.includes('引体')) {
    return '肩胛下沉，避免耸肩，核心收紧，发力时保持身体稳定。'
  }
  if (name.includes('平板')) {
    return '核心收紧，头肩髋脚保持一条直线，臀部不要塌陷。'
  }
  if (metrics.score < 70) {
    return '动作偏差较大，请放慢速度，优先保持全身稳定和核心收紧。'
  }
  return '动作整体稳定，请保持当前姿态和呼吸节奏。'
}

function markCompleted() {
  const score = Number(metrics.score ?? 0)
  const avg = Number(averageScore.value ?? score)
  emit('analysis-completed', { movement_name: props.movementName, score, average_score: avg })
  ElMessage.success('已记录该动作完成情况')
}

function speakFeedback(text: string) {
  const now = Date.now()
  if (!text || now - lastSpokenAt.value < 10000) {
    return
  }
  if (text === lastSpoken.value) {
    return
  }
  lastSpoken.value = text
  lastSpokenAt.value = now
  void speakText(text, { voiceType: getVoiceType() })
}

function calcAngle(a?: Landmark, b?: Landmark, c?: Landmark) {
  if (!a || !b || !c) {
    return 0
  }
  const radians = Math.atan2(c.y - b.y, c.x - b.x) - Math.atan2(a.y - b.y, a.x - b.x)
  let degrees = Math.abs((radians * 180) / Math.PI)
  if (degrees > 180) {
    degrees = 360 - degrees
  }
  return degrees
}

function calcTorsoAngle(shoulder?: Landmark, hip?: Landmark) {
  if (!shoulder || !hip) {
    return 0
  }
  const radians = Math.atan2(shoulder.y - hip.y, shoulder.x - hip.x)
  return Math.abs((radians * 180) / Math.PI)
}

function syncCanvasSize() {
  const canvas = canvasRef.value
  const video = videoRef.value
  if (!canvas || !video) {
    return
  }
  const rect = video.getBoundingClientRect()
  canvas.width = Math.max(1, Math.round(rect.width))
  canvas.height = Math.max(1, Math.round(rect.height))
}

async function uploadVideo(option: any) {
  try {
    await setupPose()
    const form = new FormData()
    form.append('file', option.file)
    // Do not manually set Content-Type for FormData; axios will add the correct boundary.
    const { data } = await http.post(`/pose/upload?movement_name=${encodeURIComponent(props.movementName)}`, form)
    stopCamera()
    videoUploaded.value = true
    uploadedUrl && URL.revokeObjectURL(uploadedUrl)
    uploadedUrl = URL.createObjectURL(option.file)
    if (videoRef.value) {
      videoRef.value.srcObject = null
      videoRef.value.src = uploadedUrl
      videoRef.value.loop = true
      await videoRef.value.play()
    }
    option.onSuccess?.({})
    syncCanvasSize()
    startAnalyzeLoop()
    const score = data?.analysis?.score
    const suggestions = data?.analysis?.suggestions || []
    if (typeof score === 'number') {
      feedbackText.value = `视频分析完成：得分 ${score} 分。${suggestions[0] || '请保持全身入镜并稳定节奏。'}`
      speakFeedback(feedbackText.value)
      ElMessage.success(`视频已上传并分析完成（得分 ${score}）`)
    } else {
      ElMessage.success('视频已上传，开始抽帧分析')
    }
  } catch (error) {
    option.onError?.(error)
    ElMessage.error('视频上传或分析失败')
  }
}

function angleClass(value: number) {
  const diff = Math.abs(value - 90)
  if (diff <= 15) {
    return 'good'
  }
  if (diff <= 30) {
    return 'warn'
  }
  return 'bad'
}

function percentClass(value: number) {
  if (value >= 85) {
    return 'good'
  }
  if (value >= 70) {
    return 'warn'
  }
  return 'bad'
}

function averageAngle(key: 'elbow' | 'shoulder' | 'torso') {
  return averageBy(key)
}

function averageBy(key: 'elbow' | 'shoulder' | 'torso' | 'score') {
  if (!history.value.length) {
    return 0
  }
  return Math.round(history.value.reduce((total, item) => total + item[key], 0) / history.value.length)
}

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value))
}

function buildProfessionalSuggestion(input: {
  movementName: string
  avgScore: number
  elbow: number
  shoulder: number
  torso: number
  symmetry: number
}) {
  const name = input.movementName
  const highlights: string[] = []
  const angleTip: string[] = []

  if (input.symmetry < 75) {
    highlights.push('左右对称性不足（建议放慢节奏，先保证两侧同步发力）')
  }
  if (name.includes('深蹲')) {
    if (input.torso < 145) {
      highlights.push('躯干前倾偏多（核心收紧、胸廓上提，髋主导下蹲）')
      angleTip.push('练习“髋铰链”与靠墙深蹲，优先保持脊柱中立')
    }
    if (input.avgScore < 75) {
      angleTip.push('控制下降速度，底部停顿 0.5-1 秒，膝盖始终对准脚尖')
    }
  } else if (name.includes('俯卧撑')) {
    if (input.elbow > 120) {
      highlights.push('屈肘幅度不足（下降更深，胸部接近地面）')
      angleTip.push('可先用斜板/跪姿俯卧撑，逐步增加活动范围')
    }
    if (input.shoulder < 70 || input.shoulder > 120) {
      highlights.push('肩部角度波动大（保持肩胛稳定，避免耸肩/塌肩）')
    }
  } else if (name.includes('平板')) {
    if (input.torso < 155) {
      highlights.push('躯干线条不够平直（避免塌腰，骨盆微后倾）')
      angleTip.push('缩短支撑时间，分组累计，优先保证姿态标准')
    }
  }

  let level: string
  if (input.avgScore >= 85) level = '优秀'
  else if (input.avgScore >= 70) level = '合格'
  else level = '需要改进'

  const suggestion = [
    `综合评估：${level}（平均得分 ${input.avgScore}）。`,
    highlights.length ? `重点问题：${highlights.join('；')}。` : '重点问题：未发现明显动作风险点，保持节奏与呼吸即可。',
    angleTip.length ? `训练建议：${angleTip.slice(0, 2).join('；')}。` : '训练建议：保持稳定呼吸与控制速度，优先保证动作标准。',
    '提示：若出现疼痛或明显代偿，请立即停止并调整。'
  ].join('\n')

  return { suggestion, highlights }
}

watch(
  () => props.movementName,
  () => {
    history.value = []
    cameraWasOpened.value = false
    lastSpoken.value = ''
    feedbackText.value = '请保持全身入镜，动作稳定后系统会给出实时建议。'
  }
)

onMounted(setupPose)
onBeforeUnmount(() => {
  pageClosing = true
  void persistSessionIfNeeded('unmount')
  void stopCamera()
  stopTts()
  uploadedUrl && URL.revokeObjectURL(uploadedUrl)
})

async function persistSessionIfNeeded(reason: 'camera_off' | 'unmount') {
  const hasHistory = history.value.length > 0
  const shouldPersist = hasHistory || (cameraWasOpened.value && reason === 'camera_off')
  if (!shouldPersist) return
  try {
    const summary_metrics = {
      average_elbow: hasHistory ? averageBy('elbow') : 0,
      average_shoulder: hasHistory ? averageBy('shoulder') : 0,
      average_torso: hasHistory ? averageBy('torso') : 0,
      symmetry: Number(metrics.symmetry ?? 0),
      source: reason
    }
    const payload = {
      movement_name: props.movementName,
      landmarks: lastLandmarks.value || [],
      summary_metrics,
      average_score: hasHistory ? averageBy('score') : 0
    }
    await http.post('/pose/frame', payload)
    emit('session-saved')
  } catch (e: any) {
    console.error('姿态分析记录保存失败:', e)
  }
}
</script>

<style scoped>
.pose-analyzer {
  position: relative;
  height: 100%;
  overflow: hidden;
  background: #000;
}

.pose-analyzer.embedded {
  height: auto;
  overflow: visible;
  background: transparent;
}

.pose-stage {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
  background: radial-gradient(circle at center, #111827 0%, #020617 100%);
}

.pose-video,
.pose-canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

.pose-video {
  object-fit: cover;
}

.pose-canvas {
  pointer-events: none;
}

.mirror-view {
  transform: scaleX(-1);
}

.embedded-layout {
  display: grid;
  grid-template-columns: minmax(520px, 1.7fr) minmax(220px, 0.62fr) minmax(230px, 0.62fr);
  align-items: stretch;
  gap: 12px;
  width: 100%;
  padding: 12px;
  border: 1px solid #e5e7eb;
  border-radius: 22px;
  background: #f8fafc;
  box-sizing: border-box;
}

.embed-video-col,
.embed-info-card,
.embed-metrics-card {
  min-width: 0;
}

.embed-video-box {
  position: relative;
  overflow: hidden;
  aspect-ratio: 16 / 9;
  min-height: 230px;
  max-height: 340px;
  border-radius: 14px;
  background: radial-gradient(circle at center, #111827 0%, #020617 100%);
}

.embed-hint {
  position: absolute;
  inset: 0;
  display: grid;
  place-content: center;
  padding: 28px;
  text-align: center;
  color: #e5e7eb;
  background: linear-gradient(135deg, rgba(15, 23, 42, 0.84), rgba(3, 7, 18, 0.7));
}

.embed-hint h3 {
  margin: 0 0 8px;
  font-size: 22px;
}

.embed-hint p {
  margin: 0;
  color: #cbd5e1;
}

.embed-controls {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 10px;
}

.embedded :deep(.el-button) {
  height: 30px;
  padding: 6px 12px;
  font-size: 12px;
}

.embed-info-card,
.embed-metrics-card {
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  background: #fff;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
}

.embed-info-card {
  padding: 14px;
  align-self: stretch;
}

.embed-metrics-card {
  padding: 14px;
  align-self: stretch;
}

.no-camera-hint {
  position: absolute;
  inset: 0;
  display: grid;
  place-content: center;
  text-align: center;
  color: #e5e7eb;
  background: linear-gradient(135deg, rgba(15, 23, 42, 0.82), rgba(3, 7, 18, 0.65));
}

.no-camera-hint h2 {
  margin: 0 0 12px;
  font-size: 38px;
}

.no-camera-hint p {
  max-width: 520px;
  margin: 0;
  color: #cbd5e1;
}

.overlay-panel {
  position: absolute;
  z-index: 2;
  border: 1px solid rgba(148, 163, 184, 0.25);
  border-radius: 22px;
  background: rgba(0, 0, 0, 0.66);
  color: #fff;
  backdrop-filter: blur(14px);
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.35);
}

.info-card {
  top: 28px;
  left: 28px;
  width: 360px;
  padding: 22px 24px;
}

.embedded .info-card {
  width: 300px;
}

.movement-head {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 24px;
}

.movement-head span {
  padding: 4px 12px;
  border-radius: 999px;
  background: rgba(34, 197, 94, 0.2);
  color: #39ff14;
  font-size: 14px;
}

.movement-desc {
  margin: 14px 0;
  color: #e5e7eb;
  line-height: 1.7;
}

.info-card ul {
  margin: 0;
  padding-left: 18px;
  color: #f8fafc;
  line-height: 1.9;
}

.data-panel {
  top: 28px;
  right: 28px;
  width: 250px;
  padding: 20px;
}

.angle-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
  font-size: 16px;
}

.angle-row strong {
  font-size: 24px;
}

.score-box {
  margin: 10px 0 12px;
  padding: 12px;
  border-radius: 14px;
  background: rgba(15, 23, 42, 0.8);
  text-align: center;
}

.score-box span {
  display: block;
  color: #cbd5e1;
}

.score-box strong {
  color: #39ff14;
  font-size: 42px;
  line-height: 1;
}

.feedback-box {
  padding-top: 10px;
  border-top: 1px solid rgba(148, 163, 184, 0.24);
}

.feedback-box span {
  color: #93c5fd;
  font-size: 13px;
}

.feedback-box p {
  margin: 4px 0 0;
  color: #fff;
  line-height: 1.45;
}

.good {
  color: #39ff14;
}

.warn {
  color: #facc15;
}

.bad {
  color: #fb7185;
}

.bottom-controls {
  position: absolute;
  left: 50%;
  bottom: 28px;
  z-index: 3;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 18px;
  width: min(920px, calc(100% - 56px));
  padding: 18px 22px;
  border-radius: 28px;
  background: rgba(0, 0, 0, 0.72);
  backdrop-filter: blur(14px);
  transform: translateX(-50%);
}

.report-btn {
  border-color: #f97316;
  background: #f97316;
  color: #fff;
  font-weight: 800;
}

.report-content {
  line-height: 1.9;
}

.embedded .movement-head {
  font-size: 18px;
  color: #111827;
}

.embedded .movement-desc {
  margin: 10px 0;
  color: #475569;
  line-height: 1.55;
}

.embedded .embed-info-card ul {
  margin: 0;
  padding-left: 18px;
  color: #1f2937;
  line-height: 1.6;
}

.embedded .feedback-box {
  border-top-color: #e5e7eb;
}

.embedded .feedback-box p {
  color: #111827;
}

.complete-btn {
  margin-top: 10px;
  width: 100%;
  border-radius: 12px;
  font-weight: 800;
}

.embed-report-btn {
  width: 100%;
  margin-top: 10px;
}

@media (max-width: 1120px) {
  .embedded-layout {
    grid-template-columns: 1fr;
  }

  .embed-video-box {
    min-height: 300px;
  }
}
</style>
