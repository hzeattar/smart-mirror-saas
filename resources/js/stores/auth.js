import { computed, reactive } from 'vue'
import api from '../lib/api'

const state = reactive({
  user: JSON.parse(localStorage.getItem('smart_mirror_user') || 'null'),
  loading: false,
})

export function useAuth() {
  const isAuthenticated = computed(() => Boolean(localStorage.getItem('smart_mirror_token')))

  async function login(email, password) {
    state.loading = true
    try {
      const { data } = await api.post('/auth/login', { email, password, device_name: 'Vue Admin Dashboard' })
      localStorage.setItem('smart_mirror_token', data.token)
      localStorage.setItem('smart_mirror_user', JSON.stringify(data.user))
      state.user = data.user
      return data.user
    } finally { state.loading = false }
  }

  async function refresh() {
    const { data } = await api.get('/auth/me')
    state.user = data.user
    localStorage.setItem('smart_mirror_user', JSON.stringify(data.user))
  }

  async function logout() {
    try { await api.post('/auth/logout') } catch (_) { /* local logout still proceeds */ }
    localStorage.removeItem('smart_mirror_token')
    localStorage.removeItem('smart_mirror_user')
    state.user = null
  }

  return { state, isAuthenticated, login, refresh, logout }
}
