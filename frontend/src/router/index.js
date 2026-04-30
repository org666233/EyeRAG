import { createRouter, createWebHistory } from 'vue-router'
import { getToken, getUserInfo } from '@/api/auth.js'

const routes = [
  {
    path: '/',
    redirect: '/login',
  },
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: { requiresAuth: false, title: '登录' },
  },
  {
    path: '/chat',
    name: 'chat',
    component: () => import('@/views/ChatView.vue'),
    meta: { requiresAuth: true, title: '智能问答' },
  },
  {
    path: '/knowledge',
    name: 'knowledge',
    component: () => import('@/views/KnowledgeView.vue'),
    meta: { requiresAuth: true, title: '知识库管理' },
  },
  {
    path: '/favorites',
    name: 'favorites',
    component: () => import('@/views/FavoritesView.vue'),
    meta: { requiresAuth: true, title: '我的收藏' },
  },
  {
    path: '/stats',
    name: 'stats',
    component: () => import('@/views/StatsView.vue'),
    meta: { requiresAuth: true, title: '数据看板' },
  },
  {
    path: '/history',
    name: 'history',
    component: () => import('@/views/HistoryView.vue'),
    meta: { requiresAuth: true, title: '检索历史' },
  },
  {
    path: '/admin',
    name: 'admin',
    component: () => import('@/views/AdminView.vue'),
    meta: { requiresAuth: true, requiresAdmin: true, title: '管理后台' },
  },
  {
    path: '/system',
    name: 'system',
    component: () => import('@/views/SystemView.vue'),
    meta: { requiresAuth: true, title: '系统介绍' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 路由守卫 - 登录验证
router.beforeEach((to, _from, next) => {
  document.title = `${to.meta.title || '眼科问答'} - 眼科医疗知识问答系统`

  const token = getToken()

  if (to.meta.requiresAuth && !token) {
    next({ name: 'login', query: { redirect: to.fullPath } })
  } else if (to.meta.requiresAdmin && getUserInfo()?.role !== 'admin') {
    next({ name: 'chat' })
  } else if (to.name === 'login' && token) {
    next({ name: 'chat' })
  } else {
    next()
  }
})

export default router
