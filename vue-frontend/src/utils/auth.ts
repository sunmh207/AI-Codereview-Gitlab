const TOKEN_KEY = 'auth_token'
const USER_KEY = 'auth_user'

// 简化的token管理，直接使用localStorage存储JWT token

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function removeToken(): void {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

export function setUser(user: any): void {
  localStorage.setItem(USER_KEY, JSON.stringify(user))
}

export function getUser(): any | null {
  const userStr = localStorage.getItem(USER_KEY)
  if (!userStr) return null

  try {
    return JSON.parse(userStr)
  } catch (error) {
    console.error('Parse user data error:', error)
    localStorage.removeItem(USER_KEY)
    return null
  }
}

export function isAuthenticated(): boolean {
  const token = getToken()
  const user = getUser()
  return !!(token && user)
}

export function getCurrentUser(): any | null {
  return getUser()
}
