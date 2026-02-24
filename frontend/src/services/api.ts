import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

// Request interceptor - add auth token
api.interceptors.request.use((config) => {
  const storage = localStorage.getItem('fiscalspy-auth')
  if (storage) {
    const { state } = JSON.parse(storage)
    if (state?.accessToken) {
      config.headers.Authorization = `Bearer ${state.accessToken}`
    }
  }
  return config
})

// Response interceptor - handle 401/refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config

    if (error.response?.status === 401 && !original._retry) {
      original._retry = true
      try {
        const storage = localStorage.getItem('fiscalspy-auth')
        if (storage) {
          const { state } = JSON.parse(storage)
          if (state?.refreshToken) {
            const { data } = await axios.post('/api/auth/refresh', {
              refresh_token: state.refreshToken
            })
            // Update storage
            const parsed = JSON.parse(storage)
            parsed.state.accessToken = data.access_token
            parsed.state.refreshToken = data.refresh_token
            localStorage.setItem('fiscalspy-auth', JSON.stringify(parsed))
            original.headers.Authorization = `Bearer ${data.access_token}`
            return api(original)
          }
        }
      } catch {
        // Redirect to login
        localStorage.removeItem('fiscalspy-auth')
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export default api
