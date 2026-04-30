<template>
  <div class="app-layout">
    <!-- 侧边栏 -->
    <aside class="app-sidebar">
      <div class="sidebar-header">
        <div class="logo-area">
          <el-icon :size="28" color="#3b82f6"><View /></el-icon>
          <div class="logo-text">
            <span class="logo-title">EyeRAG</span>
            <span class="logo-subtitle">眼科智能问答</span>
          </div>
        </div>
      </div>

      <nav class="sidebar-nav">
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="nav-item"
          :class="{ active: $route.path === item.path }"
        >
          <el-icon :size="18"><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </router-link>
      </nav>

      <div class="sidebar-footer">
        <div v-if="userInfo" class="user-info">
          <el-icon :size="16"><UserFilled /></el-icon>
          <span class="user-name">{{ userInfo.username }}</span>
          <el-icon class="logout-btn" :size="14" @click="handleLogout" title="退出登录">
            <SwitchButton />
          </el-icon>
        </div>
        <div class="version-badge">
          <el-icon :size="14"><InfoFilled /></el-icon>
          <span>V1.0.0</span>
        </div>
      </div>
    </aside>

    <!-- 主内容区 -->
    <main class="app-main">
      <slot />
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import {
  ChatLineSquare, Collection, InfoFilled, View,
  UserFilled, SwitchButton, Star, DataAnalysis, Clock,
  Setting, Monitor,
} from '@element-plus/icons-vue'
import { getUserInfo, clearAuth } from '@/api/auth.js'

const router = useRouter()

const navItems = computed(() => {
  const base = [
    { path: '/chat',      label: '智能问答',   icon: ChatLineSquare },
    { path: '/knowledge', label: '知识库管理', icon: Collection },
    { path: '/history',   label: '检索历史',   icon: Clock },
    { path: '/favorites', label: '我的收藏',   icon: Star },
    { path: '/stats',     label: '数据看板',   icon: DataAnalysis },
    { path: '/system',    label: '系统介绍',   icon: Monitor },
  ]
  if (userInfo.value?.role === 'admin') {
    base.push({ path: '/admin', label: '管理后台', icon: Setting })
  }
  return base
})

const userInfo = computed(() => getUserInfo())

function handleLogout() {
  clearAuth()
  router.push('/login')
}
</script>

<style scoped>
.app-layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

.app-sidebar {
  width: var(--sidebar-width, 148px);
  min-width: var(--sidebar-width, 148px);
  height: 100vh;
  background: #0f172a;
  color: #e2e8f0;
  display: flex;
  flex-direction: column;
  border-right: 1px solid rgba(255, 255, 255, 0.05);
}

.sidebar-header {
  padding: 18px 14px 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.logo-area {
  display: flex;
  align-items: center;
  gap: 10px;
}

.logo-text { display: flex; flex-direction: column; }

.logo-title {
  font-size: 16px;
  font-weight: 700;
  color: #f1f5f9;
  letter-spacing: -0.2px;
}

.logo-subtitle {
  font-size: 10px;
  color: #64748b;
  margin-top: 1px;
}

.sidebar-nav {
  flex: 1;
  padding: 10px 8px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 9px 12px;
  border-radius: 7px;
  color: #64748b;
  font-size: 13px;
  transition: all 0.15s;
  cursor: pointer;
  text-decoration: none;
  position: relative;
}

.nav-item:hover {
  color: #cbd5e1;
  background: rgba(255, 255, 255, 0.05);
}

.nav-item.active {
  color: #93c5fd;
  background: rgba(59, 130, 246, 0.12);
  font-weight: 500;
}

.nav-item.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 18px;
  background: #3b82f6;
  border-radius: 0 2px 2px 0;
}

.sidebar-footer {
  padding: 10px 14px 14px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.user-info {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 12px;
  color: #94a3b8;
  margin-bottom: 8px;
  padding: 5px 0;
}

.user-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.logout-btn {
  cursor: pointer;
  color: #475569;
  transition: color 0.15s;
}

.logout-btn:hover { color: #ef4444; }

.version-badge {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  color: #334155;
}

.app-main {
  flex: 1;
  overflow-y: auto;
  background: var(--color-bg-secondary, #f8fafc);
}
</style>
