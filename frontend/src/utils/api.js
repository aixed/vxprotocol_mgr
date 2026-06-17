import axios from 'axios'
import router from '@/router'
import { useAuthStore } from '@/stores/auth'

const api = axios.create({
  baseURL: '/api',
  withCredentials: true,
  timeout: 30000
})

api.interceptors.response.use(
  (resp) => resp,
  (err) => {
    if (err.response && err.response.status === 401) {
      const auth = useAuthStore()
      auth.clear()
      if (router.currentRoute.value.name !== 'login') {
        router.replace({ name: 'login' })
      }
    }
    return Promise.reject(err)
  }
)

export default api
