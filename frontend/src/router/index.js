import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: { public: true }
  },
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    children: [
      { path: '', redirect: '/shanghao' },
      {
        path: 'shanghao',
        name: 'shanghao',
        component: () => import('@/views/ShanghaoView.vue')
      },
      {
        path: 'oldlogin',
        name: 'oldlogin',
        component: () => import('@/views/OldLoginView.vue')
      },
      {
        path: 'accounts',
        name: 'accounts',
        component: () => import('@/views/AccountsView.vue')
      },
      {
        path: 'accounts/:port',
        name: 'account-detail',
        component: () => import('@/views/AccountDetailView.vue'),
        props: true
      },
      {
        path: 'tools',
        redirect: '/tools/newsendmsg'
      },
      {
        path: 'tools/newsendmsg',
        name: 'tools-newsendmsg',
        component: () => import('@/views/ToolsView.vue')
      }
    ]
  },
  { path: '/:pathMatch(.*)*', redirect: '/shanghao' }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (!auth.loggedIn) {
    await auth.fetchSession()
  }
  if (!to.meta.public && !auth.loggedIn) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.name === 'login' && auth.loggedIn) {
    return { name: 'shanghao' }
  }
})

export default router
