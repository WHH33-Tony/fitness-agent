<template>
  <section class="page training-page">
    <div class="panel training-panel">
      <template v-if="!showPlan">
        <h2>定制训练计划问卷</h2>
        <el-steps :active="step" finish-status="success" simple>
          <el-step title="基础信息" />
          <el-step title="目标部位" />
          <el-step title="运动习惯" />
          <el-step title="补充能力" />
        </el-steps>

        <div class="question-card">
          <div v-if="step === 0" class="question-grid">
            <el-form-item label="身高(cm)"><el-input-number v-model="form.height" :min="120" :max="230" /></el-form-item>
            <el-form-item label="体重(kg)"><el-input-number v-model="form.weight" :min="30" :max="200" /></el-form-item>
            <el-form-item label="年龄(岁)"><el-input-number v-model="form.age" :min="10" :max="100" /></el-form-item>
            <ChoiceGroup v-model="form.gender" title="性别" :options="['男', '女']" />
            <ChoiceGroup v-model="form.bodyShape" title="体型" :options="['直筒型', '梨形', '沙漏型', '苹果形']" />
          </div>

          <div v-else-if="step === 1" class="question-grid">
            <ChoiceGroup v-model="form.goal" title="要达成的目标" :options="['瘦身减重', '塑形/增肌', '保持健康']" />
            <ChoiceGroup v-model="form.injury" title="伤病部位" :options="['无', '膝盖', '腰部']" />
            <ChoiceGroup v-model="form.focus" title="重点改善部位" multiple :options="['胸部', '肩臂', '腰腹', '臀腿', '全身']" />
          </div>

          <div v-else-if="step === 2" class="question-grid">
            <ChoiceGroup v-model="form.preference" title="运动偏好" multiple :options="['操课', '跳绳', '跑步']" />
            <el-form-item label="每天运动时间">
              <el-select v-model="form.duration" placeholder="请选择">
                <el-option label="15分钟" value="15分钟" />
                <el-option label="30分钟" value="30分钟" />
                <el-option label="45分钟" value="45分钟" />
                <el-option label="60分钟以上" value="60分钟以上" />
              </el-select>
            </el-form-item>
            <el-form-item label="每周训练次数">
              <el-select v-model="form.weeklyCount" placeholder="请选择">
                <el-option label="每周1-2次" value="1-2次" />
                <el-option label="每周3-4次" value="3-4次" />
                <el-option label="每周5次以上" value="5次以上" />
              </el-select>
            </el-form-item>
            <ChoiceGroup v-model="form.equipment" title="是否使用运动器械" :options="['不使用', '哑铃', '弹力带', '都可以']" />
          </div>

          <div v-else class="question-grid">
            <el-form-item label="连续标准俯卧撑"><el-input-number v-model="form.pushups" :min="0" /></el-form-item>
            <el-form-item label="连续标准深蹲"><el-input-number v-model="form.squats" :min="0" /></el-form-item>
            <el-form-item label="连续标准卷腹"><el-input-number v-model="form.crunches" :min="0" /></el-form-item>
            <ChoiceGroup v-model="form.stairsTired" title="上五层楼后是否疲惫或呼吸急促" :options="['是', '否']" />
          </div>
        </div>

        <div class="step-actions">
          <el-button :disabled="step === 0" @click="step--">上一步</el-button>
          <el-button v-if="step < 3" type="primary" @click="step++">下一步</el-button>
          <el-button v-else type="primary" :loading="loading" @click="generatePlan">生成训练计划</el-button>
        </div>
      </template>

      <template v-else-if="!activeTrainingDay">
        <div class="plan-tools">
          <el-button link type="primary" @click="resetPlan">重新做计划 &gt;</el-button>
        </div>
        <div class="plan-calendar">
          <div class="calendar-head">
            <div>
              <h2>本周训练安排</h2>
              <p>计划开始日：{{ planStartText }}</p>
            </div>
          </div>

          <div v-if="recommendedDay" class="recommend-card">
            <div>
              <strong>{{ recommendedDay.isToday ? '今天是训练日，快去开练！' : '今天无训练安排，推荐训练：' }}</strong>
              <p>{{ recommendedDay.dateText }} {{ recommendedDay.day }} · {{ recommendedDay.focus }}</p>
            </div>
            <el-button type="success" @click="startTraining(recommendedDay)">开练推荐训练</el-button>
          </div>

          <div class="calendar-grid">
            <div v-for="day in calendarSchedule" :key="day.key" class="calendar-day" :class="{ today: day.isToday, rest: isRestDay(day) }">
              <div class="day-date">{{ day.dateText }}</div>
              <h3>{{ day.day }} · {{ day.focus }}</h3>
              <ul>
                <li v-for="item in day.items" :key="item">{{ item }}</li>
              </ul>
              <div v-if="isRestDay(day)" class="rest-tag">本日休息</div>
              <div class="day-actions">
                <el-button v-if="!isRestDay(day)" class="start-btn" type="success" @click="startTraining(day)">开练</el-button>
                <el-button v-if="!isRestDay(day)" @click="markRest(day)">标记休息</el-button>
                <el-button v-else @click="cancelRest(day)">取消休息</el-button>
              </div>
            </div>
          </div>
        </div>
      </template>

      <template v-else-if="activeTrainingDay">
        <div class="training-detail" :class="{ analyzing: activeAnalysisItem }">
          <div class="plan-tools">
            <el-button @click="activeTrainingDay = null">返回训练日历</el-button>
          </div>
          <h2>{{ activeTrainingDay.dateText }} {{ activeTrainingDay.day }}：{{ activeTrainingDay.focus }}</h2>
          <p class="muted">按当天训练动作逐项进行，点击开始分析后会在当前页面打开摄像头并对照标准动作评判。</p>
          <div v-if="!activeAnalysisItem" class="movement-list">
            <div v-for="item in activeTrainingDay.items" :key="item" class="movement-row">
              <strong>{{ item }}</strong>
              <el-button type="primary" @click="startAnalysis(item)">开始分析</el-button>
            </div>
          </div>
          <div v-else class="analysis-panel">
            <div class="plan-tools">
              <el-button @click="activeAnalysisItem = null">返回动作列表</el-button>
            </div>
            <h3>正在分析：{{ activeAnalysisItem.name }}</h3>
            <div class="burned-strip">
              <strong>今日已消耗：{{ todayBurned }} kcal</strong>
            </div>
            <div class="agent-strip">
              <el-button type="info" plain @click="askAgentForMovement">询问Agent关于此动作</el-button>
            </div>
            <PoseAnalyzer :movement-name="activeAnalysisItem.name" embedded @analysis-completed="onAnalysisCompleted" />
          </div>
        </div>
      </template>

    </div>
  </section>
</template>

<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus'
import { computed, defineComponent, h, onMounted, reactive, ref } from 'vue'

import { http } from '../../api/http'
import PoseAnalyzer from '../../components/PoseAnalyzer.vue'
import { useRouter } from 'vue-router'

type ChoiceValue = string | string[]
type TrainingDay = {
  key: string
  dateText: string
  day: string
  focus: string
  items: string[]
  isToday: boolean
}

const ChoiceGroup = defineComponent({
  props: {
    modelValue: { type: [String, Array], required: true },
    title: { type: String, required: true },
    options: { type: Array<string>, required: true },
    multiple: { type: Boolean, default: false }
  },
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    function toggle(option: string) {
      if (!props.multiple) {
        emit('update:modelValue', option)
        return
      }
      const current = Array.isArray(props.modelValue) ? props.modelValue : []
      emit('update:modelValue', current.includes(option) ? current.filter((item) => item !== option) : [...current, option])
    }
    return () =>
      h('div', { class: 'choice-block' }, [
        h('label', props.title),
        h(
          'div',
          { class: 'choice-list' },
          props.options.map((option) => {
            const selected = props.multiple ? (props.modelValue as string[]).includes(option) : props.modelValue === option
            return h('button', { type: 'button', class: ['choice-pill', { active: selected }], onClick: () => toggle(option) }, option)
          })
        )
      ])
  }
})

const step = ref(0)
const loading = ref(false)
const showPlan = ref(false)
const generatedPlan = ref<any>()
const generatedAt = ref('')
const planId = ref<number | string>('')
const activeTrainingDay = ref<any>(null)
const activeAnalysisItem = ref<{ name: string } | null>(null)
const restDates = ref<string[]>([])
const todayBurned = ref(0)
const todayRecords = ref<Record<string, number>>({})
const router = useRouter()
const form = reactive({
  height: 175,
  weight: 65,
  age: 22,
  gender: '男' as ChoiceValue,
  bodyShape: '直筒型' as ChoiceValue,
  injury: '无' as ChoiceValue,
  goal: '塑形/增肌' as ChoiceValue,
  focus: ['全身'] as string[],
  preference: ['跑步'] as string[],
  duration: '30分钟',
  weeklyCount: '3-4次',
  equipment: '不使用' as ChoiceValue,
  pushups: 10,
  squats: 20,
  crunches: 15,
  stairsTired: '否' as ChoiceValue
})

const dayOffsetMap: Record<string, number> = {
  周一: 0,
  周二: 1,
  周三: 2,
  周四: 3,
  周五: 4,
  周六: 5,
  周日: 6
}

const planStartDate = computed(() => startOfBeijingWeek(new Date().toISOString()))
const planStartText = computed(() => formatBeijingDate(planStartDate.value))
const todayText = computed(() => formatBeijingDate(toBeijingDate(new Date().toISOString())))
const calendarSchedule = computed(() => {
  const schedule = generatedPlan.value?.weekly_schedule || []
  return schedule.map((day: any, index: number) => {
    const date = new Date(planStartDate.value)
    date.setUTCDate(date.getUTCDate() + (dayOffsetMap[day.day] ?? index))
    const dateText = formatBeijingDate(date)
    return {
      ...day,
      key: `${day.day}-${dateText}`,
      date,
      dateText,
      isToday: dateText === todayText.value
    }
  }).sort((a: TrainingDay, b: TrainingDay) => a.dateText.localeCompare(b.dateText))
})

const recommendedDay = computed(() => {
  const availableDays = calendarSchedule.value.filter((day: TrainingDay) => !isRestDay(day))
  const today = availableDays.find((day: TrainingDay) => day.isToday)
  if (today) {
    return today
  }
  return availableDays.find((day: TrainingDay) => day.dateText >= todayText.value) || availableDays[0]
})

async function generatePlan() {
  loading.value = true
  const injuryList = Array.isArray(form.injury) ? form.injury : [form.injury]
  await http.post('/plans/questionnaire', {
    physique: `${form.gender}，${form.bodyShape}，身高${form.height}cm，体重${form.weight}kg`,
    fitness_goal: `${form.goal}，${form.weeklyCount}训练`,
    exercise_level: `俯卧撑${form.pushups}个，深蹲${form.squats}个，卷腹${form.crunches}个`,
    injury_history: injuryList.filter((item) => item !== '无'),
    avoid_movements: injuryList.includes('膝盖') ? ['跳跃冲击动作'] : [],
    extra_info: { ...form }
  })
  const plans = (await http.get('/plans')).data
  planId.value = plans[0]?.id || ''
  generatedPlan.value = plans[0]?.plan_data
  generatedAt.value = plans[0]?.generated_at || new Date().toISOString()
  restDates.value = loadRestDates()
  showPlan.value = true
  loading.value = false
  ElMessage.success('训练计划已生成')
}

function beijingDateTextOfNow() {
  const now = toBeijingDate(new Date().toISOString())
  return formatBeijingDate(now)
}

async function loadTodayBurned() {
  const rows = (await http.get('/sports/daily')).data || []
  const todayText = beijingDateTextOfNow()
  const found = Array.isArray(rows) ? rows.find((item: any) => item.exercise_date === todayText) : null
  todayBurned.value = Number(found?.calories_burned ?? 0)
  todayRecords.value = (found?.exercise_records && typeof found.exercise_records === 'object') ? found.exercise_records : {}
}

const calorieMap: Record<string, number> = {
  徒手深蹲: 15,
  深蹲: 15,
  俯卧撑: 10,
  箭步蹲: 12,
  臀桥: 8,
  开合跳: 12,
  登山跑: 12,
  卷腹: 6,
  平板支撑: 5,
  引体向上: 10,
  俯身划船: 10
}

function calorieOfMovement(name: string) {
  const cleaned = cleanMovementName(name)
  return Number(calorieMap[cleaned] ?? 8)
}

async function onAnalysisCompleted(payload: { movement_name: string; score: number; average_score: number }) {
  const movement = cleanMovementName(payload?.movement_name || activeAnalysisItem.value?.name || '')
  const kcal = calorieOfMovement(movement)
  const todayText = beijingDateTextOfNow()
  const nextRecords = { ...(todayRecords.value || {}) }
  nextRecords[movement] = Number(nextRecords[movement] ?? 0) + 1
  const nextBurned = Number(todayBurned.value ?? 0) + kcal

  await http.post('/sports/daily', { exercise_date: todayText, calories_burned: nextBurned, exercise_records: nextRecords })
  todayBurned.value = nextBurned
  todayRecords.value = nextRecords
  ElMessage.success(`已记录：${movement} +${kcal} kcal（今日累计 ${nextBurned}）`)
}

function askAgentForMovement() {
  if (!activeAnalysisItem.value?.name) {
    return
  }
  const movement = cleanMovementName(activeAnalysisItem.value.name)
  const prompt = `帮我分析刚才的${movement}动作（给出纠错建议），并告诉我今天摄入多少蛋白质合适。`
  router.push({ path: '/qa', query: { q: prompt } })
}

function resetPlan() {
  showPlan.value = false
  activeTrainingDay.value = null
  activeAnalysisItem.value = null
  restDates.value = []
  step.value = 0
}

function startTraining(day: any) {
  activeTrainingDay.value = day
  activeAnalysisItem.value = null
}

function startAnalysis(item: string) {
  activeAnalysisItem.value = { name: cleanMovementName(item) }
}

function cleanMovementName(item: string) {
  return item.split(' ')[0]
}

function isRestDay(day: TrainingDay) {
  return restDates.value.includes(day.dateText)
}

async function markRest(day: TrainingDay) {
  await ElMessageBox.confirm(`确定将 ${day.dateText} ${day.day} 标记为休息吗？`, '标记休息', {
    confirmButtonText: '确定休息',
    cancelButtonText: '取消',
    type: 'warning'
  })
  localStorage.setItem(restStorageKey(day.dateText), '1')
  restDates.value = loadRestDates()
  ElMessage.success('已标记为休息')
}

function cancelRest(day: TrainingDay) {
  localStorage.removeItem(restStorageKey(day.dateText))
  restDates.value = loadRestDates()
  ElMessage.success('已取消休息')
}

function restStorageKey(dateText: string) {
  return `rest_${planId.value || 'latest'}_${dateText}`
}

function loadRestDates() {
  return calendarSchedule.value.map((day: TrainingDay) => day.dateText).filter((dateText: string) => localStorage.getItem(restStorageKey(dateText)) === '1')
}

function toBeijingDate(input: string) {
  const date = new Date(input)
  return new Date(date.getTime() + 8 * 60 * 60 * 1000)
}

function startOfBeijingWeek(input: string) {
  const date = toBeijingDate(input)
  const day = date.getUTCDay() || 7
  date.setUTCDate(date.getUTCDate() - day + 1)
  date.setUTCHours(0, 0, 0, 0)
  return date
}

function formatBeijingDate(date: Date) {
  const year = date.getUTCFullYear()
  const month = String(date.getUTCMonth() + 1).padStart(2, '0')
  const day = String(date.getUTCDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

onMounted(async () => {
  const plans = (await http.get('/plans')).data
  if (plans.length) {
    planId.value = plans[0].id
    generatedPlan.value = plans[0].plan_data
    generatedAt.value = plans[0].generated_at || new Date().toISOString()
    restDates.value = loadRestDates()
    showPlan.value = true
  }
  await loadTodayBurned()
})
</script>

<style scoped>
.training-panel {
  padding: 40px;
  width: 100%;
  box-sizing: border-box;
}

.burned-strip {
  display: flex;
  justify-content: flex-end;
  margin: 8px 0 12px;
  color: #16a34a;
}

.agent-strip {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 12px;
}

.question-card {
  margin-top: 28px;
  padding: 38px 52px;
  background: #4774c5;
}

.question-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(260px, 1fr));
  gap: 30px 68px;
}

:deep(.question-card .el-form-item__label),
:deep(.choice-block label) {
  color: #fff;
  font-weight: 700;
}

:deep(.el-input-number),
:deep(.el-select) {
  width: 100%;
}

:deep(.choice-list) {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

:deep(.choice-pill) {
  min-width: 96px;
  padding: 10px 16px;
  border: 1px solid #c7d2fe;
  background: #dbe7ff;
  color: #1f2937;
  cursor: pointer;
}

:deep(.choice-pill.active) {
  background: #67e8f9;
  border-color: #06b6d4;
  font-weight: 700;
}

.step-actions {
  display: flex;
  justify-content: flex-end;
  gap: 14px;
  margin-top: 24px;
}

.plan-calendar {
  width: 100%;
}

.calendar-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.calendar-head h2 {
  margin: 0 0 6px;
}

.calendar-head p {
  margin: 0;
  color: #6b7280;
}

.recommend-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 18px;
  padding: 16px 20px;
  border: 1px solid #bae6fd;
  border-radius: 18px;
  background: #eff6ff;
}

.recommend-card p {
  margin: 6px 0 0;
  color: #2563eb;
  font-weight: 700;
}

.calendar-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
  gap: 16px;
}

.calendar-day {
  min-height: 210px;
  padding: 18px;
  border: 1px solid #e5e7eb;
  border-radius: 18px;
  background: #f8fafc;
}

.calendar-day.today {
  border-color: #22c55e;
  background: #ecfdf5;
  box-shadow: 0 12px 24px rgba(34, 197, 94, 0.18);
}

.calendar-day.rest {
  border-color: #d1d5db;
  background: #f3f4f6;
  color: #6b7280;
}

.day-date {
  color: #2563eb;
  font-weight: 800;
}

.calendar-day h3 {
  margin: 10px 0;
}

.calendar-day ul {
  margin: 0;
  padding-left: 18px;
}

.calendar-day li {
  margin-bottom: 6px;
}

.rest-tag {
  margin-top: 12px;
  padding: 8px 10px;
  border-radius: 999px;
  background: #e5e7eb;
  text-align: center;
  font-weight: 700;
}

.day-actions {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-top: 16px;
}

.start-btn {
  height: 48px;
  flex: 1;
  border: 0;
  border-radius: 24px;
  font-size: 18px;
}

.plan-tools {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-bottom: 8px;
}

.training-detail {
  width: min(1280px, 100%);
  margin: 0 auto;
}

.training-detail.analyzing {
  width: min(1440px, 100%);
}

.training-detail h2 {
  margin: 0 0 8px;
}

.training-detail.analyzing h2 {
  margin-bottom: 4px;
  font-size: 20px;
}

.training-detail.analyzing .muted {
  margin: 0;
  font-size: 13px;
}

.movement-list {
  display: grid;
  gap: 14px;
  margin-top: 20px;
}

.movement-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 18px 20px;
  border-radius: 16px;
  background: #f8fafc;
}

.analysis-panel {
  width: 100%;
  margin-top: 14px;
}

.analysis-panel h3 {
  margin: 0 0 10px;
  font-size: 18px;
}

</style>
