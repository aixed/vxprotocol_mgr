<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const openGroups = ref({
  protocol: route.path.startsWith('/shanghao') || route.path.startsWith('/oldlogin'),
  accounts: route.path.startsWith('/accounts'),
  tools: route.path.startsWith('/tools')
})

function toggleGroup(key) {
  openGroups.value[key] = !openGroups.value[key]
}

function isActive(name) {
  return route.name === name
}

function isGroupActive(paths) {
  return paths.some((p) => route.path.startsWith(p))
}

async function doLogout() {
  await auth.logout()
  router.replace({ name: 'login' })
}
</script>

<template>
  <div class="app-shell">
    <aside class="sidebar">
      <div class="sidebar-brand">
        <i class="bi bi-grid-fill" />
        <span>管理后台</span>
      </div>

      <nav class="sidebar-nav">
        <!-- 协议上号 -->
        <button
          type="button"
          class="sidebar-group-toggle"
          :class="{ active: isGroupActive(['/shanghao', '/oldlogin']) }"
          :aria-expanded="openGroups.protocol"
          @click="toggleGroup('protocol')"
        >
          <i class="bi bi-qr-code-scan" />
          <span>协议上号</span>
          <i class="bi bi-chevron-right chevron" />
        </button>
        <div class="sidebar-subnav" :class="{ open: openGroups.protocol }">
          <RouterLink
            to="/shanghao"
            class="sub-link"
            :class="{ active: isActive('shanghao') }"
          >
            <i class="bi bi-qr-code-scan" />
            <span>协议上号</span>
          </RouterLink>
          <RouterLink
            to="/oldlogin"
            class="sub-link"
            :class="{ active: isActive('oldlogin') }"
          >
            <i class="bi bi-person-badge" />
            <span>老号登录</span>
          </RouterLink>
        </div>

        <!-- 账号管理 -->
        <RouterLink
          to="/accounts"
          class="sidebar-link"
          :class="{ active: isGroupActive(['/accounts']) }"
        >
          <i class="bi bi-people-fill" />
          <span>账号管理</span>
        </RouterLink>

        <!-- 通用测试 -->
        <button
          type="button"
          class="sidebar-group-toggle"
          :class="{ active: isGroupActive(['/tools']) }"
          :aria-expanded="openGroups.tools"
          @click="toggleGroup('tools')"
        >
          <i class="bi bi-tools" />
          <span>通用测试</span>
          <i class="bi bi-chevron-right chevron" />
        </button>
        <div class="sidebar-subnav" :class="{ open: openGroups.tools }">
          <RouterLink
            to="/tools/newsendmsg"
            class="sub-link"
            :class="{ active: isActive('tools-newsendmsg') }"
          >
            <i class="bi bi-send" />
            <span>newsendmsg</span>
          </RouterLink>
        </div>
      </nav>

      <div class="sidebar-bottom">
        <a href="javascript:void(0)" @click="doLogout">
          <i class="bi bi-box-arrow-left" />
          <span>退出登录</span>
        </a>
      </div>
    </aside>

    <main class="main-content">
      <RouterView />
    </main>
  </div>
</template>

<style lang="scss" scoped>
.app-shell {
  min-height: 100vh;
}

.sidebar {
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  width: 220px;
  background: var(--sidebar-bg);
  color: var(--sidebar-text);
  display: flex;
  flex-direction: column;
  z-index: 100;
}

.sidebar-brand {
  padding: 24px 20px 20px;
  font-size: 18px;
  font-weight: 700;
  color: #fff;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  display: flex;
  align-items: center;
  gap: 10px;
}

.sidebar-brand i {
  font-size: 22px;
  color: var(--primary);
}

.sidebar-nav {
  flex: 1;
  padding: 12px 0;
  overflow-y: auto;
}

.sidebar-group-toggle {
  width: 100%;
  border: 0;
  background: transparent;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 20px;
  color: var(--sidebar-text);
  font-size: 14px;
  transition: 0.15s;
  text-align: left;
  cursor: pointer;
}

.sidebar-group-toggle:hover,
.sidebar-group-toggle.active {
  background: rgba(255, 255, 255, 0.06);
  color: #fff;
}

.sidebar-group-toggle.active {
  border-right: 3px solid var(--primary);
}

.sidebar-group-toggle i {
  font-size: 18px;
  width: 22px;
  text-align: center;
}

.sidebar-group-toggle .chevron {
  margin-left: auto;
  width: auto;
  font-size: 12px;
  transition: transform 0.15s;
}

.sidebar-group-toggle[aria-expanded='true'] .chevron {
  transform: rotate(90deg);
}

.sidebar-subnav {
  display: none;
  &.open {
    display: block;
  }
}

.sidebar-nav a {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 20px;
  color: var(--sidebar-text);
  text-decoration: none;
  font-size: 14px;
  transition: 0.15s;
}

.sidebar-nav a.sidebar-link {
  width: 100%;
  background: transparent;
  border: 0;
  text-align: left;
  cursor: pointer;
}

.sidebar-nav a:hover,
.sidebar-nav a.active {
  background: rgba(255, 255, 255, 0.06);
  color: #fff;
}

.sidebar-nav a.active {
  border-right: 3px solid var(--primary);
}

.sidebar-nav a i {
  font-size: 18px;
  width: 22px;
  text-align: center;
}

.sidebar-nav a.sub-link {
  padding-left: 52px;
  font-size: 13px;
}

.sidebar-nav a.sub-link i {
  font-size: 16px;
}

.sidebar-bottom {
  padding: 16px 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.sidebar-bottom a {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--sidebar-text);
  text-decoration: none;
  font-size: 13px;
  cursor: pointer;
}

.sidebar-bottom a:hover {
  color: #f87171;
}

.main-content {
  margin-left: 220px;
  padding: 32px 36px;
  min-height: 100vh;
}

@media (max-width: 768px) {
  .sidebar {
    width: 60px;
  }
  .sidebar-brand span,
  .sidebar-nav a span,
  .sidebar-group-toggle span,
  .sidebar-group-toggle .chevron,
  .sidebar-bottom span {
    display: none;
  }
  .sidebar-brand {
    padding: 18px 12px;
    justify-content: center;
  }
  .sidebar-nav a {
    justify-content: center;
    padding: 14px 0;
  }
  .sidebar-group-toggle {
    justify-content: center;
    padding: 14px 0;
  }
  .main-content {
    margin-left: 60px;
    padding: 20px 16px;
  }
}
</style>
