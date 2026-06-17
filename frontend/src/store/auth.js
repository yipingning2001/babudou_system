import { reactive } from 'vue'

// 登录状态，全局共享。user = { id, username, display_name, role, store_id }
export const authState = reactive({
  token: null,
  user: null,
})

export function restoreAuth() {
  const token = localStorage.getItem('babadou_token')
  const userStr = localStorage.getItem('babadou_user')
  if (token && userStr) {
    authState.token = token
    authState.user = JSON.parse(userStr)
  }
}

export function setAuth(token, user) {
  authState.token = token
  authState.user = user
  localStorage.setItem('babadou_token', token)
  localStorage.setItem('babadou_user', JSON.stringify(user))
}

export function clearAuth() {
  authState.token = null
  authState.user = null
  localStorage.removeItem('babadou_token')
  localStorage.removeItem('babadou_user')
}

export function isAuthenticated() {
  return !!authState.token
}

export function isOwner() {
  return authState.user?.role === 'owner'
}
