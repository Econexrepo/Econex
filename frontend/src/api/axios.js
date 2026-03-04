import axios from 'axios'

const api = axios.create({
  baseURL: 'http://localhost:8000',
  headers: { 'Content-Type': 'application/json' },
})

// Attach JWT token from localStorage to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('econex_token') || sessionStorage.getItem('econex_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// If 401, clear session and redirect to login
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('econex_token')
      localStorage.removeItem('econex_user')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export default api
