import { apiClient } from './client'

export interface ReviewData {
  id: number
  project_name: string
  author: string
  updated_at: string
  commit_messages: string
  score: number
  url?: string
  source_branch?: string
  target_branch?: string
  branch?: string
  additions?: number
  deletions?: number
  review_result?: string
  title?: string
}

export interface ProjectStatistics {
  project_name: string
  count?: number
  average_score?: number
}

export interface AuthorStatistics {
  author: string
  count?: number
  average_score?: number
  additions?: number
  deletions?: number
}

export interface ReviewFilters {
  start_date?: string
  end_date?: string
  authors?: string[]
  project_names?: string[]
}

export interface ApiResponse<T> {
  data: T[]
  total: number
}

export interface StatisticsResponse {
  project_counts: ProjectStatistics[]
  project_scores: ProjectStatistics[]
}

export interface AuthorStatisticsResponse {
  author_counts: AuthorStatistics[]
  author_scores: AuthorStatistics[]
  author_code_lines: AuthorStatistics[]
}

export interface MetadataResponse {
  authors: string[]
  project_names: string[]
  push_review_enabled: boolean
}

// Get MR reviews
export const getMRReviews = async (filters: ReviewFilters): Promise<ApiResponse<ReviewData>> => {
  const params = new URLSearchParams()

  if (filters.start_date) params.append('start_date', filters.start_date)
  if (filters.end_date) params.append('end_date', filters.end_date)
  if (filters.authors) {
    filters.authors.forEach(author => params.append('authors', author))
  }
  if (filters.project_names) {
    filters.project_names.forEach(project => params.append('project_names', project))
  }

  const response = await apiClient.get(`/api/reviews/mr?${params}`)
  return response.data
}

// Get push reviews
export const getPushReviews = async (filters: ReviewFilters): Promise<ApiResponse<ReviewData>> => {
  const params = new URLSearchParams()

  if (filters.start_date) params.append('start_date', filters.start_date)
  if (filters.end_date) params.append('end_date', filters.end_date)
  if (filters.authors) {
    filters.authors.forEach(author => params.append('authors', author))
  }
  if (filters.project_names) {
    filters.project_names.forEach(project => params.append('project_names', project))
  }

  const response = await apiClient.get(`/api/reviews/push?${params}`)
  return response.data
}

// Get project statistics
export const getProjectStatistics = async (
  filters: ReviewFilters & { type?: 'mr' | 'push' }
): Promise<StatisticsResponse> => {
  const params = new URLSearchParams()

  if (filters.start_date) params.append('start_date', filters.start_date)
  if (filters.end_date) params.append('end_date', filters.end_date)
  if (filters.type) params.append('type', filters.type)

  const response = await apiClient.get(`/api/statistics/projects?${params}`)
  return response.data
}

// Get author statistics
export const getAuthorStatistics = async (
  filters: ReviewFilters & { type?: 'mr' | 'push' }
): Promise<AuthorStatisticsResponse> => {
  const params = new URLSearchParams()

  if (filters.start_date) params.append('start_date', filters.start_date)
  if (filters.end_date) params.append('end_date', filters.end_date)
  if (filters.type) params.append('type', filters.type)

  const response = await apiClient.get(`/api/statistics/authors?${params}`)
  return response.data
}

// Get specific statistics by type
export const getStatistics = async (
  statType: 'project_counts' | 'project_scores' | 'author_counts' | 'author_scores' | 'author_code_lines',
  filters?: ReviewFilters & { type?: 'mr' | 'push' }
): Promise<{ data: any[] }> => {
  const params = new URLSearchParams()

  if (filters?.start_date) params.append('start_date', filters.start_date)
  if (filters?.end_date) params.append('end_date', filters.end_date)
  if (filters?.type) params.append('type', filters.type)

  const url = `/api/statistics/${statType}?${params}`
  const response = await apiClient.get(url)
  return response.data
}

// Get metadata for filters
export const getMetadata = async (
  filters: { start_date?: string; end_date?: string; type?: 'mr' | 'push' }
): Promise<MetadataResponse> => {
  const params = new URLSearchParams()

  if (filters.start_date) params.append('start_date', filters.start_date)
  if (filters.end_date) params.append('end_date', filters.end_date)
  if (filters.type) params.append('type', filters.type)

  const response = await apiClient.get(`/api/metadata?${params}`)
  return response.data
}