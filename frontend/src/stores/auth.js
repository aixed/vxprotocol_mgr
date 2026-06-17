import { defineStore } from 'pinia'
import api from '@/utils/api'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    loggedIn: false,
    server: '',
    mgrPort: 29999,
    loading: false
  }),
  actions: {
    async fetchSession() {
      try {
        const { data } = await api.get('/session')
        this.loggedIn = !!data.logged_in
        this.server = data.server || ''
        this.mgrPort = data.mgr_port || 29999
      } catch (e) {
        this.loggedIn = false
      }
    },
    async login(payload) {
      this.loading = true
      try {
        const { data } = await api.post('/login', payload)
        this.loggedIn = true
        this.server = data.server
        this.mgrPort = data.mgr_port
        return data
      } finally {
        this.loading = false
      }
    },
    async logout() {
      try {
        await api.post('/logout')
      } catch (e) {
        /* ignore */
      }
      this.clear()
    },
    clear() {
      this.loggedIn = false
      this.server = ''
      this.mgrPort = 29999
    }
  }
})
