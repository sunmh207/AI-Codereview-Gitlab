import { formatDate } from './date'
import type { ReviewData } from '@/api/reviews'

export const formatDelta = (additions: number | undefined, deletions: number | undefined): string => {
  if (additions !== undefined && deletions !== undefined && !isNaN(additions) && !isNaN(deletions)) {
    return `+${additions}  -${deletions}`
  }
  return ''
}

export const formatScore = (score: number): string => {
  return score?.toFixed(2) || '0.00'
}

export const formatTableData = (data: ReviewData[]): any[] => {
  return data.map(item => ({
    ...item,
    updated_at: formatDate(item.updated_at),
    delta: formatDelta(item.additions, item.deletions),
    score_formatted: formatScore(item.score)
  }))
}

export const truncateText = (text: string, maxLength: number = 50): string => {
  if (text.length <= maxLength) return text
  return text.substring(0, maxLength) + '...'
}

export const getScoreColor = (score: number): string => {
  if (score >= 80) return '#67C23A' // Green
  if (score >= 60) return '#E6A23C' // Orange
  return '#F56C6C' // Red
}