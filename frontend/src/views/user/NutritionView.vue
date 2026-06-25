<template>
  <section class="page nutrition-page">
    <div class="nutrition-panel">
      <h1 class="page-title">营养计算</h1>

      <el-card class="calc-card" shadow="never">
        <div class="calc-toolbar">
          <el-select
            v-model="activeCategory"
            placeholder="全部分类"
            clearable
            style="width: 160px"
            @change="onCategoryChange"
          >
            <el-option label="全部" value="" />
            <el-option v-for="c in categories" :key="c" :label="c" :value="c" />
          </el-select>
          <el-input v-model="foodName" placeholder="食物名称" clearable style="width: 200px" />
          <el-input-number v-model="grams" :min="1" :max="5000" controls-position="right" />
          <span class="unit">g</span>
          <el-button type="primary" :loading="loading" @click="calculate">计算</el-button>
        </div>
        <p v-if="result" class="result-inline">
          <strong>{{ result.food_name }}</strong>（{{ grams }}g）：
          热量 {{ result.calories_kcal.toFixed(1) }} kcal，
          蛋白 {{ result.protein_g.toFixed(1) }} g，
          脂肪 {{ result.fat_g.toFixed(1) }} g，
          碳水 {{ result.carbs_g.toFixed(1) }} g
        </p>
      </el-card>

      <el-card class="library-card" shadow="never">
        <template #header>
          <div class="library-header">
            <div>
              <span class="library-title">食物库</span>
              <span class="muted library-meta">
                {{ activeCategory || '全部' }} · 共 {{ displayCount }} 条 · 每页 {{ PAGE_SIZE }} 条
              </span>
            </div>
            <div class="library-actions">
              <span class="page-indicator">第 {{ currentPage }} / {{ totalPages }} 页</span>
              <el-button size="small" :loading="listLoading" @click="loadFoods">刷新</el-button>
            </div>
          </div>
        </template>

        <el-table
          v-loading="listLoading"
          :data="pagedFoods"
          stripe
          size="small"
          :max-height="tableMaxHeight"
          style="width: 100%"
          @row-click="pickFood"
        >
          <el-table-column prop="category" label="分类" width="100" />
          <el-table-column prop="name" label="名称" min-width="160" show-overflow-tooltip />
          <el-table-column prop="calories_per_100g" label="热量" width="90" align="right" />
          <el-table-column prop="protein" label="蛋白" width="80" align="right" />
          <el-table-column prop="fat" label="脂肪" width="80" align="right" />
          <el-table-column prop="carbs" label="碳水" width="80" align="right" />
        </el-table>

        <div v-if="filteredFoods.length" class="pagination-row">
          <el-pagination
            v-model:current-page="currentPage"
            :page-size="PAGE_SIZE"
            :total="filteredFoods.length"
            layout="total, prev, pager, next, jumper"
            background
            @current-change="scrollTableTop"
          />
        </div>
        <el-empty v-else-if="!listLoading" description="暂无匹配食物" :image-size="72" />
      </el-card>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { computed, onMounted, ref, watch } from 'vue'

import { http } from '../../api/http'

const PAGE_SIZE = 10
const tableMaxHeight = 15 * 40 + 48

const foodName = ref('')
const grams = ref(200)
const loading = ref(false)
const listLoading = ref(false)
const allFoods = ref<any[]>([])
const categories = ref<string[]>([])
const activeCategory = ref<string>('')
const currentPage = ref(1)

const isAllCategory = computed(() => !activeCategory.value)

const tableFoods = computed(() => {
  if (isAllCategory.value) return allFoods.value
  return allFoods.value.filter((f) => String(f?.category || '') === activeCategory.value)
})

const filteredFoods = computed(() => {
  const q = String(foodName.value || '').trim()
  if (!q) return tableFoods.value
  const lower = q.toLowerCase()
  return tableFoods.value.filter(
    (f) =>
      String(f?.name || '').toLowerCase().includes(lower) ||
      String(f?.name || '').includes(q)
  )
})

const displayCount = computed(() => tableFoods.value.length)

const totalPages = computed(() => Math.max(1, Math.ceil(filteredFoods.value.length / PAGE_SIZE)))

const pagedFoods = computed(() => {
  const start = (currentPage.value - 1) * PAGE_SIZE
  return filteredFoods.value.slice(start, start + PAGE_SIZE)
})

const matchedFood = computed(() => {
  const q = String(foodName.value || '').trim()
  if (!q) return null
  const lower = q.toLowerCase()
  return (
    allFoods.value.find((f) => String(f?.name || '').toLowerCase() === lower) ||
    allFoods.value.find((f) => String(f?.name || '').includes(q)) ||
    null
  )
})

const result = ref<null | {
  food_name: string
  calories_kcal: number
  protein_g: number
  fat_g: number
  carbs_g: number
}>(null)

function scrollTableTop() {
  const el = document.querySelector('.library-card .el-table__body-wrapper')
  if (el) el.scrollTop = 0
}

async function loadFoods() {
  listLoading.value = true
  try {
    const { data } = await http.get('/sports/nutrition')
    allFoods.value = Array.isArray(data) ? data : []
  } catch (e: any) {
    allFoods.value = []
    ElMessage.warning(`加载食物库失败：${e?.message || '未知错误'}`)
  } finally {
    listLoading.value = false
  }
}

async function loadCategories() {
  try {
    const { data } = await http.get('/sports/nutrition/categories')
    categories.value = Array.isArray(data) ? data : []
  } catch (_) {
    categories.value = []
  }
}

function onCategoryChange() {
  currentPage.value = 1
  result.value = null
}

watch(totalPages, (pages) => {
  if (currentPage.value > pages) currentPage.value = pages
})

watch(foodName, () => {
  currentPage.value = 1
})

async function calculate() {
  loading.value = true
  try {
    if (!allFoods.value.length) await loadFoods()
    const food = matchedFood.value
    if (!food) {
      result.value = null
      ElMessage.warning('未找到匹配食物，请调整名称或在下方表格中选择。')
      return
    }
    const g = Number(grams.value ?? 0)
    if (!Number.isFinite(g) || g <= 0) {
      ElMessage.warning('克数必须大于 0')
      return
    }
    const ratio = g / 100
    result.value = {
      food_name: String(food.name || ''),
      calories_kcal: Number(food.calories_per_100g ?? 0) * ratio,
      protein_g: Number(food.protein ?? 0) * ratio,
      fat_g: Number(food.fat ?? 0) * ratio,
      carbs_g: Number(food.carbs ?? 0) * ratio
    }
  } finally {
    loading.value = false
  }
}

async function pickFood(row: any) {
  if (!row?.name) return
  foodName.value = String(row.name)
  await calculate()
}

onMounted(async () => {
  await Promise.all([loadFoods(), loadCategories()])
})
</script>

<style scoped>
.nutrition-page {
  overflow-y: auto;
  padding-bottom: 20px;
}

.nutrition-panel {
  width: 100%;
  margin: 0;
  padding: 18px 40px 24px;
  box-sizing: border-box;
}

.muted {
  color: rgba(100, 116, 139, 0.95);
}

.calc-card {
  margin-top: 12px;
  border-radius: 12px;
}

.calc-card :deep(.el-card__body) {
  padding: 14px 16px;
}

.calc-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.unit {
  color: rgba(100, 116, 139, 0.95);
  font-weight: 600;
}

.result-inline {
  margin: 12px 0 0;
  padding: 10px 12px;
  border-radius: 8px;
  background: #f0f9ff;
  border: 1px solid #bae6fd;
  color: #0f172a;
  font-size: 13px;
  line-height: 1.5;
}

.library-card {
  margin-top: 14px;
  border-radius: 12px;
}

.library-card :deep(.el-card__header) {
  padding: 12px 16px;
}

.library-card :deep(.el-card__body) {
  padding: 0 16px 16px;
}

.library-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.library-title {
  font-weight: 700;
  margin-right: 10px;
}

.library-meta {
  font-size: 13px;
}

.library-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.page-indicator {
  font-size: 13px;
  color: #475569;
  font-weight: 600;
}

.pagination-row {
  display: flex;
  justify-content: center;
  margin-top: 14px;
  padding-top: 4px;
}
</style>
