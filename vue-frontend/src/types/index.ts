export interface User {
  username: string
}

export interface LoginForm {
  username: string
  password: string
  remember: boolean
}

export interface MergeRequestLog {
  project_name: string
  author: string
  source_branch: string
  target_branch: string
  updated_at: string
  commit_messages: string
  delta: string
  score: number
  url: string
  additions: number
  deletions: number
}

export interface PushLog {
  project_name: string
  author: string
  branch: string
  updated_at: string
  commit_messages: string
  delta: string
  score: number
  commits_json?: string
  additions: number
  deletions: number
}

export interface Commit {
  id: string
  message: string
  author: string
  timestamp: string
  url?: string
}

export interface FilterParams {
  startDate: string
  endDate: string
  authors: string[]
  projectNames: string[]
  page?: number
  page_size?: number
}

export interface PaginationResponse<T> {
  success: boolean
  data: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
  message?: string
}

export interface ChartData {
  name: string
  value: number
}

export interface ApiResponse<T> {
  data: T
  message?: string
  success: boolean
}

export interface Developer {
  name: string
  gitlab_username: string
  group?: string
}

export interface UsersWithoutReviewData {
  users_without_review: Developer[]
  total_developers: number
  total_unreviewed_users: number
  review_coverage_rate: number
  time_range: string
}

export interface TimeRangeOption {
  label: string
  value: string
}
