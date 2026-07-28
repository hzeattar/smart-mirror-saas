import axios from 'axios'

const api = axios.create({ baseURL: '/api', headers: { Accept: 'application/json' } })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('smart_mirror_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && !location.pathname.startsWith('/checkout')) {
      localStorage.removeItem('smart_mirror_token')
      localStorage.removeItem('smart_mirror_user')
      if (location.pathname !== '/login') location.href = '/login'
    }
    return Promise.reject(error)
  },
)

export function errorMessage(error) {
  const errors = error.response?.data?.errors
  if (errors) return Object.values(errors).flat().join(' ')
  return error.response?.data?.message || error.message || 'Request failed.'
}

export default api
