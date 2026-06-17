<script setup>
import { reactive, ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '@/utils/api'

const route = useRoute()
const router = useRouter()

const form = reactive({
  port: localStorage.getItem('tools_port') || '30004',
  session_id: localStorage.getItem('tools_session_id') || '',
  userName: localStorage.getItem('tools_userName') || 'filehelper',
  content: localStorage.getItem('tools_content') || '我用PC微信给你发送了一条消息',
  msgType: parseInt(localStorage.getItem('tools_msgType') || '1', 10)
})

const submitting = ref(false)
const lastError = ref('')
const lastResponse = ref(null)
const lastSuccess = ref(false)

function persist() {
  localStorage.setItem('tools_port', form.port)
  localStorage.setItem('tools_session_id', form.session_id)
  localStorage.setItem('tools_userName', form.userName)
  localStorage.setItem('tools_content', form.content)
  localStorage.setItem('tools_msgType', String(form.msgType))
}

const sessionPreview = computed(() => {
  if (!form.session_id) return '未填写 session_id'
  if (form.session_id.length <= 12) return form.session_id
  return form.session_id.slice(0, 6) + '…' + form.session_id.slice(-4)
})

const requestPreview = computed(() => {
  const port = parseInt(form.port, 10) || 0
  return {
    method: 'POST',
    url: `http://{{host}}:${port || '{port}'}/newsendmsg`,
    body: {
      session_id: form.session_id,
      userName: form.userName,
      content: form.content,
      msgType: form.msgType
    }
  }
})

async function send() {
  lastError.value = ''
  lastResponse.value = null
  lastSuccess.value = false
  const port = parseInt(form.port, 10)
  if (!port) {
    lastError.value = '请填写正确的 port'
    return
  }
  if (!form.session_id) {
    lastError.value = '请填写 session_id'
    return
  }
  if (!form.userName) {
    lastError.value = '请填写 userName'
    return
  }
  if (!form.content) {
    lastError.value = '请填写 content'
    return
  }
  persist()
  submitting.value = true
  try {
    const r = await api.post('/newsendmsg', {
      port,
      session_id: form.session_id,
      userName: form.userName,
      content: form.content,
      msgType: form.msgType
    })
    lastResponse.value = r.data
    lastSuccess.value = r.data?.ok === true || (!r.data?.error && r.status === 200)
  } catch (e) {
    lastError.value = e?.response?.data?.error || e.message || '请求失败'
    lastResponse.value = e?.response?.data || null
  } finally {
    submitting.value = false
  }
}

function fillFromQuery() {
  const q = route.query
  if (q.port) form.port = String(q.port)
  if (q.session_id) form.session_id = String(q.session_id)
  if (q.userName) form.userName = String(q.userName)
  if (q.content) form.content = String(q.content)
  if (q.msgType) form.msgType = parseInt(String(q.msgType), 10) || 1
}

onMounted(() => {
  fillFromQuery()
})
</script>

<template>
  <div>
    <div class="page-header">
      <h2>
        <i class="bi bi-send" style="color: var(--primary)" />
        通用测试 / newsendmsg
      </h2>
    </div>

    <div class="row g-4">
      <!-- 左侧表单 -->
      <div class="col-lg-5">
        <div class="card">
          <div class="card-header">
            <i class="bi bi-gear me-2" />
            请求参数
          </div>
          <div class="card-body">
            <form @submit.prevent="send">
              <div class="mb-3">
                <label class="form-label">
                  实例 Port <span class="text-danger">*</span>
                </label>
                <input
                  v-model="form.port"
                  type="number"
                  class="form-control"
                  placeholder="如 30004"
                  required
                />
                <div class="form-hint">newsendmsg 走实例端口（不是 mgr 端口 29999）</div>
              </div>
              <div class="mb-3">
                <label class="form-label">
                  session_id <span class="text-danger">*</span>
                </label>
                <input
                  v-model="form.session_id"
                  type="text"
                  class="form-control"
                  placeholder="从 GetSessionList 获取的 session_id"
                  required
                />
                <div class="form-hint">当前: <span class="mono">{{ sessionPreview }}</span></div>
              </div>
              <div class="mb-3">
                <label class="form-label">
                  userName <span class="text-danger">*</span>
                </label>
                <input
                  v-model="form.userName"
                  type="text"
                  class="form-control"
                  placeholder="filehelper / wxid_xxx / 群 ID ..."
                  required
                />
              </div>
              <div class="mb-3">
                <label class="form-label">
                  content <span class="text-danger">*</span>
                </label>
                <textarea
                  v-model="form.content"
                  class="form-control"
                  rows="4"
                  placeholder="要发送的内容"
                  required
                />
              </div>
              <div class="mb-3">
                <label class="form-label">msgType</label>
                <select v-model.number="form.msgType" class="form-select">
                  <option :value="1">1 - 文本</option>
                  <option :value="2">2 - 图片</option>
                  <option :value="3">3 - 语音</option>
                  <option :value="4">4 - 视频</option>
                  <option :value="5">5 - 文件</option>
                </select>
              </div>

              <button
                type="submit"
                class="btn btn-primary w-100"
                :disabled="submitting"
              >
                <i class="bi bi-send me-1" />
                {{ submitting ? '发送中...' : '发送请求' }}
              </button>
            </form>
          </div>
        </div>
      </div>

      <!-- 右侧预览 / 结果 -->
      <div class="col-lg-7">
        <div class="card">
          <div class="card-header">
            <i class="bi bi-eye me-2" />
            请求预览
          </div>
          <div class="card-body">
            <div class="kv-row">
              <span class="kv-label">Method</span>
              <span class="kv-value mono">{{ requestPreview.method }}</span>
            </div>
            <div class="kv-row">
              <span class="kv-label">URL</span>
              <span class="kv-value mono">{{ requestPreview.url }}</span>
            </div>
            <div class="kv-row block">
              <span class="kv-label">Body</span>
              <pre class="kv-pre mono">{{ JSON.stringify(requestPreview.body, null, 2) }}</pre>
            </div>
          </div>
        </div>

        <div class="card mt-4">
          <div class="card-header">
            <i class="bi bi-terminal me-2" />
            响应
          </div>
          <div class="card-body">
            <div v-if="submitting" class="status-badge status-waiting">
              <i class="bi bi-hourglass-split" /> 正在请求 ...
            </div>
            <div v-else-if="lastError" class="alert-error">
              <i class="bi bi-exclamation-triangle me-1" />{{ lastError }}
            </div>
            <div v-else-if="lastSuccess" class="status-badge status-success">
              <i class="bi bi-check2-circle" /> 请求成功
            </div>
            <div v-else class="text-muted" style="font-size: 13px">
              <i class="bi bi-info-circle me-1" /> 还没发送过请求
            </div>

            <details v-if="lastResponse" class="raw-details" open>
              <summary>原始响应</summary>
              <pre class="mono">{{ JSON.stringify(lastResponse, null, 2) }}</pre>
            </details>
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

.form-hint {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 4px;
}

.mono {
  font-family: 'Consolas', monospace;
}

.kv-row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px dashed #e2e8f0;
  font-size: 13px;
}
.kv-row:last-child { border-bottom: 0; }
.kv-row.block { flex-direction: column; }
.kv-label {
  flex: 0 0 80px;
  color: #94a3b8;
  font-size: 12px;
}
.kv-value {
  color: #1e293b;
  word-break: break-all;
}
.kv-pre {
  background: #0f172a;
  color: #e2e8f0;
  padding: 12px;
  border-radius: 8px;
  font-size: 12px;
  max-height: 220px;
  overflow: auto;
  margin: 0;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 12px;
}
.status-waiting { background: #fef3c7; color: #92400e; }
.status-success { background: #d1fae5; color: #065f46; }
.alert-error {
  background: #fee2e2;
  color: #991b1b;
  padding: 10px 12px;
  border-radius: 8px;
  font-size: 13px;
  margin-bottom: 12px;
}

.raw-details {
  margin-top: 12px;
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
  max-height: 320px;
  overflow: auto;
  margin-top: 8px;
}
</style>
