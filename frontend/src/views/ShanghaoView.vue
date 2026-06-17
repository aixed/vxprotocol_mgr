<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount } from 'vue'
import api from '@/utils/api'

// ─────────────────────────────── state ───────────────────────────────
const form = reactive({
  startPort: localStorage.getItem('sh_startPort') || '30004',
  rdv: localStorage.getItem('sh_rdv') || '',
  callBackURL: localStorage.getItem('sh_callBackURL') || '',
  proxyType: localStorage.getItem('sh_proxyType') || '',
  proxyIP: localStorage.getItem('sh_proxyIP') || '',
  proxyPort: localStorage.getItem('sh_proxyPort') || '',
  proxyUsr: localStorage.getItem('sh_proxyUsr') || '',
  proxyPwd: localStorage.getItem('sh_proxyPwd') || ''
})

const submitting = ref(false)
const resultPanel = ref(false)
const successPanel = ref(false)
const step = ref(0)
const stepText = ref('')
const qrImgUrl = ref('')
const scanStatus = ref({ cls: 'waiting', text: '等待扫码...' })
const showScanned = ref(false)
const scannedInfo = ref({ avatar: '', nick: '' })
const successInfo = ref({ nick: '', wxid: '' })
const rdvMapping = ref({})
const lastError = ref('')

let pollTimer = null
let currentPort = null
let currentUUID = null
let currentSessionId = null

// ─────────────────────────────── computed ────────────────────────────
const useProxyCredentials = computed(() => form.proxyType && form.proxyType !== 'socks5')

// ─────────────────────────────── helpers ─────────────────────────────
function persist() {
  Object.keys(form).forEach((k) => {
    localStorage.setItem('sh_' + k, form[k])
  })
}

function setStep(n, text) {
  step.value = n
  stepText.value = text || ''
}

function setStatus(cls, text) {
  scanStatus.value = { cls, text }
}

function disableForm(disabled) {
  submitting.value = disabled
}

function hexToObjectUrl(hex) {
  if (!hex) return ''
  const clean = hex.replace(/\s+/g, '')
  const bytes = new Uint8Array(clean.match(/.{2}/g).map((b) => parseInt(b, 16)))
  return URL.createObjectURL(new Blob([bytes], { type: 'image/png' }))
}

function revokeQr() {
  if (qrImgUrl.value && qrImgUrl.value.startsWith('blob:')) {
    URL.revokeObjectURL(qrImgUrl.value)
  }
  qrImgUrl.value = ''
}

function getMappingWxid(entry) {
  if (!entry) return ''
  return typeof entry === 'object' ? entry.wxid || entry.userName || '' : entry
}
function getMappingPort(entry) {
  if (!entry || typeof entry !== 'object') return ''
  return entry.port || entry.StartPort || entry.startPort || ''
}
function getMappingProxy(entry) {
  if (!entry || typeof entry !== 'object' || !entry.proxy) return {}
  return entry.proxy
}
function hasProxyConfig(p) {
  return !!(p.Proxy_Type || p.Proxy_IP || p.Proxy_Port || p.Proxy_Usr || p.Proxy_Pwd)
}

// ─────────────────────────────── mapping list ───────────────────────
async function loadAccountConfigs() {
  try {
    const { data } = await api.get('/get_rdv_mapping')
    rdvMapping.value = data || {}
  } catch (e) {
    /* ignore */
  }
}

function fillAccountConfig(rdv) {
  const entry = rdvMapping.value[rdv]
  if (!entry) return
  const port = getMappingPort(entry)
  const proxy = getMappingProxy(entry)
  if (port) form.startPort = port
  form.rdv = rdv
  form.proxyType = proxy.Proxy_Type || ''
  form.proxyIP = proxy.Proxy_IP || ''
  form.proxyPort = proxy.Proxy_Port || ''
  form.proxyUsr = proxy.Proxy_Usr || ''
  form.proxyPwd = proxy.Proxy_Pwd || ''
  persist()
}

// ─────────────────────────────── flow ───────────────────────────────
async function startLogin() {
  lastError.value = ''
  if (!form.startPort || !form.rdv) {
    alert('请填写 StartPort 和 RDV')
    return
  }
  persist()

  currentPort = form.startPort
  currentUUID = null
  currentSessionId = null
  disableForm(true)
  resultPanel.value = true
  successPanel.value = false
  showScanned.value = false
  revokeQr()
  setStatus('waiting', '准备中...')

  try {
    // ── 步骤 1: 检查端口 ──
    setStep(1, '正在检查端口是否可用...')
    let check
    try {
      const r = await api.post('/check_port', { StartPort: parseInt(form.startPort, 10) })
      check = r.data
    } catch (e) {
      throw new Error(e?.response?.data?.error || e.message || '检查端口失败')
    }
    if (check?.error) throw new Error(check.error)
    // 服务端返回 Occupied: false / true
    if (check?.Occupied === true || check?.Occupied === '1' || check?.Occupied === 1) {
      throw new Error(`端口 ${form.startPort} 已被占用，请更换端口`)
    }

    // ── 步骤 2: 启动协议进程 StartObjectProcess ──
    setStep(2, '正在启动协议进程...')
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

    // ── 步骤 3: 启动微信 StartWechat ──
    // 注意：/StartWechat 是调用在实例端口（用户输入的端口），不是 mgr 端口
    setStep(3, '正在启动微信...')
    let startRes
    try {
      const r = await api.post('/start_wechat', {
        port: instancePort,
        StartPort: instancePort,
        RDV: form.rdv,
        CallBackURL: form.callBackURL || '',
        Proxy_Type: form.proxyType || '',
        Proxy_IP: form.proxyIP || '',
        Proxy_Port: form.proxyPort || '',
        Proxy_Usr: useProxyCredentials.value ? form.proxyUsr || '' : '',
        Proxy_Pwd: useProxyCredentials.value ? form.proxyPwd || '' : ''
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
    // 同步更新 currentPort，后续 /getloginqrcode / /checkloginqrcode 都用实例端口
    currentPort = String(instancePort)

    // ── 步骤 4: 获取二维码 getloginqrcode ──
    setStep(4, '正在获取登录二维码...')
    let qr
    try {
      const r = await api.post('/get_qrcode', {
        port: instancePort,
        session_id: currentSessionId
      })
      qr = r.data
    } catch (e) {
      throw new Error(e?.response?.data?.error || e.message || '获取二维码失败')
    }
    if (qr?.error) throw new Error(qr.error)
    const qrHex = qr?.qrcode?.qrcode_png_hex
    if (!qrHex) throw new Error('未获取到二维码内容')

    currentUUID = qr.qrcode.uuid
    revokeQr()
    qrImgUrl.value = hexToObjectUrl(qrHex)
    setStatus('waiting', '请使用微信扫描二维码')
    setStep(4, '等待用户扫码登录...')
    startPolling()
  } catch (e) {
    setStep(step.value, '')
    setStatus('error', e.message || '流程失败')
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
        setStatus('waiting', `等待扫码... (剩余 ${expired ?? '?'} 秒)`)
      } else if (state === 1 || state === 'scanned' || data?.state === 'scanned') {
        const nick = check.nick_name || check.nickName
        const head = check.head_img_url || check.headImgUrl
        setStatus('scanned', `${nick || '用户'} 已扫码，请在手机上确认登录`)
        if (head) {
          scannedInfo.value = { avatar: head, nick: nick || '' }
          showScanned.value = true
        }
      } else if (state === 2 || state === 'logged_in' || data?.state === 'logged_in') {
        clearInterval(pollTimer)
        pollTimer = null
        setStatus('confirmed', '用户已确认，正在完成登录...')
        const userName = check.user_name || check.userName
        await onLoggedIn(userName)
      }

      if (expired !== undefined && expired <= 0) {
        clearInterval(pollTimer)
        pollTimer = null
        setStatus('error', '二维码已过期，请重新上号')
        disableForm(false)
      }
    } catch (e) {
      /* ignore polling errors */
    }
  }, 5000)
}

async function onLoggedIn(userName) {
  // 登录成功：保存映射
  try {
    if (userName) {
      const proxy = {
        Proxy_Type: form.proxyType || '',
        Proxy_IP: form.proxyIP || '',
        Proxy_Port: form.proxyPort || '',
        Proxy_Usr: useProxyCredentials.value ? form.proxyUsr || '' : '',
        Proxy_Pwd: useProxyCredentials.value ? form.proxyPwd || '' : ''
      }
      await api.post('/save_rdv_mapping', {
        rdv: form.rdv,
        wxid: userName,
        port: form.startPort,
        proxy
      })
    }
  } catch (e) {
    /* ignore */
  }
  await loadAccountConfigs()
  successInfo.value = { nick: '', wxid: userName || '' }
  setStatus('success', '登录成功')
  successPanel.value = true
  disableForm(false)
}

function reset() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
  revokeQr()
  resultPanel.value = false
  successPanel.value = false
  showScanned.value = false
  step.value = 0
  stepText.value = ''
  setStatus('waiting', '等待扫码...')
  currentPort = null
  currentUUID = null
  currentSessionId = null
  disableForm(false)
}

onMounted(() => {
  loadAccountConfigs()
})

onBeforeUnmount(() => {
  if (pollTimer) clearInterval(pollTimer)
  revokeQr()
})
</script>

<template>
  <div>
    <div class="page-header">
      <h2>
        <i class="bi bi-qr-code-scan" style="color: var(--primary)" />
        协议上号
      </h2>
    </div>

    <div class="row g-4">
      <!-- 左侧表单 -->
      <div class="col-lg-5">
        <div class="card">
          <div class="card-header">
            <i class="bi bi-gear me-2" />
            上号参数
          </div>
          <div class="card-body">
            <form @submit.prevent="startLogin">
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
              </div>
              <div class="mb-3">
                <label class="form-label">CallBackURL</label>
                <input
                  v-model="form.callBackURL"
                  type="text"
                  class="form-control"
                  placeholder="如 http://localhost:8000/receiveChatBotMsg/msg (留空可跳过)"
                />
              </div>

              <div class="proxy-section">
                <div class="proxy-title">
                  <i class="bi bi-shield-lock me-1" />
                  代理设置（可选）
                </div>
                <div class="row g-2">
                  <div class="col-12">
                    <label class="form-label">Proxy_Type</label>
                    <select v-model="form.proxyType" class="form-select">
                      <option value="">不使用代理</option>
                      <option value="socks5h">socks5h</option>
                      <option value="socks5">socks5</option>
                      <option value="http">http</option>
                      <option value="https">https</option>
                    </select>
                  </div>
                  <div class="col-8">
                    <label class="form-label">Proxy_IP</label>
                    <input
                      v-model="form.proxyIP"
                      type="text"
                      class="form-control"
                      placeholder="IP 地址"
                    />
                  </div>
                  <div class="col-4">
                    <label class="form-label">Proxy_Port</label>
                    <input
                      v-model="form.proxyPort"
                      type="text"
                      class="form-control"
                      placeholder="端口"
                    />
                  </div>
                  <div v-if="useProxyCredentials" class="col-6">
                    <label class="form-label">Proxy_Usr</label>
                    <input
                      v-model="form.proxyUsr"
                      type="text"
                      class="form-control"
                      placeholder="用户名"
                    />
                  </div>
                  <div v-if="useProxyCredentials" class="col-6">
                    <label class="form-label">Proxy_Pwd</label>
                    <input
                      v-model="form.proxyPwd"
                      type="password"
                      class="form-control"
                      placeholder="密码"
                    />
                  </div>
                </div>
              </div>

              <button
                type="submit"
                class="btn btn-primary w-100 mt-4"
                :disabled="submitting"
                style="height: 44px; font-weight: 600"
              >
                <span v-if="submitting" class="spinner" />
                <i v-else class="bi bi-play-fill" />
                {{ submitting ? '处理中...' : '确定上号' }}
              </button>
              <button
                v-if="resultPanel"
                type="button"
                class="btn btn-ghost w-100 mt-2"
                @click="reset"
              >
                取消 / 重新上号
              </button>
            </form>
          </div>
        </div>

        <div class="card mt-4">
          <div class="card-header">
            <i class="bi bi-collection me-2" />
            已登录账号配置
          </div>
          <div class="card-body" id="accountConfigList">
            <div
              v-if="Object.keys(rdvMapping).length === 0"
              class="text-center text-muted py-4"
            >
              <i class="bi bi-inbox" style="font-size: 32px" />
              <div class="mt-2" style="font-size: 13px">暂无已登录账号配置</div>
            </div>
            <div
              v-for="(entry, rdv) in rdvMapping"
              :key="rdv"
              class="account-config-item"
              @click="fillAccountConfig(rdv)"
            >
              <i class="bi bi-person-badge" style="color: var(--primary)" />
              <span class="wxid-text">{{ getMappingWxid(entry) || '-' }}</span>
              <span class="meta-text">
                <template v-if="getMappingPort(entry)">Port: {{ getMappingPort(entry) }}<br /></template>
                RDV: {{ rdv }}<template v-if="hasProxyConfig(getMappingProxy(entry))"> · {{ getMappingProxy(entry).Proxy_Type || 'proxy' }}</template>
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧结果 -->
      <div v-if="resultPanel" class="col-lg-7">
        <div class="card">
          <div class="card-header">
            <i class="bi bi-qr-code me-2" />
            扫码登录
          </div>
          <div class="card-body">
            <div class="step-indicator">
              <div
                v-for="i in 4"
                :key="i"
                class="step"
                :class="{
                  done: i < step,
                  active: i === step
                }"
              />
            </div>
            <div class="text-center text-muted mb-3" style="font-size: 13px">
              {{ stepText }}
            </div>

            <div class="qr-container">
              <img v-if="qrImgUrl" :src="qrImgUrl" alt="二维码" />
              <div v-else class="qr-placeholder">
                <i class="bi bi-qr-code" />
                <div>二维码准备中...</div>
              </div>
              <div class="scan-status" :class="scanStatus.cls">
                <i
                  v-if="scanStatus.cls === 'waiting'"
                  class="bi bi-hourglass-split me-1"
                />
                <i
                  v-else-if="scanStatus.cls === 'scanned'"
                  class="bi bi-phone me-1"
                />
                <i
                  v-else-if="scanStatus.cls === 'success'"
                  class="bi bi-check-circle-fill me-1"
                />
                <i v-else class="bi bi-x-circle-fill me-1" />
                {{ scanStatus.text }}
              </div>
              <div v-if="showScanned" class="user-scanned-info">
                <img :src="scannedInfo.avatar" alt="" />
                <div>
                  <div style="font-weight: 600; color: #1e293b">
                    {{ scannedInfo.nick }}
                  </div>
                  <div style="font-size: 12px; color: #94a3b8">
                    已扫码，等待确认登录
                  </div>
                </div>
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
            <div class="text-muted mb-3">
              <strong>{{ successInfo.nick || successInfo.wxid }}</strong><br />
              <span style="font-size: 13px">
                wxid: {{ successInfo.wxid }}
              </span>
            </div>
            <div class="text-muted" style="font-size: 12px">
              已保存到「已登录账号配置」列表，老号登录时可一键复用
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

.step-indicator {
  display: flex;
  gap: 8px;
  margin-bottom: 24px;
}
.step-indicator .step {
  flex: 1;
  height: 4px;
  border-radius: 4px;
  background: #e2e8f0;
  transition: 0.3s;
}
.step-indicator .step.done {
  background: var(--success);
}
.step-indicator .step.active {
  background: var(--primary);
}

.qr-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 16px 0;
}
.qr-container img {
  width: 240px;
  height: 240px;
  border-radius: 12px;
  border: 2px solid #e2e8f0;
  background: #fff;
}
.qr-placeholder {
  width: 240px;
  height: 240px;
  border-radius: 12px;
  border: 2px dashed #cbd5e1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #94a3b8;
  gap: 8px;
  i {
    font-size: 64px;
  }
}

.scan-status {
  margin-top: 16px;
  padding: 10px 20px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  text-align: center;
  display: inline-flex;
  align-items: center;
}
.scan-status.waiting {
  background: #fef3c7;
  color: #92400e;
}
.scan-status.scanned {
  background: #d1fae5;
  color: #065f46;
}
.scan-status.confirmed {
  background: #dbeafe;
  color: #1e40af;
}
.scan-status.success {
  background: #d1fae5;
  color: #065f46;
}
.scan-status.error {
  background: #fee2e2;
  color: #991b1b;
}

.user-scanned-info {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px;
  background: #f8fafc;
  border-radius: 10px;
  margin-top: 12px;
  width: 100%;
  max-width: 320px;
}
.user-scanned-info img {
  width: 48px;
  height: 48px;
  border-radius: 50%;
}

.proxy-section {
  border-top: 1px solid #f1f5f9;
  padding-top: 18px;
  margin-top: 8px;
}
.proxy-title {
  font-size: 13px;
  font-weight: 600;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 12px;
}
.account-config-item {
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
.account-config-item:hover {
  background: #e2e8f0;
  border-color: var(--primary);
}
.account-config-item .wxid-text {
  font-family: 'Consolas', monospace;
  font-size: 14px;
  color: #1e293b;
  font-weight: 600;
  word-break: break-all;
}
.account-config-item .meta-text {
  font-size: 12px;
  color: #94a3b8;
  margin-left: auto;
  text-align: right;
  line-height: 1.4;
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
</style>
