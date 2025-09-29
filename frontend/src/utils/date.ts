/**
 * 日期工具函数
 */

/**
 * 格式化日期
 * @param date 日期字符串或Date对象
 * @param format 格式化模板，默认 'YYYY-MM-DD HH:mm:ss'
 */
export function formatDate(date: string | Date, format = 'YYYY-MM-DD HH:mm:ss'): string {
  if (!date) return ''
  
  const d = typeof date === 'string' ? new Date(date) : date
  
  if (isNaN(d.getTime())) return ''
  
  const year = d.getFullYear()
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const hours = String(d.getHours()).padStart(2, '0')
  const minutes = String(d.getMinutes()).padStart(2, '0')
  const seconds = String(d.getSeconds()).padStart(2, '0')
  
  return format
    .replace('YYYY', String(year))
    .replace('MM', month)
    .replace('DD', day)
    .replace('HH', hours)
    .replace('mm', minutes)
    .replace('ss', seconds)
}

/**
 * 获取相对时间描述
 * @param date 日期字符串或Date对象
 */
export function getRelativeTime(date: string | Date): string {
  if (!date) return ''
  
  const d = typeof date === 'string' ? new Date(date) : date
  const now = new Date()
  const diff = now.getTime() - d.getTime()
  
  const minute = 60 * 1000
  const hour = 60 * minute
  const day = 24 * hour
  const week = 7 * day
  const month = 30 * day
  const year = 365 * day
  
  if (diff < minute) {
    return '刚刚'
  } else if (diff < hour) {
    return `${Math.floor(diff / minute)}分钟前`
  } else if (diff < day) {
    return `${Math.floor(diff / hour)}小时前`
  } else if (diff < week) {
    return `${Math.floor(diff / day)}天前`
  } else if (diff < month) {
    return `${Math.floor(diff / week)}周前`
  } else if (diff < year) {
    return `${Math.floor(diff / month)}个月前`
  } else {
    return `${Math.floor(diff / year)}年前`
  }
}

/**
 * 获取默认日期范围（最近7天）
 */
export function getDefaultDateRange(): [string, string] {
  const endDate = new Date()
  const startDate = new Date()
  startDate.setDate(startDate.getDate() - 7)
  
  return [
    formatDate(startDate, 'YYYY-MM-DD'),
    formatDate(endDate, 'YYYY-MM-DD')
  ]
}

/**
 * 获取日期范围选项
 */
export function getDateRangeOptions() {
  const today = new Date()
  const yesterday = new Date(today)
  yesterday.setDate(yesterday.getDate() - 1)
  
  const lastWeek = new Date(today)
  lastWeek.setDate(lastWeek.getDate() - 7)
  
  const lastMonth = new Date(today)
  lastMonth.setMonth(lastMonth.getMonth() - 1)
  
  const lastThreeMonths = new Date(today)
  lastThreeMonths.setMonth(lastThreeMonths.getMonth() - 3)
  
  return [
    {
      text: '今天',
      value: [formatDate(today, 'YYYY-MM-DD'), formatDate(today, 'YYYY-MM-DD')]
    },
    {
      text: '昨天',
      value: [formatDate(yesterday, 'YYYY-MM-DD'), formatDate(yesterday, 'YYYY-MM-DD')]
    },
    {
      text: '最近一周',
      value: [formatDate(lastWeek, 'YYYY-MM-DD'), formatDate(today, 'YYYY-MM-DD')]
    },
    {
      text: '最近一个月',
      value: [formatDate(lastMonth, 'YYYY-MM-DD'), formatDate(today, 'YYYY-MM-DD')]
    },
    {
      text: '最近三个月',
      value: [formatDate(lastThreeMonths, 'YYYY-MM-DD'), formatDate(today, 'YYYY-MM-DD')]
    }
  ]
}

/**
 * 判断是否为今天
 */
export function isToday(date: string | Date): boolean {
  if (!date) return false
  
  const d = typeof date === 'string' ? new Date(date) : date
  const today = new Date()
  
  return d.getFullYear() === today.getFullYear() &&
         d.getMonth() === today.getMonth() &&
         d.getDate() === today.getDate()
}

/**
 * 判断是否为本周
 */
export function isThisWeek(date: string | Date): boolean {
  if (!date) return false
  
  const d = typeof date === 'string' ? new Date(date) : date
  const today = new Date()
  const startOfWeek = new Date(today)
  startOfWeek.setDate(today.getDate() - today.getDay())
  startOfWeek.setHours(0, 0, 0, 0)
  
  const endOfWeek = new Date(startOfWeek)
  endOfWeek.setDate(startOfWeek.getDate() + 6)
  endOfWeek.setHours(23, 59, 59, 999)
  
  return d >= startOfWeek && d <= endOfWeek
}

/**
 * 获取时间戳
 */
export function getTimestamp(date?: string | Date): number {
  if (!date) return Date.now()
  
  const d = typeof date === 'string' ? new Date(date) : date
  return d.getTime()
}

/**
 * 解析ISO日期字符串
 */
export function parseISODate(dateString: string): Date | null {
  if (!dateString) return null
  
  try {
    const date = new Date(dateString)
    return isNaN(date.getTime()) ? null : date
  } catch {
    return null
  }
}