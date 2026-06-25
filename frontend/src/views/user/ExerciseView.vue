<template>
  <section class="page exercise-page">
    <div class="panel exercise-panel">
      <h1 class="page-title">当天运动消耗</h1>

      <div class="chart-strip">
        <VChart class="calorie-chart" :option="chartOption" autoresize />
      </div>

      <el-form label-position="top" class="exercise-form">
        <el-form-item label="日期">
          <el-date-picker
            v-model="daily.exercise_date"
            type="date"
            value-format="YYYY-MM-DD"
            :disabled-date="disableFutureDate"
            placeholder="选择日期"
          />
          <p class="date-hint muted">可补录今天及以往日期，不能选择今天之后</p>
        </el-form-item>
        <el-form-item label="消耗热量(kcal)">
          <el-input-number v-model="daily.calories_burned" :min="0" />
        </el-form-item>
        <el-button type="success" @click="saveDaily">保存运动数据</el-button>
      </el-form>

      <el-divider />

      <div class="history-list">
        <div v-for="item in recentDailyList" :key="item.exercise_date" class="history-row">
          <span>{{ item.exercise_date }}：</span>
          <strong>{{ item.calories_burned }} kcal</strong>
          <el-button type="danger" link @click="deleteDaily(item.exercise_date)">删除</el-button>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { computed, onMounted, reactive, ref } from 'vue'
import VChart from 'vue-echarts'

import { http } from '../../api/http'
import { beijingTodayText, isAfterBeijingToday } from '../../utils/datetime'

use([LineChart, GridComponent, TooltipComponent, CanvasRenderer])

const daily = reactive({ exercise_date: beijingTodayText(), calories_burned: 300, exercise_records: {} })

function disableFutureDate(value: Date) {
  return isAfterBeijingToday(value)
}
const dailyList = ref<any[]>([])
const recentDailyList = computed(() => dailyList.value.slice(0, 5))

const chartOption = computed(() => {
  const rows = [...recentDailyList.value].reverse()
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 58, right: 20, top: 24, bottom: 28 },
    xAxis: { type: 'category', data: rows.map((item) => item.exercise_date) },
    yAxis: {
      type: 'value',
      name: 'kcal',
      min: 0,
      axisLabel: { show: true, formatter: (value: number) => String(value) }
    },
    series: [{ type: 'line', smooth: true, data: rows.map((item) => item.calories_burned), areaStyle: {} }]
  }
})

async function saveDaily() {
  if (daily.exercise_date > beijingTodayText()) {
    ElMessage.warning('不能选择今天之后的日期')
    return
  }
  await http.post('/sports/daily', daily)
  await loadDaily()
  ElMessage.success('运动数据已保存')
}

async function loadDaily() {
  dailyList.value = (await http.get('/sports/daily')).data
}

async function deleteDaily(exerciseDate: string) {
  await http.delete(`/sports/daily/${exerciseDate}`)
  await loadDaily()
  ElMessage.success('已删除')
}

onMounted(loadDaily)
</script>

<style scoped>
.exercise-page {
  overflow-y: auto;
}

.exercise-panel {
  width: 100%;
  margin: 0;
  padding: 22px 56px 28px;
  box-sizing: border-box;
}

.chart-strip {
  height: 160px;
  margin-bottom: 14px;
  border: 1px solid #e5e7eb;
  background: #f8fafc;
}

.calorie-chart {
  width: 100%;
  height: 100%;
}

.exercise-form {
  max-width: 360px;
}

.date-hint {
  margin: 6px 0 0;
  font-size: 12px;
  line-height: 1.45;
}

.history-list {
  font-size: 20px;
  line-height: 1.45;
  padding-bottom: 16px;
}

.history-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
