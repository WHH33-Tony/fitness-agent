const BEIJING_TZ = 'Asia/Shanghai'

/** 北京时间当天，格式 YYYY-MM-DD */
export function beijingTodayText(): string {
  return new Intl.DateTimeFormat('en-CA', { timeZone: BEIJING_TZ }).format(new Date())
}

/** 将 Date 格式化为北京时间 YYYY-MM-DD */
export function formatBeijingDateText(value: Date): string {
  return new Intl.DateTimeFormat('en-CA', { timeZone: BEIJING_TZ }).format(value)
}

/** 是否晚于北京时间当天（用于禁用未来日期） */
export function isAfterBeijingToday(value: Date): boolean {
  return formatBeijingDateText(value) > beijingTodayText()
}

/** 后端 SQLite 存 UTC，API 常返回无时区的 ISO 字符串，需按 UTC 解析 */
export function parseApiDateTime(value: string | number | Date | null | undefined): Date | null {
  if (value == null || value === '') return null
  if (value instanceof Date) return Number.isNaN(value.getTime()) ? null : value

  const raw = String(value).trim()
  if (!raw) return null

  const hasTz = /[zZ]$|[+-]\d{2}:\d{2}$/.test(raw)
  const date = new Date(hasTz ? raw : `${raw}Z`)
  return Number.isNaN(date.getTime()) ? null : date
}

/** 格式化为北京时间 YYYY-MM-DD HH:mm */
export function formatBeijingDateTime(value: string | number | Date | null | undefined): string {
  const date = parseApiDateTime(value)
  if (!date) return value != null && value !== '' ? String(value) : ''

  const parts = new Intl.DateTimeFormat('zh-CN', {
    timeZone: BEIJING_TZ,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  }).formatToParts(date)

  const get = (type: Intl.DateTimeFormatPartTypes) =>
    parts.find((part) => part.type === type)?.value || ''

  return `${get('year')}-${get('month')}-${get('day')} ${get('hour')}:${get('minute')}`
}
