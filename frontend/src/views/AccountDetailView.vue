<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '@/utils/api'

const props = defineProps({
  port: { type: [String, Number], required: true }
})
const route = useRoute()
const router = useRouter()

const port = ref(parseInt(String(props.port ?? route.params.port), 10))
const loading = ref(false)
const refreshing = ref(false)
const lastError = ref('')
const sessions = ref([])
// session_id -> { loading, profile, error, state }
const profileState = ref({})

// Reuse the key set on the Accounts page (same localStorage namespace)
const apiKey = ref(localStorage.getItem('accounts_api_key') || '')

let pollTimer = null

async function fetchSessionList() {
  const r = await api.post('/get_session_list', {
    port: port.value,
    key: apiKey.value,
    not_started_after_seconds:
      parseInt(localStorage.getItem('accounts_not_started_after') || '300', 10)
  })
  return r.data || {}
}

async function fetchProfile(sessionId) {
  const r = await api.post('/get_profile', {
    port: port.value,
    session_id: sessionId
  })
  return r.data || {}
}

async function loadAll({ silent = false } = {}) {
  if (silent) refreshing.value = true
  else loading.value = true
  lastError.value = ''
  try {
    const data = await fetchSessionList()
    const list = Array.isArray(data.sessions) ? data.sessions : []
    sessions.value = list
    // Initialize profile state for any new sessions, keep previous profiles when possible
    const next = {}
    list.forEach((s) => {
      const sid = s.session_id
      const prev = profileState.value[sid]
      next[sid] = prev
        ? { ...prev, state: s.state, online: s.online, updated_at: s.updated_at }
        : { loading: true, profile: null, error: '', state: s.state, online: s.online, updated_at: s.updated_at }
      next[sid].loading = !next[sid].profile
    })
    profileState.value = next

    // Fetch profile for sessions that don't have one yet
    const needFetch = list.filter((s) => !profileState.value[s.session_id]?.profile)
    await Promise.all(
      needFetch.map(async (s) => {
        const sid = s.session_id
        try {
          const data = await fetchProfile(sid)
          if (data.ok && data.profile) {
            profileState.value[sid] = {
              ...profileState.value[sid],
              loading: false,
              profile: data.profile,
              error: ''
            }
          } else {
            profileState.value[sid] = {
              ...profileState.value[sid],
              loading: false,
              error: data.error || '未返回 profile'
            }
          }
        } catch (e) {
          profileState.value[sid] = {
            ...profileState.value[sid],
            loading: false,
            error: e?.response?.data?.error || e.message || '获取 profile 失败'
          }
        }
      })
    )
  } catch (e) {
    lastError.value = e?.response?.data?.error || e.message || '加载失败'
  } finally {
    loading.value = false
    refreshing.value = false
  }
}

function refreshOne(sid) {
  profileState.value[sid] = {
    ...profileState.value[sid],
    loading: true,
    error: ''
  }
  fetchProfile(sid)
    .then((data) => {
      if (data.ok && data.profile) {
        profileState.value[sid] = {
          ...profileState.value[sid],
          loading: false,
          profile: data.profile,
          error: ''
        }
      } else {
        profileState.value[sid] = {
          ...profileState.value[sid],
          loading: false,
          error: data.error || '未返回 profile'
        }
      }
    })
    .catch((e) => {
      profileState.value[sid] = {
        ...profileState.value[sid],
        loading: false,
        error: e?.response?.data?.error || e.message || '获取 profile 失败'
      }
    })
}

function goBack() {
  if (window.history.length > 1) router.back()
  else router.push({ name: 'accounts' })
}

function sexLabel(sex) {
  if (sex === 1) return '男'
  if (sex === 2) return '女'
  return '-'
}

function fmtTime(t) {
  if (!t) return '-'
  // Trim fractional seconds for readability
  return String(t).replace(/(\.\d+)(?=[+-Z])/g, '')
}

onMounted(() => {
  loadAll()
  pollTimer = setInterval(() => loadAll({ silent: true }), 15000)
})

onBeforeUnmount(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<template>
  <div>
    <div class="page-header">
      <div class="d-flex align-items-center">
        <button class="btn btn-sm btn-outline-secondary me-3" @click="goBack">
          <i class="bi bi-arrow-left" />
        </button>
        <h2>
          <i class="bi bi-hdd-network" style="color: var(--primary)" />
          协议 {{ port }} · 账号详情
        </h2>
      </div>
      <button
        class="btn btn-sm btn-outline-primary refresh-btn"
        :disabled="loading || refreshing"
        @click="loadAll()"
      >
        <i class="bi bi-arrow-clockwise" :class="{ 'spin-icon': refreshing }" />
        <span class="ms-1">{{ refreshing ? '刷新中' : '刷新' }}</span>
      </button>
    </div>

    <div v-if="!apiKey" class="alert alert-warning">
      <i class="bi bi-key me-2" />
      尚未配置上游 API key。
      <RouterLink to="/accounts">回到账号管理</RouterLink>
      配置后再进入详情。
    </div>

    <div v-if="loading && sessions.length === 0" class="card">
      <div class="card-body text-center text-muted" style="padding: 40px">
        <i class="bi bi-hourglass-split" /> 正在加载 sessions ...
      </div>
    </div>

    <div v-else-if="lastError" class="alert alert-danger">
      <i class="bi bi-exclamation-triangle me-2" />{{ lastError }}
    </div>

    <div v-else-if="sessions.length === 0" class="card">
      <div class="card-body text-center text-muted" style="padding: 40px">
        <i class="bi bi-inbox" style="font-size: 32px" />
        <div class="mt-2">该协议上没有 session</div>
      </div>
    </div>

    <div v-else class="row g-4 account-grid">
      <div
        v-for="s in sessions"
        :key="s.session_id"
        class="col-lg-6"
      >
        <div class="account-card">
          <div class="account-head">
            <div class="d-flex align-items-center">
              <div class="avatar-box">
                <i v-if="(profileState[s.session_id] || {}).loading" class="bi bi-hourglass-split" />
                <i v-else-if="s.online" class="bi bi-person-fill-check" />
                <i v-else class="bi bi-person-fill" />
              </div>
              <div class="ms-3">
                <div class="account-nick">
                  {{ (profileState[s.session_id] || {}).profile?.nick_name || s.rdv || '加载中...' }}
                </div>
                <div class="account-state">
                  <i
                    class="bi"
                    :class="s.online ? 'bi-circle-fill text-success' : 'bi-circle text-secondary'"
                  />
                  <span class="ms-1">{{ s.state }}</span>
                </div>
              </div>
            </div>
            <button
              class="btn btn-sm btn-light"
              :disabled="(profileState[s.session_id] || {}).loading"
              title="刷新该账号"
              @click="refreshOne(s.session_id)"
            >
              <i class="bi bi-arrow-clockwise" />
            </button>
          </div>

          <div v-if="(profileState[s.session_id] || {}).loading" class="loading-tip">
            <i class="bi bi-hourglass-split" /> 正在拉取 profile ...
          </div>

          <div v-else-if="(profileState[s.session_id] || {}).error" class="alert-error">
            <i class="bi bi-exclamation-triangle me-1" />
            {{ (profileState[s.session_id] || {}).error }}
          </div>

          <div v-else-if="(profileState[s.session_id] || {}).profile" class="profile-body">
            <div class="profile-avatar-row">
              <img
                v-if="(profileState[s.session_id] || {}).profile?.big_head_url"
                :src="(profileState[s.session_id] || {}).profile.big_head_url"
                alt="avatar"
                class="big-avatar"
                @error="(e) => (e.target.style.display = 'none')"
              />
              <div class="profile-grid">
                <div class="profile-field">
                  <span class="field-label">wxid (user_name)</span>
                  <span class="field-value mono">{{ (profileState[s.session_id] || {}).profile.user_name || '-' }}</span>
                </div>
                <div class="profile-field">
                  <span class="field-label">昵称</span>
                  <span class="field-value">{{ (profileState[s.session_id] || {}).profile.nick_name || '-' }}</span>
                </div>
                <div class="profile-field">
                  <span class="field-label">微信号 (alias)</span>
                  <span class="field-value mono">{{ (profileState[s.session_id] || {}).profile.alias || '-' }}</span>
                </div>
                <div class="profile-field">
                  <span class="field-label">手机号</span>
                  <span class="field-value mono">{{ (profileState[s.session_id] || {}).profile.phone || '-' }}</span>
                </div>
                <div class="profile-field">
                  <span class="field-label">性别</span>
                  <span class="field-value">{{ sexLabel((profileState[s.session_id] || {}).profile.sex) }}</span>
                </div>
                <div class="profile-field">
                  <span class="field-label">国家</span>
                  <span class="field-value">{{ (profileState[s.session_id] || {}).profile.country || '-' }}</span>
                </div>
              </div>
            </div>

            <details class="raw-details">
              <summary>查看原始 JSON</summary>
              <pre class="mono">{{ JSON.stringify((profileState[s.session_id] || {}).profile, null, 2) }}</pre>
            </details>
          </div>

          <div class="session-meta">
            <span><strong>session_id:</strong> <span class="mono">{{ s.session_id }}</span></span>
            <span><strong>rdv:</strong> <span class="mono">{{ s.rdv }}</span></span>
            <span><strong>start_port:</strong> {{ s.start_port }}</span>
            <span><strong>login:</strong> {{ s.login_started ? '是' : '否' }}</span>
            <span><strong>更新:</strong> {{ fmtTime(s.updated_at) }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
}
.refresh-btn {
  display: inline-flex;
  align-items: center;
}
.spin-icon {
  animation: spin 1s linear infinite;
}
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.account-grid {
  display: flex;
  flex-wrap: wrap;
  margin: 0 -8px;
}
.account-grid > [class*='col-'] {
  padding: 0 8px;
  margin-bottom: 24px;
}

.account-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 18px 20px;
  height: 100%;
}

.account-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.avatar-box {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
}
.account-nick {
  font-size: 16px;
  font-weight: 700;
  color: #1e293b;
  line-height: 1.2;
}
.account-state {
  font-size: 12px;
  color: #64748b;
  margin-top: 2px;
}
.account-state i { font-size: 8px; }

.loading-tip,
.alert-error {
  padding: 14px;
  border-radius: 8px;
  font-size: 13px;
  text-align: center;
}
.loading-tip {
  background: #fef3c7;
  color: #92400e;
}
.alert-error {
  background: #fee2e2;
  color: #991b1b;
  text-align: left;
}

.profile-avatar-row {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}
.big-avatar {
  width: 96px;
  height: 96px;
  border-radius: 12px;
  object-fit: cover;
  flex-shrink: 0;
  border: 1px solid #e2e8f0;
}
.profile-grid {
  flex: 1;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px 14px;
}
.profile-field {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.field-label {
  font-size: 11px;
  color: #94a3b8;
}
.field-value {
  font-size: 13px;
  color: #1e293b;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.mono {
  font-family: 'Consolas', monospace;
}

.raw-details {
  margin-top: 14px;
  border-top: 1px solid #f1f5f9;
  padding-top: 10px;
}
.raw-details summary {
  cursor: pointer;
  font-size: 12px;
  color: var(--primary);
}
.raw-details pre {
  background: #0f172a;
  color: #e2e8f0;
  padding: 12px;
  border-radius: 8px;
  font-size: 12px;
  max-height: 260px;
  overflow: auto;
  margin-top: 8px;
}

.session-meta {
  margin-top: 14px;
  padding-top: 10px;
  border-top: 1px dashed #e2e8f0;
  display: flex;
  flex-wrap: wrap;
  gap: 6px 14px;
  font-size: 12px;
  color: #475569;
}

@media (max-width: 576px) {
  .profile-avatar-row { flex-direction: column; }
  .big-avatar { width: 72px; height: 72px; }
  .profile-grid { grid-template-columns: 1fr; }
}
</style>
