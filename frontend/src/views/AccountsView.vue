<script setup>
import { ref, reactive, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/utils/api'

const router = useRouter()

const loading = ref(false)
const refreshing = ref(false)
const lastError = ref('')
const protocols = ref([])
// port -> { loading, sessionList, counts, error }
const portState = reactive({})

// /GetSessionList 的鉴权 key（上游 API 共享 key），持久化到 localStorage
const apiKey = ref(localStorage.getItem('accounts_api_key') || '')
const notStartedAfter = ref(
  parseInt(localStorage.getItem('accounts_not_started_after') || '300', 10)
)
const showKeyInput = ref(!apiKey.value)
const keyError = ref('')

function persistKey() {
  localStorage.setItem('accounts_api_key', apiKey.value)
  localStorage.setItem('accounts_not_started_after', String(notStartedAfter.value))
}

let pollTimer = null

function portOf(item) {
  if (!item) return null
  if (typeof item.port === 'number') return item.port
  if (typeof item.StartPort === 'number') return item.StartPort
  if (item.Par && typeof item.Par === 'string') {
    const m = item.Par.match(/StartPort\s*=\s*(\d+)/i)
    if (m) return parseInt(m[1], 10)
  }
  return null
}

async function fetchProcessList() {
  const r = await api.post('/get_object_process_number', {})
  return r.data || {}
}

async function fetchSessionList(port) {
  return getSessionListWithKey(port)
}

async function getSessionListWithKey(port) {
  const r = await api.post('/get_session_list', {
    port,
    key: apiKey.value,
    not_started_after_seconds: notStartedAfter.value
  })
  return r.data || {}
}

function saveKeyAndReload() {
  keyError.value = ''
  if (!apiKey.value.trim()) {
    keyError.value = '请填写 key'
    return
  }
  persistKey()
  showKeyInput.value = false
  loadAll()
}

function editKey() {
  showKeyInput.value = true
}

async function loadAll({ silent = false } = {}) {
  if (silent) refreshing.value = true
  else loading.value = true
  lastError.value = ''
  // If key is not configured, just show the prompt and bail (don't spam /api)
  if (!apiKey.value.trim()) {
    showKeyInput.value = true
    loading.value = false
    refreshing.value = false
    return
  }
  try {
    const data = await fetchProcessList()
    const list = Array.isArray(data.List) ? data.List : []
    // Capture previous loading flags so we don't wipe card state while refetching
    const previous = { ...portState }
    protocols.value = list
    list.forEach((item) => {
      const port = portOf(item)
      if (!port) return
      portState[port] = previous[port] || {
        loading: true,
        sessions: [],
        counts: null,
        error: '',
        raw: null
      }
      portState[port].loading = true
      portState[port].error = ''
    })

    // Fetch session lists in parallel
    const ports = list.map((it) => portOf(it)).filter((p) => p !== null)
    await Promise.all(
      ports.map(async (port) => {
        try {
          const sl = await fetchSessionList(port)
          portState[port].raw = sl
          portState[port].sessions = Array.isArray(sl.sessions) ? sl.sessions : []
          portState[port].counts = sl.counts || null
          portState[port].error = sl.ok === false ? sl.error || 'session list failed' : ''
        } catch (e) {
          portState[port].sessions = []
          portState[port].counts = null
          portState[port].error =
            e?.response?.data?.error || e.message || '获取 session 列表失败'
        } finally {
          portState[port].loading = false
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

function openDetail(port) {
  router.push({ name: 'account-detail', params: { port } })
}

function fmtAge(sec) {
  if (sec == null) return '-'
  if (sec < 60) return `${sec}s`
  if (sec < 3600) return `${Math.floor(sec / 60)}m ${sec % 60}s`
  const h = Math.floor(sec / 3600)
  const m = Math.floor((sec % 3600) / 60)
  return `${h}h ${m}m`
}

function onlineCount(p) {
  return p?.counts?.online ?? 0
}
function totalCount(p) {
  if (typeof p?.raw?.total === 'number') return p.raw.total
  return p?.sessions?.length ?? 0
}
function offlineCount(p) {
  return p?.counts?.offline ?? 0
}
function notStartedCount(p) {
  return p?.counts?.not_started ?? 0
}

function statusBadgeClass(p) {
  if (p.loading) return 'badge-loading'
  if (p.error) return 'badge-error'
  if (onlineCount(p) > 0) return 'badge-online'
  if (totalCount(p) === 0) return 'badge-empty'
  return 'badge-idle'
}

function statusBadgeText(p) {
  if (p.loading) return '加载中'
  if (p.error) return '异常'
  if (onlineCount(p) > 0) return `${onlineCount(p)} 在线`
  if (totalCount(p) === 0) return '空'
  return `${totalCount(p)} 个账号`
}

onMounted(() => {
  loadAll()
  // light auto-refresh every 10s so login/logout elsewhere shows up
  pollTimer = setInterval(() => loadAll({ silent: true }), 10000)
})

onBeforeUnmount(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<template>
  <div>
    <div class="page-header">
      <h2>
        <i class="bi bi-people-fill" style="color: var(--primary)" />
        账号管理
      </h2>
      <div class="d-flex align-items-center gap-2">
        <div v-if="!showKeyInput && apiKey" class="key-pill" @click="editKey" title="点击修改 key">
          <i class="bi bi-key" />
          <span class="key-dots">●●●●●●●●</span>
          <i class="bi bi-pencil edit-icon" />
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
    </div>

    <div v-if="showKeyInput" class="card key-card">
      <div class="card-body">
        <div class="d-flex align-items-center mb-2">
          <i class="bi bi-key-fill me-2" style="color: var(--primary); font-size: 18px" />
          <strong>配置上游 API key</strong>
        </div>
        <div class="text-muted" style="font-size: 12px; margin-bottom: 12px">
          /GetSessionList 需要鉴权 key（共享给所有实例）。保存到 localStorage，仅本机使用。
        </div>
        <div class="row g-2 align-items-end">
          <div class="col-md-6">
            <label class="form-label" style="font-size: 12px">key <span class="text-danger">*</span></label>
            <input
              v-model="apiKey"
              type="text"
              class="form-control form-control-sm mono"
              placeholder="请输入上游 API key"
              @keyup.enter="saveKeyAndReload"
            />
          </div>
          <div class="col-md-3">
            <label class="form-label" style="font-size: 12px">not_started_after_seconds</label>
            <input
              v-model.number="notStartedAfter"
              type="number"
              min="0"
              class="form-control form-control-sm"
            />
          </div>
          <div class="col-md-3 d-flex gap-2">
            <button class="btn btn-sm btn-primary flex-fill" @click="saveKeyAndReload">
              <i class="bi bi-check2" /> 保存并加载
            </button>
          </div>
        </div>
        <div v-if="keyError" class="text-danger mt-2" style="font-size: 12px">
          <i class="bi bi-exclamation-triangle me-1" />{{ keyError }}
        </div>
      </div>
    </div>

    <div v-if="!showKeyInput && loading && protocols.length === 0" class="card">
      <div class="card-body text-center text-muted" style="padding: 40px">
        <i class="bi bi-hourglass-split" /> 正在加载协议列表...
      </div>
    </div>

    <div v-else-if="!showKeyInput && lastError" class="alert alert-danger">
      <i class="bi bi-exclamation-triangle me-2" />{{ lastError }}
    </div>

    <div v-else-if="!showKeyInput && protocols.length === 0" class="card">
      <div class="card-body text-center text-muted" style="padding: 40px">
        <i class="bi bi-inbox" style="font-size: 32px" />
        <div class="mt-2">暂无运行中的协议</div>
        <div style="font-size: 12px">请到「协议上号」启动一个实例</div>
      </div>
    </div>

    <div v-else class="row g-4 protocol-grid">
      <div
        v-for="item in protocols"
        :key="item.Index ?? item.PID"
        class="col-lg-4 col-md-6"
      >
        <div
          class="protocol-card"
          :class="{ 'is-clickable': true }"
          @click="openDetail(portOf(item))"
        >
          <div class="protocol-card-head">
            <div>
              <div class="protocol-port">
                <i class="bi bi-hdd-network" /> Port: {{ portOf(item) }}
              </div>
              <div class="protocol-pid">PID: {{ item.PID }} · Index: {{ item.Index }}</div>
            </div>
            <span class="status-badge" :class="statusBadgeClass(portState[portOf(item)] || {})">
              {{ statusBadgeText(portState[portOf(item)] || {}) }}
            </span>
          </div>

          <div class="protocol-card-body">
            <div class="count-row">
              <div class="count-cell">
                <div class="count-num text-success">{{ onlineCount(portState[portOf(item)] || {}) }}</div>
                <div class="count-label">在线</div>
              </div>
              <div class="count-cell">
                <div class="count-num text-secondary">{{ offlineCount(portState[portOf(item)] || {}) }}</div>
                <div class="count-label">离线</div>
              </div>
              <div class="count-cell">
                <div class="count-num text-warning">{{ notStartedCount(portState[portOf(item)] || {}) }}</div>
                <div class="count-label">未启动</div>
              </div>
              <div class="count-cell">
                <div class="count-num text-primary">{{ totalCount(portState[portOf(item)] || {}) }}</div>
                <div class="count-label">总数</div>
              </div>
            </div>

            <div v-if="(portState[portOf(item)] || {}).error" class="card-error">
              <i class="bi bi-exclamation-triangle" />
              {{ (portState[portOf(item)] || {}).error }}
            </div>

            <div v-else-if="(portState[portOf(item)] || {}).sessions?.length" class="rdv-list">
              <div
                v-for="s in (portState[portOf(item)] || {}).sessions.slice(0, 3)"
                :key="s.session_id"
                class="rdv-row"
              >
                <i
                  class="bi"
                  :class="s.online ? 'bi-circle-fill text-success' : 'bi-circle text-secondary'"
                />
                <span class="rdv-code">{{ s.rdv || '-' }}</span>
                <span class="rdv-state">{{ s.state }}</span>
              </div>
              <div
                v-if="(portState[portOf(item)] || {}).sessions.length > 3"
                class="rdv-more"
              >
                ... 还有 {{ (portState[portOf(item)] || {}).sessions.length - 3 }} 个
              </div>
            </div>

            <div v-else-if="!(portState[portOf(item)] || {}).loading" class="empty-tip">
              <i class="bi bi-person-dash" /> 该协议上没有微信账号
            </div>
          </div>

          <div class="protocol-card-foot">
            <span>查看账号详情</span>
            <i class="bi bi-arrow-right" />
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
}
.refresh-btn {
  display: inline-flex;
  align-items: center;
}
.spin-icon {
  animation: spin 1s linear infinite;
}

.key-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: #eef2ff;
  color: #3730a3;
  padding: 4px 10px 4px 8px;
  border-radius: 999px;
  font-size: 12px;
  cursor: pointer;
  transition: 0.15s;
  border: 1px solid transparent;
}
.key-pill:hover {
  background: #e0e7ff;
  border-color: var(--primary);
}
.key-pill .key-dots {
  font-family: 'Consolas', monospace;
  letter-spacing: 1px;
  font-size: 13px;
}
.key-pill .edit-icon {
  font-size: 11px;
  opacity: 0;
  transition: 0.15s;
}
.key-pill:hover .edit-icon {
  opacity: 1;
}

.key-card {
  border-left: 3px solid var(--primary);
  margin-bottom: 20px;
}
.mono {
  font-family: 'Consolas', monospace;
}
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.protocol-grid {
  display: flex;
  flex-wrap: wrap;
  margin: 0 -8px;
}
.protocol-grid > [class*='col-'] {
  padding: 0 8px;
  margin-bottom: 24px;
}

.protocol-card {
  background: #fff;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  overflow: hidden;
  transition: 0.18s;
  display: flex;
  flex-direction: column;
  height: 100%;
}
.protocol-card.is-clickable {
  cursor: pointer;
}
.protocol-card.is-clickable:hover {
  border-color: var(--primary);
  box-shadow: 0 6px 16px rgba(99, 102, 241, 0.12);
  transform: translateY(-2px);
}

.protocol-card-head {
  padding: 16px 18px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  border-bottom: 1px solid #f1f5f9;
  background: linear-gradient(180deg, #f8fafc 0%, #ffffff 100%);
}
.protocol-port {
  font-size: 16px;
  font-weight: 700;
  color: #1e293b;
  display: flex;
  align-items: center;
  gap: 6px;
}
.protocol-port i {
  color: var(--primary);
}
.protocol-pid {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 4px;
  font-family: 'Consolas', monospace;
}

.status-badge {
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
}
.badge-online { background: #d1fae5; color: #065f46; }
.badge-idle { background: #e0e7ff; color: #3730a3; }
.badge-empty { background: #f1f5f9; color: #64748b; }
.badge-loading { background: #fef3c7; color: #92400e; }
.badge-error { background: #fee2e2; color: #991b1b; }

.protocol-card-body {
  padding: 16px 18px;
  flex: 1;
}
.count-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  margin-bottom: 14px;
}
.count-cell {
  text-align: center;
  background: #f8fafc;
  border-radius: 8px;
  padding: 10px 4px;
}
.count-num {
  font-size: 20px;
  font-weight: 700;
  line-height: 1.1;
}
.count-label {
  font-size: 11px;
  color: #94a3b8;
  margin-top: 2px;
}

.rdv-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.rdv-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #475569;
}
.rdv-row i { font-size: 8px; }
.rdv-code {
  font-family: 'Consolas', monospace;
  color: #1e293b;
  font-weight: 600;
}
.rdv-state {
  margin-left: auto;
  font-size: 11px;
  color: #94a3b8;
  text-transform: uppercase;
}
.rdv-more {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 2px;
}
.empty-tip {
  font-size: 13px;
  color: #94a3b8;
  text-align: center;
  padding: 12px 0;
}
.card-error {
  background: #fee2e2;
  color: #991b1b;
  font-size: 12px;
  padding: 8px 10px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.protocol-card-foot {
  padding: 10px 18px;
  border-top: 1px solid #f1f5f9;
  font-size: 13px;
  color: var(--primary);
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 500;
  background: #fafbfc;
}
.protocol-card-foot i {
  transition: 0.15s;
}
.protocol-card.is-clickable:hover .protocol-card-foot i {
  transform: translateX(4px);
}
</style>
