<template>
  <section class="page movements-page">
    <div class="atlas-shell">
      <aside class="body-nav">
        <div class="nav-title">
          <strong>动作图谱</strong>
        </div>
        <button
          v-for="part in bodyParts"
          :key="part.value"
          class="body-tab"
          :class="{ active: activeBodyPart === part.value }"
          @click="selectBodyPart(part.value)"
        >
          <span>{{ part.label }}</span>
        </button>
      </aside>

      <main class="atlas-main">
        <div class="atlas-head">
          <div>
            <p>智能动作库</p>
            <h1>{{ currentBodyPartLabel }}训练动作图谱</h1>
            <span>选择动作后可查看步骤、要点、常见错误，并跳转到姿态分析模块。</span>
          </div>
          <el-button type="primary" :loading="loading" @click="loadExercises">刷新动作</el-button>
        </div>

        <div v-loading="loading" class="exercise-grid">
          <article v-for="exercise in exercises" :key="exercise.id" class="exercise-card" @click="openDetail(exercise)">
            <div class="thumb-wrap">
              <ExerciseImage class="thumb-img" :src="exercise.image_url" :alt="exercise.name" :body-part="exercise.body_part" />
              <span class="difficulty">{{ exercise.difficulty_label || difficultyLabel(exercise.difficulty) }}</span>
            </div>
            <div class="card-body">
              <h3>{{ exercise.name }}</h3>
              <p>{{ exercise.target_muscle }} · {{ exercise.equipment }}</p>
              <div class="tag-row">
                <span>{{ exercise.body_part_label || exercise.body_part }}</span>
                <span>{{ exercise.steps?.length || 0 }} 步</span>
              </div>
            </div>
          </article>
        </div>
      </main>
    </div>

    <el-drawer v-model="drawerVisible" class="exercise-drawer" size="520px" :title="selectedExercise ? selectedExercise.name : '动作详情'">
      <div v-if="selectedExercise" class="detail-content">
        <ExerciseImage class="detail-img" :src="selectedExercise.image_url" :alt="selectedExercise.name" :body-part="selectedExercise.body_part" />
        <div class="detail-tags">
          <el-tag type="success">{{ selectedExercise.difficulty_label || difficultyLabel(selectedExercise.difficulty) }}</el-tag>
          <el-tag>{{ selectedExercise.equipment }}</el-tag>
          <el-tag type="warning">{{ selectedExercise.body_part_label || selectedExercise.body_part }}</el-tag>
        </div>

        <section class="detail-section">
          <h3>目标肌肉</h3>
          <p>{{ selectedExercise.target_muscles.join(' / ') }}</p>
        </section>

        <section class="detail-section">
          <h3>动作步骤</h3>
          <ol>
            <li v-for="step in selectedExercise.steps" :key="step">{{ step }}</li>
          </ol>
        </section>

        <section class="detail-section">
          <h3>常见错误</h3>
          <ul>
            <li v-for="error in selectedExercise.common_errors" :key="error">{{ error }}</li>
          </ul>
        </section>

        <section class="detail-section">
          <h3>标准姿态数据</h3>
          <div class="pose-template">
            <span v-for="(range, key) in selectedExercise.standard_pose.main_angles" :key="key">
              {{ key }}：{{ range[0] }}°-{{ range[1] }}°
            </span>
          </div>
        </section>

        <el-button class="analyze-btn" type="primary" @click="startPoseAnalysis(selectedExercise)">开始姿态分析</el-button>
      </div>
    </el-drawer>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { http } from '../../api/http'
import ExerciseImage from '../../components/ExerciseImage.vue'

type Exercise = {
  id: string
  name: string
  difficulty: string
  difficulty_label?: string
  equipment: string
  body_part: string
  body_part_label?: string
  target_muscle: string
  target_muscles: string[]
  secondary_muscles: string[]
  steps: string[]
  common_errors: string[]
  image_url: string
  standard_pose: {
    main_angles: Record<string, [number, number]>
    keypoints: string[]
  }
  raw?: { name?: string }
}

const router = useRouter()
const loading = ref(false)
const activeBodyPart = ref('chest')
const exercises = ref<Exercise[]>([])
const selectedExercise = ref<Exercise | null>(null)
const drawerVisible = ref(false)

const bodyParts = [
  { value: 'chest', label: '胸部' },
  { value: 'back', label: '背部' },
  { value: 'waist', label: '腰腹' },
  { value: 'shoulders', label: '肩部' },
  { value: 'upper arms', label: '上臂' },
  { value: 'lower arms', label: '前臂' },
  { value: 'upper legs', label: '大腿' },
  { value: 'lower legs', label: '小腿' },
  { value: 'cardio', label: '有氧' }
]

const englishNameToPoseMovement: Record<string, string> = {
  'push up': '俯卧撑',
  'wide push up': '俯卧撑',
  'bodyweight squat': '徒手深蹲',
  lunge: '箭步蹲',
  'front plank': '平板支撑',
  crunch: '卷腹',
  'pull up': '引体向上',
  'dumbbell row': '俯身划船',
  'jumping jack': '开合跳',
  'dumbbell shoulder press': '肩部推举',
  'dumbbell biceps curl': '哑铃弯举',
  'bench dip': '臂屈伸'
}

const currentBodyPartLabel = computed(() => bodyParts.find((p) => p.value === activeBodyPart.value)?.label || '训练')

async function selectBodyPart(bodyPart: string) {
  activeBodyPart.value = bodyPart
  await loadExercises()
}

async function loadExercises() {
  loading.value = true
  try {
    exercises.value = (await http.get('/exercises/list', { params: { bodyPart: activeBodyPart.value, limit: 36 } })).data
  } finally {
    loading.value = false
  }
}

function openDetail(exercise: Exercise) {
  selectedExercise.value = exercise
  drawerVisible.value = true
}

function startPoseAnalysis(exercise: Exercise) {
  localStorage.setItem('selectedExerciseTemplate', JSON.stringify(exercise))
  router.push({ path: '/pose', query: { movement: resolvePoseMovement(exercise), exerciseId: exercise.id } })
}

function resolvePoseMovement(exercise: Exercise) {
  const rawName = String(exercise.raw?.name || exercise.name || '').toLowerCase()
  return englishNameToPoseMovement[rawName] || exercise.name
}

function difficultyLabel(value: string) {
  const map: Record<string, string> = {
    beginner: '初级',
    intermediate: '中级',
    advanced: '高级'
  }
  return map[value] || '标准'
}

onMounted(loadExercises)
</script>

<style scoped>
.movements-page {
  overflow: hidden;
}

.atlas-shell {
  display: grid;
  grid-template-columns: 210px 1fr;
  gap: 22px;
  width: min(1380px, calc(100% - 48px));
  height: calc(100vh - 118px);
  margin: 0 auto;
}

.body-nav {
  padding: 18px;
  border-radius: 28px;
  background: linear-gradient(180deg, #111827, #1e3a8a);
  color: #fff;
  box-shadow: 0 18px 40px rgba(30, 58, 138, 0.25);
}

.nav-title {
  margin-bottom: 18px;
}

.nav-title span {
  display: block;
  color: #bfdbfe;
  font-size: 13px;
}

.nav-title strong {
  font-size: 22px;
}

.body-tab {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  margin-bottom: 10px;
  padding: 12px 14px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.08);
  color: #e5e7eb;
  cursor: pointer;
}

.body-tab.active {
  border-color: #67e8f9;
  background: #eff6ff;
  color: #1d4ed8;
  font-weight: 800;
}

.body-tab small {
  color: inherit;
  opacity: 0.7;
}

.atlas-main {
  min-width: 0;
  padding: 24px;
  border-radius: 30px;
  background: rgba(255, 255, 255, 0.78);
  box-shadow: 0 20px 60px rgba(99, 102, 241, 0.16);
}

.atlas-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 18px;
}

.atlas-head p {
  margin: 0 0 4px;
  color: #2563eb;
  font-weight: 800;
}

.atlas-head h1 {
  margin: 0 0 6px;
  color: #111827;
  font-size: 30px;
}

.atlas-head span {
  color: #64748b;
}

.exercise-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(210px, 1fr));
  gap: 18px;
  max-height: calc(100vh - 235px);
  overflow-y: auto;
  padding: 4px 6px 10px;
}

.exercise-card {
  overflow: hidden;
  border: 1px solid #e5e7eb;
  border-radius: 22px;
  background: #fff;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.exercise-card:hover {
  box-shadow: 0 18px 34px rgba(37, 99, 235, 0.18);
  transform: translateY(-4px);
}

.thumb-wrap {
  position: relative;
  height: 180px;
  background: #f8fafc;
}

.thumb-wrap img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.thumb-img {
  width: 100%;
  height: 100%;
}

.difficulty {
  position: absolute;
  top: 12px;
  right: 12px;
  padding: 4px 10px;
  border-radius: 999px;
  background: #22c55e;
  color: #fff;
  font-size: 12px;
  font-weight: 800;
}

.card-body {
  padding: 14px;
}

.card-body h3 {
  margin: 0 0 8px;
  color: #111827;
  font-size: 17px;
  line-height: 1.35;
}

.card-body p {
  margin: 0 0 12px;
  color: #64748b;
}

.tag-row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.tag-row span {
  padding: 5px 9px;
  border-radius: 999px;
  background: #eff6ff;
  color: #2563eb;
  font-size: 12px;
  font-weight: 700;
}

.detail-content {
  padding-right: 4px;
}

.detail-img {
  width: 100%;
  height: 260px;
  object-fit: contain;
  border-radius: 22px;
  background: #f8fafc;
}

.detail-tags {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin: 16px 0;
}

.detail-section {
  margin-top: 18px;
  padding: 16px;
  border-radius: 18px;
  background: #f8fafc;
}

.detail-section h3 {
  margin: 0 0 10px;
  color: #111827;
}

.detail-section p,
.detail-section li {
  color: #334155;
  line-height: 1.75;
}

.pose-template {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.pose-template span {
  padding: 7px 10px;
  border-radius: 12px;
  background: #e0f2fe;
  color: #0369a1;
  font-weight: 700;
}

.analyze-btn {
  width: 100%;
  height: 44px;
  margin-top: 18px;
  border-radius: 22px;
}

@media (max-width: 980px) {
  .atlas-shell {
    grid-template-columns: 1fr;
    height: auto;
  }

  .body-nav {
    display: flex;
    overflow-x: auto;
    gap: 10px;
  }

  .body-tab {
    min-width: 128px;
  }
}
</style>
