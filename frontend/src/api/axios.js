import axios from "axios"

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:8000",
  timeout: 10000,
  headers: {
    "Content-Type": "application/json"
  }
})

/* ─────────────────────────────────────────
   Attach JWT token to every request
───────────────────────────────────────── */
api.interceptors.request.use(
  (config) => {
    const token =
      localStorage.getItem("econex_token") ||
      sessionStorage.getItem("econex_token")

    if (token) {
      config.headers = config.headers || {}
      config.headers.Authorization = `Bearer ${token}`
    }

    return config
  },
  (error) => Promise.reject(error)
)

/* ─────────────────────────────────────────
   Handle unauthorized responses
───────────────────────────────────────── */
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const url = error.config?.url || ""
    const isAuthRequest = url.includes("/auth/login") || url.includes("/auth/register")

    if (error.response?.status === 401 && !isAuthRequest) {
      // Expired/invalid session — clear tokens and redirect
      localStorage.removeItem("econex_token")
      localStorage.removeItem("econex_user")
      sessionStorage.removeItem("econex_token")
      window.location.replace("/login")
    }

    return Promise.reject(error)
  }
)

export default api