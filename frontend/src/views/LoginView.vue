<script setup>
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const form = reactive({
  server: localStorage.getItem('login_server') || '',
  mgrPort: localStorage.getItem('login_mgr_port') || '29999',
  username: localStorage.getItem('login_username') || '',
  password: ''
})

const error = ref('')
const submitting = ref(false)

async function submit() {
  error.value = ''
  if (!form.server.trim()) {
    error.value = '请填写设备地址'
    return
  }
  if (!form.username || !form.password) {
    error.value = '请填写用户名和密码'
    return
  }
  submitting.value = true
  try {
    await auth.login({
      server: form.server.trim(),
      mgr_port: parseInt(form.mgrPort, 10) || 29999,
      username: form.username.trim(),
      password: form.password
    })
    localStorage.setItem('login_server', form.server.trim())
    localStorage.setItem('login_mgr_port', form.mgrPort)
    localStorage.setItem('login_username', form.username.trim())
    const redirect = route.query.redirect || '/shanghao'
    router.replace(redirect)
  } catch (e) {
    error.value = e?.response?.data?.error || e.message || '登录失败'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-brand">
        <div class="icon"><i class="bi bi-grid-fill" /></div>
        <h1>管理后台</h1>
        <p>请登录以继续操作</p>
      </div>

      <div v-if="error" class="alert alert-error" role="alert">
        <i class="bi bi-exclamation-circle-fill" />
        <span>{{ error }}</span>
      </div>

      <form @submit.prevent="submit">
        <div class="form-floating">
          <input
            v-model="form.server"
            type="text"
            class="form-control"
            placeholder="设备地址"
            required
            autofocus
          />
          <label><i class="bi bi-hdd-network me-1" />设备地址</label>
        </div>

        <div class="form-floating">
          <input
            v-model="form.mgrPort"
            type="number"
            min="1"
            max="65535"
            class="form-control"
            placeholder="端口"
            required
          />
          <label><i class="bi bi-router me-1" />端口</label>
        </div>

        <div class="form-floating">
          <input
            v-model="form.username"
            type="text"
            class="form-control"
            placeholder="用户名"
            required
          />
          <label><i class="bi bi-person me-1" />用户名</label>
        </div>

        <div class="form-floating">
          <input
            v-model="form.password"
            type="password"
            class="form-control"
            placeholder="密码"
            required
          />
          <label><i class="bi bi-lock me-1" />密码</label>
        </div>

        <button type="submit" class="btn btn-login" :disabled="submitting">
          <span v-if="submitting" class="spinner" />
          <span v-else>登 录</span>
        </button>
      </form>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.login-card {
  background: #fff;
  border-radius: 16px;
  padding: 48px 40px;
  width: 100%;
  max-width: 400px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
}

.login-brand {
  text-align: center;
  margin-bottom: 32px;
}

.login-brand .icon {
  width: 56px;
  height: 56px;
  border-radius: 14px;
  background: var(--primary);
  color: #fff;
  font-size: 26px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 14px;
}

.login-brand h1 {
  font-size: 22px;
  font-weight: 700;
  color: #1e293b;
  margin: 0;
}

.login-brand p {
  font-size: 13px;
  color: #94a3b8;
  margin: 6px 0 0;
}

.form-floating {
  margin-bottom: 16px;
  position: relative;
}

.form-floating .form-control {
  border-radius: 10px;
  border: 1.5px solid #e2e8f0;
  height: 52px;
  padding: 16px 14px 4px;
  font-size: 14px;
  width: 100%;
  transition: 0.15s;
  background: #fff;
}

.form-floating .form-control:focus {
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.12);
}

.form-floating label {
  position: absolute;
  top: 16px;
  left: 14px;
  font-size: 14px;
  color: #94a3b8;
  pointer-events: none;
  transition: 0.15s;
  display: flex;
  align-items: center;
}

.form-floating .form-control:focus + label,
.form-floating .form-control:not(:placeholder-shown) + label {
  top: 6px;
  font-size: 11px;
  color: var(--primary);
}

.btn-login {
  width: 100%;
  height: 48px;
  border-radius: 10px;
  font-weight: 600;
  font-size: 15px;
  background: var(--primary);
  border: none;
  color: #fff;
  transition: 0.2s;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-top: 8px;
}

.btn-login:hover:not(:disabled) {
  background: var(--primary-hover);
}

.btn-login:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}
</style>
