<script setup>
import { ref, reactive, onMounted, onBeforeUnmount, watch } from 'vue'
import api from '@/utils/api'

// ─────────────────────────────── state ───────────────────────────────
const form = reactive({
  startPort: '',
  rdv: '',
  wxid: ''
})

const submitting = ref(false)
const resultPanel = ref(false)
const successPanel = ref(false)
const stepText = ref('')
const status = ref({ cls: 'waiting', icon: 'hourglass-split', text: '正在推送登录请求...' })
const confirmInfo = ref({ show: false, avatar: '', nick: '' })
const resultInfo = ref({ uuid: '', msg: '' })
const successInfo = ref({ nick: '', wxid: '' })
const rdvMapping = ref({})
const rdvHint = ref('')
const lastError = ref('')

let pollTimer = null
let currentPort = null
let currentUUID = null
let currentSessionId = null

// ─────────────────────────────── helpers ─────────────────────────────
function getMappingWxid(entry) {
  if (!entry) return ''
  return typeof entry === 'object' ? entry.wxid || entry.userName || '' : entry
}
function getMappingPort(entry) {
  if (!entry || typeof entry !== 'object') return ''
  return entry.port || entry.StartPort || entry.startPort || ''
}
function isSameMapping(entry, wxid, port) {
  return getMappingWxid(entry) === wxid && getMappingPort(entry) === port
}

function setStatus(cls, icon, text) {
  status.value = { cls, icon, text }
}

function disableForm(d) {
  submitting.value = d
}

// ─────────────────────────────── mapping list ───────────────────────
async function loadMapping() {
  try {
    const { data } = await api.get('/get_rdv_mapping')
    rdvMapping.value = data || {}
  } catch (e) {
    /* ignore */
  }
}

function fillFromList(rdv) {
  const entry = rdvMapping.value[rdv]
  if (!entry) return
  const wxid = getMappingWxid(entry)
  const port = getMappingPort(entry)
  if (port) form.startPort = port
  form.rdv = rdv
  form.wxid = wxid
  rdvHint.value = '已自动填充WXID（来自已保存映射）'
}

async function deleteMapping(rdv) {
  if (!confirm(`确定要删除 RDV=${rdv} 的映射吗？`)) return
  try {
    const r = await api.post('/delete_rdv_mapping', { rdv })
    if (r.data?.mapping) rdvMapping.value = r.data.mapping
  } catch (e) {
    /* ignore */
  }
}

watch(
  () => form.rdv,
  (rdv) => {
    const v = (rdv || '').trim()
    if (!v) {
      rdvHint.value = ''
      return
    }
    if (rdvMapping.value[v]) {
      const entry = rdvMapping.value[v]
      const port = getMappingPort(entry)
      if (port && !form.startPort) form.startPort = port
      form.wxid = getMappingWxid(entry)
      rdvHint.value = '已自动匹配WXID'
    } else {
      rdvHint.value = '此RDV暂无映射，请手动输入WXID'
    }
  }
)

// ─────────────────────────────── flow ───────────────────────────────
async function startOldLogin() {
  lastError.value = ''
  if (!form.startPort || !form.rdv || !form.wxid) {
    alert('请填写 StartPort、RDV 和 WXID')
    return
  }

  currentPort = form.startPort
  currentUUID = null
  currentSessionId = null
  disableForm(true)
  resultPanel.value = true
  successPanel.value = false
  confirmInfo.value.show = false
  setStatus('status-waiting', 'hourglass-split', '正在检查端口...')

  try {
    // 1. 检查端口
    setStatus('status-waiting', 'hourglass-split', '正在检查端口...')
    let check
    try {
      const r = await api.post('/check_port', { StartPort: parseInt(form.startPort, 10) })
      check = r.data
    } catch (e) {
      throw new Error(e?.response?.data?.error || e.message || '检查端口失败')
    }
    if (check?.error) throw new Error(check.error)
    if (check?.Occupied === true || check?.Occupied === '1' || check?.Occupied === 1) {
      throw new Error(`端口 ${form.startPort} 已被占用，请更换端口`)
    }

    // 2. 启动协议进程
    setStatus('status-waiting', 'hourglass-split', '正在启动协议进程...')
    let proc
    try {
      const r = await api.post('/start_object_process', {
        StartPort: parseInt(form.startPort, 10)
      })
      proc = r.data
    } catch (e) {
      throw new Error(e?.response?.data?.error || e.message || '启动协议进程失败')
    }
    if (proc?.error) throw new Error(proc.error)
    if (proc && proc.Status && proc.Status !== 'started') {
      throw new Error('协议进程未正常启动: ' + JSON.stringify(proc))
    }
    // 实例端口 = 用户在页面输入的端口（也就是 StartObjectProcess 传入的 StartPort）。
    // 不取 proc.Port，因为那个字段含义不可靠；用户输入的那个值才是调用 StartObjectProcess 的参数。
    const instancePort = parseInt(form.startPort, 10)
    if (!instancePort) throw new Error('端口号无效')

    // 3. 启动微信 (老号登录不需要 CallBackURL 和代理)
    // 注意：/StartWechat 是调用在实例端口（用户输入的端口），不是 mgr 端口
    setStatus('status-waiting', 'hourglass-split', '正在启动微信...')
    let startRes
    try {
      const r = await api.post('/start_wechat', {
        port: instancePort,
        StartPort: instancePort,
        RDV: form.rdv,
        CallBackURL: '',
        Proxy_Type: '',
        Proxy_IP: '',
        Proxy_Port: '',
        Proxy_Usr: '',
        Proxy_Pwd: ''
      })
      startRes = r.data
    } catch (e) {
      throw new Error(e?.response?.data?.error || e.message || '启动微信失败')
    }
    if (startRes?.error) throw new Error(startRes.error)
    if (!startRes?.ok) {
      throw new Error('启动微信失败: ' + (startRes?.error || JSON.stringify(startRes)))
    }
    currentSessionId = startRes.session_id || ''
    if (!currentSessionId) throw new Error('未获取到 session_id')
    currentPort = String(instancePort)

    // 4. 保存 RDV → WXID 映射
    if (!isSameMapping(rdvMapping.value[form.rdv], form.wxid, form.startPort)) {
      try {
        const r = await api.post('/save_rdv_mapping', {
          rdv: form.rdv,
          wxid: form.wxid,
          port: form.startPort,
          proxy: {}
        })
        if (r.data?.mapping) rdvMapping.value = r.data.mapping
        else rdvMapping.value[form.rdv] = { wxid: form.wxid, port: form.startPort, proxy: {} }
      } catch (e) {
        /* ignore */
      }
    }

    // 5. 推送老设备登录 pushloginurl
    setStatus('status-waiting', 'hourglass-split', '正在推送登录请求...')
    let pushRes
    try {
      const r = await api.post('/push_login_url', {
        port: instancePort,
        session_id: currentSessionId,
        wxid: form.wxid
      })
      pushRes = r.data
    } catch (e) {
      throw new Error(e?.response?.data?.error || e.message || '推送登录失败')
    }
    if (pushRes?.error) throw new Error(pushRes.error)
    if (!pushRes?.ok) {
      throw new Error('推送登录失败: ' + (pushRes?.error || JSON.stringify(pushRes)))
    }
    // 兼容多种返回结构
    const qr = pushRes.qrcode || pushRes.data || pushRes
    currentUUID = qr.uuid || pushRes.uuid
    if (!currentUUID) throw new Error('未获取到 uuid')

    resultInfo.value = {
      uuid: currentUUID,
      msg: '请在手机微信确认登录'
    }
    setStatus('status-scanned', 'phone', '已推送登录请求，请在手机确认...')
    startPolling()
  } catch (e) {
    setStatus('status-error', 'exclamation-triangle', e.message || '流程失败')
    disableForm(false)
  }
}

function startPolling() {
  if (pollTimer) clearInterval(pollTimer)
  pollTimer = setInterval(async () => {
    try {
      const r = await api.post('/check_qrcode', {
        port: currentPort,
        session_id: currentSessionId,
        uuid: currentUUID
      })
      const data = r.data
      if (data?.error) return
      const check = data?.check_status || data?.data || {}
      const state = check.state ?? data?.state
      const expired = check.expired_time ?? data?.expired_time ?? data?.expiredTime

      if (state === 0 || state === 'polling' || data?.state === 'polling') {
        setStatus('status-waiting', 'hourglass-split', `等待确认... (${expired ?? '?'}秒后过期)`)
      } else if (state === 1 || state === 'scanned' || data?.state === 'scanned') {
        const nick = check.nick_name || check.nickName
        const head = check.head_img_url || check.headImgUrl
        setStatus('status-scanned', 'check-circle', '已扫码，请在手机确认登录')
        if (head) {
          confirmInfo.value = { show: true, avatar: head, nick: nick || '' }
        }
      } else if (state === 2 || state === 'logged_in' || data?.state === 'logged_in') {
        clearInterval(pollTimer)
        pollTimer = null
        setStatus('status-confirmed', 'check2', '用户已确认，登录成功！')
        const userName = check.user_name || check.userName
        successInfo.value = { nick: '', wxid: userName || form.wxid }
        successPanel.value = true
        disableForm(false)
      }

      if (expired !== undefined && expired <= 0) {
        clearInterval(pollTimer)
        pollTimer = null
        setStatus('status-error', 'x-circle', '登录超时，请重新操作')
        disableForm(false)
      }
    } catch (e) {
      /* ignore */
    }
  }, 3000)
}

function reset() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
  resultPanel.value = false
  successPanel.value = false
  confirmInfo.value.show = false
  setStatus('status-waiting', 'hourglass-split', '正在推送登录请求...')
  currentPort = null
  currentUUID = null
  currentSessionId = null
  disableForm(false)
}

onMounted(() => {
  loadMapping()
})

onBeforeUnmount(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<template>
  <div>
    <div class="page-header">
      <h2>
        <i class="bi bi-person-badge" style="color: var(--primary)" />
        老号登录
      </h2>
    </div>

    <div class="row g-4">
      <!-- 左侧表单 -->
      <div class="col-lg-5">
        <div class="card">
          <div class="card-header">
            <i class="bi bi-gear me-2" />
            登录参数
          </div>
          <div class="card-body">
            <form @submit.prevent="startOldLogin">
              <div class="mb-3">
                <label class="form-label">
                  StartPort <span class="text-danger">*</span>
                </label>
                <input
                  v-model="form.startPort"
                  type="number"
                  class="form-control"
                  placeholder="请输入端口 (如 30004)"
                  required
                />
              </div>
              <div class="mb-3">
                <label class="form-label">
                  RDV <span class="text-danger">*</span>
                </label>
                <input
                  v-model="form.rdv"
                  type="text"
                  class="form-control"
                  placeholder="请输入 RDV"
                  required
                />
                <div class="form-text">输入RDV后会自动匹配对应的wxid</div>
              </div>
              <div class="mb-3">
                <label class="form-label">
                  WXID <span class="text-danger">*</span>
                </label>
                <input
                  v-model="form.wxid"
                  type="text"
                  class="form-control"
                  placeholder="请输入 WXID"
                  required
                />
                <div v-if="rdvHint" class="form-text text-primary">
                  {{ rdvHint }}
                </div>
              </div>

              <button
                type="submit"
                class="btn btn-primary w-100 mt-3"
                :disabled="submitting"
                style="height: 44px; font-weight: 600"
              >
                <span v-if="submitting" class="spinner" />
                <i v-else class="bi bi-box-arrow-in-right" />
                {{ submitting ? '处理中...' : '开始老号登录' }}
              </button>
              <button
                v-if="resultPanel"
                type="button"
                class="btn btn-ghost w-100 mt-2"
                @click="reset"
              >
                取消 / 重新登录
              </button>
            </form>
          </div>
        </div>

        <div class="card mt-4">
          <div class="card-header">
            <i class="bi bi-collection me-2" />
            已保存的 RDV → WXID 映射
          </div>
          <div class="card-body">
            <div
              v-if="Object.keys(rdvMapping).length === 0"
              class="text-center text-muted py-4"
            >
              <i class="bi bi-inbox" style="font-size: 32px" />
              <div class="mt-2" style="font-size: 13px">暂无已保存的映射</div>
            </div>
            <div
              v-for="(entry, rdv) in rdvMapping"
              :key="rdv"
              class="wxid-list-item"
              @click="fillFromList(rdv)"
            >
              <i class="bi bi-person-badge" style="color: var(--primary)" />
              <span class="wxid-text">{{ getMappingWxid(entry) }}</span>
              <span class="rdv-text">
                <template v-if="getMappingPort(entry)">Port: {{ getMappingPort(entry) }} · </template>
                RDV: {{ rdv }}
              </span>
              <i
                class="bi bi-x-circle-fill delete-btn"
                @click.stop="deleteMapping(rdv)"
                title="删除"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧结果 -->
      <div v-if="resultPanel" class="col-lg-7">
        <div class="card">
          <div class="card-header">
            <i class="bi bi-send-check me-2" />
            老号登录进度
          </div>
          <div class="card-body">
            <div class="status-badge" :class="status.cls">
              <i :class="`bi bi-${status.icon}`" />
              <span>{{ status.text }}</span>
            </div>

            <div v-if="confirmInfo.show" class="user-confirm-info">
              <img :src="confirmInfo.avatar" alt="" />
              <div>
                <div style="font-weight: 600; color: #1e293b">
                  {{ confirmInfo.nick }}
                </div>
                <div style="font-size: 12px; color: #94a3b8">
                  已扫码，请在手机确认登录
                </div>
              </div>
            </div>

            <div
              v-if="resultInfo.uuid"
              class="mt-3 result-info"
              style="font-size: 13px; color: #64748b"
            >
              <div>
                <strong>UUID:</strong>
                <span class="mono">{{ resultInfo.uuid }}</span>
              </div>
              <div class="mt-1 text-primary">
                <i class="bi bi-phone me-1" />{{ resultInfo.msg }}
              </div>
            </div>
          </div>
        </div>

        <div v-if="successPanel" class="card mt-4">
          <div class="card-body login-success-card">
            <div class="check-icon">
              <i class="bi bi-check-lg" />
            </div>
            <h4 style="color: #1e293b; font-weight: 700">登录成功</h4>
            <div class="text-muted">
              <strong>{{ successInfo.wxid }}</strong><br />
              <span style="font-size: 13px">
                wxid: {{ successInfo.wxid }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.row {
  display: flex;
  flex-wrap: wrap;
  margin: 0 -8px;
}
.row > [class*='col-'] {
  padding: 0 8px;
}
.col-lg-5 {
  flex: 0 0 41.6667%;
  max-width: 41.6667%;
}
.col-lg-7 {
  flex: 0 0 58.3333%;
  max-width: 58.3333%;
}
.g-4 > * {
  margin-bottom: 24px;
}
@media (max-width: 991px) {
  .col-lg-5,
  .col-lg-7 {
    flex: 0 0 100%;
    max-width: 100%;
  }
}

.login-success-card {
  text-align: center;
  padding: 32px;
}
.login-success-card .check-icon {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: #d1fae5;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
}
.login-success-card .check-icon i {
  font-size: 32px;
  color: #10b981;
}

.wxid-list-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: #f8fafc;
  border-radius: 8px;
  cursor: pointer;
  transition: 0.15s;
  border: 1.5px solid transparent;
  margin-bottom: 8px;
}
.wxid-list-item:hover {
  background: #e2e8f0;
  border-color: var(--primary);
}
.wxid-list-item .wxid-text {
  font-family: 'Consolas', monospace;
  font-size: 14px;
  color: #1e293b;
  font-weight: 600;
}
.wxid-list-item .rdv-text {
  font-size: 12px;
  color: #94a3b8;
  margin-left: auto;
}
.wxid-list-item .delete-btn {
  opacity: 0;
  transition: 0.15s;
  color: var(--danger);
  cursor: pointer;
}
.wxid-list-item:hover .delete-btn {
  opacity: 1;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
}
.status-waiting {
  background: #fef3c7;
  color: #92400e;
}
.status-scanned {
  background: #d1fae5;
  color: #065f46;
}
.status-confirmed {
  background: #dbeafe;
  color: #1e40af;
}
.status-success {
  background: #d1fae5;
  color: #065f46;
}
.status-error {
  background: #fee2e2;
  color: #991b1b;
}

.user-confirm-info {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px;
  background: #f8fafc;
  border-radius: 10px;
  margin-top: 12px;
}
.user-confirm-info img {
  width: 48px;
  height: 48px;
  border-radius: 50%;
}

.result-info {
  background: #f8fafc;
  padding: 12px 16px;
  border-radius: 8px;
}
</style>
