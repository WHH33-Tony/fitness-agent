export type MealPlanItem = {
  name: string
  grams: number
  calories: number
  protein: number
  fat: number
  carbs: number
}

export type MealPlanMeal = {
  title: string
  items: MealPlanItem[]
  totals: Record<string, number>
}

export type MealPlanDay = {
  day_label: string
  meals: MealPlanMeal[]
  day_totals: Record<string, number>
}

export type MealPlanTip = {
  label: string
  desc: string
}

export type MealPlan = {
  targets?: Record<string, number | string>
  days: MealPlanDay[]
  day_count?: number
  tips?: MealPlanTip[]
  note?: string
}

export type WeatherSnapshot = {
  city?: string
  region?: string
  observed_at?: string
  current?: Record<string, number | string | null>
  today?: Record<string, number | string | null>
  tomorrow?: Record<string, number | string | null>
  source?: string
}

export type WeatherTableRow = {
  period: string
  weather_desc: string
  temp: string
  extra: string
}

export function buildWeatherRows(weather: WeatherSnapshot | null): WeatherTableRow[] {
  if (!weather) return []
  const current = weather.current || {}
  const today = weather.today || {}
  const tomorrow = weather.tomorrow || {}
  const rows: WeatherTableRow[] = [
    {
      period: `实时（${weather.observed_at || '刚刚'}）`,
      weather_desc: String(current.weather_desc || '未知'),
      temp: `${current.temperature_c ?? '-'}°C / 体感 ${current.feels_like_c ?? '-'}°C`,
      extra: `湿度 ${current.humidity_pct ?? '-'}%，风速 ${current.wind_speed_kmh ?? '-'} km/h`
    }
  ]
  if (today.date) {
    rows.push({
      period: `今日 ${today.date}`,
      weather_desc: String(today.weather_desc || '未知'),
      temp: `最高 ${today.temp_max_c ?? '-'}°C / 最低 ${today.temp_min_c ?? '-'}°C`,
      extra: `降水概率 ${today.precipitation_probability_pct ?? 0}%`
    })
  }
  if (tomorrow.date) {
    rows.push({
      period: `明日 ${tomorrow.date}`,
      weather_desc: String(tomorrow.weather_desc || '未知'),
      temp: `最高 ${tomorrow.temp_max_c ?? '-'}°C / 最低 ${tomorrow.temp_min_c ?? '-'}°C`,
      extra: `降水概率 ${tomorrow.precipitation_probability_pct ?? 0}%`
    })
  }
  return rows
}

export type DayMealTableRow = {
  meal_title: string
  food_detail: string
  calories: number | string
  protein: number | string
  carbs: number | string
  fat: number | string
  row_type: 'meal' | 'total'
}

export type AnswerBlock =
  | { type: 'text'; text: string }
  | { type: 'heading'; text: string }
  | { type: 'list'; items: string[] }

const MEAL_PLAN_MARKER = '__MEAL_PLAN__'

function parseMealPlanFromLegacyText(text: string): MealPlan | null {
  const raw = String(text || '').replace(/__MEAL_PLAN__[\s\S]*/g, '').trim()
  if (!raw.includes('【早餐】') && !raw.includes('二、具体食谱')) {
    return null
  }

  const goalMatch = raw.match(/已按「(.+?)」目标/)
  const goal = goalMatch?.[1] || '维持'
  const calories = Number(raw.match(/热量约\s*([\d.]+)\s*kcal/)?.[1] || 0)
  const protein = Number(raw.match(/蛋白质约\s*([\d.]+)\s*g/)?.[1] || 0)
  const carbs = Number(raw.match(/碳水化合物约\s*([\d.]+)\s*g/)?.[1] || 0)
  const fat = Number(raw.match(/脂肪约\s*([\d.]+)\s*g/)?.[1] || 0)

  const dayChunks = raw.split(/(?=第\d+天)/).filter((chunk) => /第\d+天/.test(chunk))
  const days: MealPlanDay[] = []

  for (const chunk of dayChunks) {
    const dayLabel = chunk.match(/第\d+天/)?.[0] || '第1天'
    const meals: MealPlanMeal[] = []
    const mealTitles = ['早餐', '午餐', '晚餐', '加餐']

    for (const title of mealTitles) {
      const mealPattern = new RegExp(
        `【${title}】\\s*([\\s\\S]*?)(?=小计：|【|当日合计|第\\d+天|三、使用提示|$)`
      )
      const mealMatch = chunk.match(mealPattern)
      if (!mealMatch) continue

      const body = mealMatch[1]
      const items: MealPlanItem[] = []
      const itemPattern = /-\s*([^\s-]+)\s+([\d.]+)g/g
      let itemMatch: RegExpExecArray | null
      while ((itemMatch = itemPattern.exec(body)) !== null) {
        items.push({
          name: itemMatch[1],
          grams: Number(itemMatch[2]),
          calories: 0,
          protein: 0,
          fat: 0,
          carbs: 0
        })
      }

      const totalsPattern = new RegExp(
        `【${title}】[\\s\\S]*?小计：热量\\s*([\\d.]+)\\s*kcal，蛋白\\s*([\\d.]+)g，碳水\\s*([\\d.]+)g，脂肪\\s*([\\d.]+)g`
      )
      const totalsMatch = chunk.match(totalsPattern)
      const totals = {
        calories: Number(totalsMatch?.[1] || 0),
        protein: Number(totalsMatch?.[2] || 0),
        carbs: Number(totalsMatch?.[3] || 0),
        fat: Number(totalsMatch?.[4] || 0)
      }

      meals.push({ title, items, totals })
    }

    const dayTotalsMatch = chunk.match(
      /当日合计：热量\s*([\d.]+)\s*kcal，蛋白\s*([\d.]+)g，碳水\s*([\d.]+)g，脂肪\s*([\d.]+)g/
    )
    days.push({
      day_label: dayLabel,
      meals,
      day_totals: {
        calories: Number(dayTotalsMatch?.[1] || 0),
        protein: Number(dayTotalsMatch?.[2] || 0),
        carbs: Number(dayTotalsMatch?.[3] || 0),
        fat: Number(dayTotalsMatch?.[4] || 0)
      }
    })
  }

  if (!days.length) return null

  const tips: MealPlanTip[] = []
  const tipSection = raw.split('三、使用提示')[1]
  if (tipSection) {
    const tipLines = tipSection
      .split('-')
      .map((line) => line.trim())
      .filter((line) => line && !line.startsWith('安全提示'))
    if (tipLines[0]) {
      tips.push({ label: '食物互换', desc: tipLines[0].replace(/^同类食物可互换[，,]?\s*/, '同类食物可互换，') })
    }
    if (tipLines[1]) {
      tips.push({ label: '灵活调整', desc: tipLines[1] })
    }
  }
  if (!tips.length) {
    tips.push(
      { label: '食物互换', desc: '同类食物可互换，例如鸡胸肉可换牛肉或虾仁。' },
      { label: '灵活调整', desc: '想调整某一餐，可直接说“把午餐换成牛肉”或“蛋白再高一点”。' },
      {
        label: '安全提示',
        desc: '如出现不适请停止并咨询专业人士；有肾病等病史请遵医嘱调整蛋白摄入。'
      }
    )
  }

  return {
    targets: { goal, calories, protein_g: protein, carbs_g: carbs, fat_g: fat },
    days,
    day_count: days.length,
    tips,
    note: '当日合计为估算值，与参考目标可能存在小幅偏差，可据体重变化与训练强度微调。'
  }
}

export function extractMealPlanIntro(text: string): string {
  const raw = stripEmbeddedPayload(text)
  const introMatch = raw.match(/^[^一【\n]+?[。]/)
  const memoryMatch = raw.match(/(已结合你上一轮[^。\n]*。?)/)
  const parts: string[] = []
  if (introMatch?.[0]) parts.push(introMatch[0].trim())
  if (memoryMatch?.[0]) parts.push(memoryMatch[0].trim())
  if (parts.length) return parts.join('\n\n')
  const cutMarkers = ['一、每日营养参考', '二、具体食谱', '三、使用提示']
  let cut = raw.length
  for (const marker of cutMarkers) {
    const idx = raw.indexOf(marker)
    if (idx >= 0) cut = Math.min(cut, idx)
  }
  return raw.slice(0, cut).trim()
}

export function stripEmbeddedPayload(text: string): string {
  let value = String(text || '')
  const markerIdx = value.indexOf(MEAL_PLAN_MARKER)
  if (markerIdx >= 0) {
    value = value.slice(0, markerIdx)
  }
  return value.trim()
}

export function getDisplayAnswerText(text: string, hasStructuredPlan = false): string {
  const stripped = stripEmbeddedPayload(text)
  if (hasStructuredPlan) {
    return extractMealPlanIntro(stripped)
  }
  return stripped
}

export function parseWeatherFromAnswerText(text: string): WeatherSnapshot | null {
  const raw = stripEmbeddedPayload(text)
  if (!raw.includes('实时天气') && !raw.includes('今明预报')) {
    return null
  }

  const cityMatch = raw.match(/([\u4e00-\u9fa5]{2,8}(?:市|省)?)(?:（观测时间|：)/)
  const currentMatch = raw.match(
    /气温\s*([\d.]+)°C，\s*体感\s*([\d.]+)°C，\s*相对湿度\s*([\d.]+)%，\s*风速\s*([\d.]+)\s*km\/h/
  )
  const descMatch = raw.match(/：([^，,]+)[，,]\s*气温/)
  const todayMatch = raw.match(
    /今日（[^）]+））：([^，,]+)，\s*最高\s*([\d.]+)°C\s*\/\s*最低\s*([\d.]+)°C，\s*降水概率\s*([\d.]+)%/
  )
  const tomorrowMatch = raw.match(
    /明日（[^）]+））：([^，,]+)，\s*最高\s*([\d.]+)°C\s*\/\s*最低\s*([\d.]+)°C，\s*降水概率\s*([\d.]+)%/
  )
  const observedMatch = raw.match(/观测时间\s*([^）)]+)[）)]/)

  if (!currentMatch && !todayMatch) return null

  return {
    city: cityMatch?.[1]?.replace(/市$/, ''),
    region: '',
    observed_at: observedMatch?.[1]?.trim(),
    current: currentMatch
      ? {
          weather_desc: descMatch?.[1]?.trim() || '未知',
          temperature_c: Number(currentMatch[1]),
          feels_like_c: Number(currentMatch[2]),
          humidity_pct: Number(currentMatch[3]),
          wind_speed_kmh: Number(currentMatch[4])
        }
      : undefined,
    today: todayMatch
      ? {
          date: '今天',
          weather_desc: todayMatch[1],
          temp_max_c: Number(todayMatch[2]),
          temp_min_c: Number(todayMatch[3]),
          precipitation_probability_pct: Number(todayMatch[4])
        }
      : undefined,
    tomorrow: tomorrowMatch
      ? {
          date: '明天',
          weather_desc: tomorrowMatch[1],
          temp_max_c: Number(tomorrowMatch[2]),
          temp_min_c: Number(tomorrowMatch[3]),
          precipitation_probability_pct: Number(tomorrowMatch[4])
        }
      : undefined,
    source: 'Open-Meteo'
  }
}

export function parseMealPlanFromAnswer(text: string): { text: string; mealPlan: MealPlan | null } {
  const raw = String(text || '')
  const markerIdx = raw.indexOf(MEAL_PLAN_MARKER)
  if (markerIdx >= 0) {
    const visible = extractMealPlanIntro(raw.slice(0, markerIdx))
    const jsonPart = raw.slice(markerIdx + MEAL_PLAN_MARKER.length).trim()
    try {
      const plan = JSON.parse(jsonPart)
      if (plan?.days?.length) {
        return { text: visible, mealPlan: plan as MealPlan }
      }
    } catch {
      const legacy = parseMealPlanFromLegacyText(visible)
      if (legacy) return { text: visible, mealPlan: legacy }
      return { text: visible, mealPlan: null }
    }
  }

  const legacy = parseMealPlanFromLegacyText(raw)
  if (legacy) {
    return { text: extractMealPlanIntro(raw), mealPlan: legacy }
  }
  return { text: stripEmbeddedPayload(raw), mealPlan: null }
}

export function trimMealPlanDuplicateText(text: string): string {
  return extractMealPlanIntro(text)
}

export function buildDayMealRows(day: MealPlanDay): DayMealTableRow[] {
  const rows: DayMealTableRow[] = (day.meals || []).map((meal) => ({
    meal_title: meal.title,
    food_detail: (meal.items || []).map((item) => `${item.name} ${item.grams}g`).join('，'),
    calories: meal.totals?.calories ?? 0,
    protein: meal.totals?.protein ?? 0,
    carbs: meal.totals?.carbs ?? 0,
    fat: meal.totals?.fat ?? 0,
    row_type: 'meal'
  }))
  rows.push({
    meal_title: '当日合计',
    food_detail: '',
    calories: day.day_totals?.calories ?? 0,
    protein: day.day_totals?.protein ?? 0,
    carbs: day.day_totals?.carbs ?? 0,
    fat: day.day_totals?.fat ?? 0,
    row_type: 'total'
  })
  return rows
}

export function buildTargetRow(plan: MealPlan | null) {
  const targets = plan?.targets || {}
  if (!targets.calories) return []
  return [
    {
      calories: `${targets.calories} kcal`,
      protein: `${targets.protein_g} g`,
      carbs: `${targets.carbs_g} g`,
      fat: `${targets.fat_g} g`
    }
  ]
}

export function normalizeAnswerText(text: string): string {
  let value = String(text || '').trim()
  value = value.replace(/__MEAL_PLAN__[\s\S]*/g, '').trim()
  value = value.replace(/([一二三四五六七八九十]+、)/g, '\n$1')
  value = value.replace(/(【[^】]+】)/g, '\n$1\n')
  value = value.replace(/(第\d+天)/g, '\n\n$1\n')
  value = value.replace(/(小计：)/g, '\n$1')
  value = value.replace(/(当日合计：)/g, '\n$1')
  value = value.replace(/(\s-\s)/g, '\n- ')
  value = value.replace(/(- )/g, '\n$1')
  value = value.replace(/(已结合你上一轮|安全提示：)/g, '\n\n$1')

  if (!value.includes('\n') && value.length > 60) {
    value = value.replace(/([。；！？])(?=[^\s])/g, '$1\n')
  }
  if (value.split('\n').length < 3 && value.length > 80) {
    value = value.replace(/([。；！？])(?=[^\s])/g, '$1\n\n')
  }

  value = value.replace(/\n{3,}/g, '\n\n')
  return value.trim()
}

export function formatAnswerBlocks(text: string): AnswerBlock[] {
  const normalized = normalizeAnswerText(stripEmbeddedPayload(text))
  const lines = normalized.split('\n')
  const blocks: AnswerBlock[] = []
  let listItems: string[] = []

  const flushList = () => {
    if (listItems.length) {
      blocks.push({ type: 'list', items: [...listItems] })
      listItems = []
    }
  }

  for (const raw of lines) {
    const line = raw.trim()
    if (!line) {
      flushList()
      continue
    }
    if (/^([一二三四五六七八九十]+、|【.+】|第\d+天)/.test(line)) {
      flushList()
      blocks.push({ type: 'heading', text: line })
      continue
    }
    if (line.startsWith('- ')) {
      listItems.push(line.slice(2).trim())
      continue
    }
    flushList()
    blocks.push({ type: 'text', text: line })
  }

  flushList()
  return blocks.length ? blocks : [{ type: 'text', text: normalized || String(text || '') }]
}
