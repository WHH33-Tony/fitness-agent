<template>
  <div class="answer-text">
    <template v-for="(block, idx) in blocks" :key="`b-${idx}`">
      <p v-if="block.type === 'text'" class="answer-line">{{ block.text }}</p>
      <h4 v-else-if="block.type === 'heading'" class="answer-heading">{{ block.text }}</h4>
      <ul v-else-if="block.type === 'list'" class="answer-list">
        <li v-for="(item, itemIdx) in block.items" :key="`l-${idx}-${itemIdx}`">{{ item }}</li>
      </ul>
    </template>

    <div v-if="weatherRows.length" class="weather-panel">
      <h4 class="answer-heading">{{ weatherTitle }}</h4>
      <el-table :data="weatherRows" size="small" border stripe class="weather-table">
        <el-table-column prop="period" label="时段" width="170" />
        <el-table-column prop="weather_desc" label="天气" width="100" align="center" />
        <el-table-column prop="temp" label="气温" min-width="180" />
        <el-table-column prop="extra" label="补充信息" min-width="220" />
      </el-table>
    </div>

    <div v-if="resolvedPlan" class="meal-plan-panel">
      <h4 class="answer-heading">一、每日营养参考目标</h4>
      <el-table v-if="targetRows.length" :data="targetRows" size="small" border class="meal-target-table">
        <el-table-column prop="calories" label="热量" align="center" />
        <el-table-column prop="protein" label="蛋白质" align="center" />
        <el-table-column prop="carbs" label="碳水化合物" align="center" />
        <el-table-column prop="fat" label="脂肪" align="center" />
      </el-table>

      <div v-for="section in daySections" :key="section.day.day_label" class="meal-day-block">
        <h4 class="answer-heading">{{ section.title }}</h4>
        <el-table
          :data="section.rows"
          size="small"
          border
          stripe
          class="meal-table"
          :row-class-name="mealRowClass"
        >
          <el-table-column prop="meal_title" label="餐次" width="88" align="center" />
          <el-table-column prop="food_detail" label="食物明细" min-width="220" />
          <el-table-column prop="calories" label="热量" width="88" align="right" />
          <el-table-column prop="protein" label="蛋白质" width="88" align="right" />
          <el-table-column prop="carbs" label="碳水" width="80" align="right" />
          <el-table-column prop="fat" label="脂肪" width="80" align="right" />
        </el-table>
      </div>

      <template v-if="tipRows.length">
        <h4 class="answer-heading">{{ tipsTitle }}</h4>
        <el-table :data="tipRows" size="small" border class="meal-tip-table">
          <el-table-column prop="label" label="提示项" width="120" />
          <el-table-column prop="desc" label="说明" min-width="260" />
        </el-table>
      </template>
      <p v-if="planNote" class="meal-note">{{ planNote }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

import {
  buildDayMealRows,
  buildTargetRow,
  buildWeatherRows,
  formatAnswerBlocks,
  getDisplayAnswerText,
  parseMealPlanFromAnswer,
  parseWeatherFromAnswerText,
  type MealPlan,
  type WeatherSnapshot
} from '../utils/qaAnswer'

const props = defineProps<{
  text?: string
  mealPlan?: MealPlan | null
  weather?: WeatherSnapshot | null
}>()

const parsed = computed(() => parseMealPlanFromAnswer(props.text || ''))
const resolvedPlan = computed(() => props.mealPlan || parsed.value.mealPlan)
const displayText = computed(() => getDisplayAnswerText(props.text || '', !!resolvedPlan.value))
const blocks = computed(() => formatAnswerBlocks(displayText.value))

const targetRows = computed(() => buildTargetRow(resolvedPlan.value))
const daySections = computed(() =>
  (resolvedPlan.value?.days || []).map((day, index) => ({
    day,
    title:
      (resolvedPlan.value?.day_count || resolvedPlan.value?.days?.length || 0) > 1
        ? `${['二', '三', '四', '五', '六'][index] || index + 2}、${day.day_label}食谱`
        : '二、今日食谱',
    rows: buildDayMealRows(day)
  }))
)
const tipRows = computed(() => resolvedPlan.value?.tips || [])
const planNote = computed(() => resolvedPlan.value?.note || '')
const tipsTitle = computed(() => {
  const nums = ['一', '二', '三', '四', '五', '六', '七']
  return `${nums[daySections.value.length + 1] || daySections.value.length + 2}、使用提示`
})

const resolvedWeather = computed(() => props.weather || parseWeatherFromAnswerText(props.text || ''))
const weatherRows = computed(() => buildWeatherRows(resolvedWeather.value))
const weatherTitle = computed(() => {
  const w = resolvedWeather.value
  if (!w) return '天气实况'
  const place = w.region ? `${w.region}${w.city}` : w.city
  return place ? `${place} 天气实况` : '天气实况'
})

function mealRowClass({ row }: { row: { row_type?: string } }) {
  return row.row_type === 'total' ? 'meal-total-row' : ''
}
</script>

<style scoped>
.answer-text {
  line-height: 1.8;
  word-break: break-word;
}

.answer-line,
.answer-heading,
.answer-list {
  margin: 0 0 10px;
}

.answer-heading {
  margin-top: 14px;
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
}

.answer-list {
  padding-left: 22px;
}

.weather-panel,
.meal-plan-panel {
  margin-top: 18px;
}

.meal-day-block + .meal-day-block {
  margin-top: 22px;
  padding-top: 18px;
  border-top: 1px solid rgba(148, 163, 184, 0.22);
}

.meal-target-table,
.meal-table,
.weather-table,
.meal-tip-table {
  width: 100%;
}

.meal-note {
  margin: 12px 0 0;
  color: #64748b;
  font-size: 12px;
  line-height: 1.6;
}

:deep(.meal-total-row) {
  font-weight: 700;
  background: rgba(37, 99, 235, 0.06) !important;
}
</style>
