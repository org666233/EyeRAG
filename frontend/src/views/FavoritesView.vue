<template>
  <AppLayout>
    <div class="favorites-page">
      <div class="page-header">
        <div class="header-left">
          <el-icon :size="24" color="#f59e0b"><Star /></el-icon>
          <h2>我的收藏</h2>
          <el-tag type="warning" size="small">{{ favorites.length }} 条</el-tag>
        </div>
        <el-input
          v-model="searchText"
          placeholder="搜索收藏内容..."
          class="search-input"
          clearable
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
      </div>

      <!-- 空状态 -->
      <div v-if="filteredFavorites.length === 0 && !loading" class="empty-state">
        <el-empty description="暂无收藏内容">
          <template #description>
            <p>在聊天界面点击 ⭐ 即可收藏 AI 回答</p>
          </template>
          <el-button type="primary" @click="$router.push('/chat')">去问答</el-button>
        </el-empty>
      </div>

      <!-- 收藏列表 -->
      <div v-else class="favorites-list" v-loading="loading">
        <div
          v-for="fav in filteredFavorites"
          :key="fav.id"
          class="fav-card"
        >
          <div class="fav-question">
            <el-icon color="#3b82f6"><QuestionFilled /></el-icon>
            <span>{{ fav.question || '（问题未记录）' }}</span>
          </div>
          <div class="fav-answer" v-html="renderMarkdown(fav.answer)"></div>

          <!-- 来源标签 -->
          <div v-if="fav.sources && fav.sources.length" class="fav-sources">
            <el-tag
              v-for="(src, i) in fav.sources"
              :key="i"
              size="small"
              type="info"
              effect="plain"
            >
              📄 {{ src.title }}
            </el-tag>
          </div>

          <div class="fav-footer">
            <span class="fav-time">{{ formatTime(fav.created_at) }}</span>
            <div class="fav-actions">
              <el-button size="small" text @click="copyAnswer(fav.answer)">
                <el-icon><CopyDocument /></el-icon> 复制
              </el-button>
              <el-button size="small" text type="primary" @click="goChat(fav.question)">
                <el-icon><ChatLineSquare /></el-icon> 继续追问
              </el-button>
              <el-button size="small" text type="danger" @click="handleRemove(fav)">
                <el-icon><Delete /></el-icon> 取消收藏
              </el-button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Star, Search, QuestionFilled, CopyDocument, ChatLineSquare, Delete } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import MarkdownIt from 'markdown-it'
import AppLayout from '@/components/common/AppLayout.vue'
import { listFavorites, removeFavorite } from '@/api/favorites.js'

const router = useRouter()
const favorites = ref([])
const loading = ref(false)
const searchText = ref('')

const md = new MarkdownIt({ html: false, linkify: true })
function renderMarkdown(text) {
  return text ? md.render(text) : ''
}

const filteredFavorites = computed(() => {
  if (!searchText.value.trim()) return favorites.value
  const kw = searchText.value.toLowerCase()
  return favorites.value.filter(
    f => f.question?.toLowerCase().includes(kw) || f.answer?.toLowerCase().includes(kw)
  )
})

function formatTime(isoStr) {
  if (!isoStr) return ''
  return new Date(isoStr).toLocaleString('zh-CN', {
    month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit',
  })
}

async function loadFavorites() {
  loading.value = true
  try {
    favorites.value = await listFavorites()
  } catch (_) {
    ElMessage.error('加载收藏失败')
  } finally {
    loading.value = false
  }
}

async function handleRemove(fav) {
  try {
    await removeFavorite(fav.id)
    favorites.value = favorites.value.filter(f => f.id !== fav.id)
    ElMessage.success('已取消收藏')
  } catch (_) {
    ElMessage.error('操作失败')
  }
}

function copyAnswer(text) {
  navigator.clipboard.writeText(text).then(() => {
    ElMessage.success('已复制到剪贴板')
  })
}

function goChat(question) {
  router.push({ path: '/chat', query: { q: question } })
}

onMounted(loadFavorites)
</script>

<style scoped>
.favorites-page {
  padding: 28px 36px;
  height: 100%;
  overflow-y: auto;
  background: #f8fafc;
}

.page-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.header-left h2 {
  font-size: 20px;
  font-weight: 600;
  color: #1e293b;
  margin: 0;
}

.search-input {
  max-width: 280px;
  margin-left: auto;
}

.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 60vh;
}

.favorites-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-width: 860px;
}

.fav-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 20px;
  transition: box-shadow 0.2s;
}

.fav-card:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
}

.fav-question {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 12px;
}

.fav-answer {
  font-size: 14px;
  color: #334155;
  line-height: 1.8;
  max-height: 200px;
  overflow: hidden;
  mask-image: linear-gradient(to bottom, black 80%, transparent 100%);
  margin-bottom: 10px;
}

.fav-answer :deep(p) { margin: 0 0 6px; }
.fav-answer :deep(ul), .fav-answer :deep(ol) { padding-left: 18px; margin: 4px 0; }
.fav-answer :deep(strong) { color: #0f172a; }

.fav-sources {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 12px;
}

.fav-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 12px;
  border-top: 1px solid #f1f5f9;
}

.fav-time {
  font-size: 12px;
  color: #94a3b8;
}

.fav-actions {
  display: flex;
  gap: 4px;
}
</style>
