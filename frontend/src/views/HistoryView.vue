<template>
  <AppLayout>
    <div class="history-page">
      <!-- 页面头部 -->
      <div class="page-header">
        <div class="header-left">
          <el-icon :size="22" color="#6366f1"><Clock /></el-icon>
          <h2>检索历史</h2>
          <el-tag type="info" size="small">{{ pagination.total }} 条记录</el-tag>
        </div>
        <div class="header-right">
          <el-button
            type="danger"
            size="small"
            plain
            :icon="Delete"
            @click="handleClearAll"
            :loading="clearing"
          >
            清空全部
          </el-button>
        </div>
      </div>

      <!-- 筛选工具栏 -->
      <div class="filter-bar">
        <el-input
          v-model="filters.keyword"
          placeholder="搜索问题关键词..."
          clearable
          style="width: 280px"
          :prefix-icon="Search"
          @keydown.enter="handleSearch"
        >
          <template #append>
            <el-button :icon="Search" @click="handleSearch" />
          </template>
        </el-input>
        <el-select
          v-model="filters.decision"
          placeholder="检索决策"
          clearable
          style="width: 160px"
          @change="handleSearch"
        >
          <el-option label="全部" value="" />
          <el-option label="正常检索" value="proceed" />
          <el-option label="二次检索" value="retry" />
          <el-option label="降级回答" value="fallback" />
        </el-select>
        <el-button @click="resetFilters">重置</el-button>
      </div>

      <!-- 加载状态 -->
      <div v-loading="loading">
        <!-- 空状态 -->
        <el-empty
          v-if="!loading && records.length === 0"
          description="暂无检索历史"
          :image-size="80"
        />

        <!-- 历史记录列表 -->
        <div v-else class="records-list">
          <div
            v-for="record in records"
            :key="record.id"
            class="record-card"
            @click="openDetail(record)"
          >
            <!-- 卡片头部 -->
            <div class="card-header">
              <div class="question-text">{{ record.question }}</div>
              <div class="card-actions" @click.stop>
                <el-button
                  size="small"
                  text
                  :type="record.rating === 1 ? 'success' : 'default'"
                  :icon="record.rating === 1 ? 'Select' : 'Top'"
                  @click="rateRecord(record, 1)"
                  title="有用"
                />
                <el-button
                  size="small"
                  text
                  :type="record.rating === 0 ? 'danger' : 'default'"
                  :icon="record.rating === 0 ? 'Select' : 'Bottom'"
                  @click="rateRecord(record, 0)"
                  title="没用"
                />
                <el-popconfirm
                  title="确定删除此条记录?"
                  @confirm="deleteRecord(record.id)"
                >
                  <template #reference>
                    <el-button size="small" text type="danger" :icon="Delete" />
                  </template>
                </el-popconfirm>
              </div>
            </div>

            <!-- 卡片内容 -->
            <div class="card-body">
              <div class="answer-preview" v-if="record.answer">
                {{ truncate(record.answer, 120) }}
              </div>
            </div>

            <!-- 卡片底部 -->
            <div class="card-footer">
              <div class="card-meta">
                <!-- 检索决策标签 -->
                <el-tag
                  size="small"
                  :type="decisionTagType(record.retrieval_decision)"
                  effect="plain"
                >
                  {{ decisionLabel(record.retrieval_decision) }}
                </el-tag>
                <!-- 来源数量 -->
                <span class="meta-item">
                  <el-icon :size="12"><Document /></el-icon>
                  {{ record.context_count ?? 0 }} 个文档块
                </span>
                <!-- 响应耗时 -->
                <span class="meta-item" v-if="record.response_time_ms">
                  <el-icon :size="12"><Timer /></el-icon>
                  {{ record.response_time_ms }} ms
                </span>
              </div>
              <span class="card-time">{{ formatTime(record.created_at) }}</span>
            </div>
          </div>
        </div>

        <!-- 分页 -->
        <div class="pagination-wrap" v-if="pagination.total > 0">
          <el-pagination
            v-model:current-page="pagination.page"
            :page-size="pagination.pageSize"
            :total="pagination.total"
            layout="prev, pager, next, total"
            background
            @current-change="loadData"
          />
        </div>
      </div>

      <!-- 详情弹窗 -->
      <el-dialog
        v-model="detailVisible"
        :title="`检索详情 — ${currentRecord?.question?.slice(0, 40)}${currentRecord?.question?.length > 40 ? '...' : ''}`"
        width="780px"
        top="4vh"
        destroy-on-close
      >
        <div v-if="currentRecord" class="detail-content">
          <!-- 问题 -->
          <div class="detail-section">
            <div class="section-label">
              <el-icon><QuestionFilled /></el-icon> 用户问题
            </div>
            <div class="section-content question-box">{{ currentRecord.question }}</div>
          </div>

          <!-- 检索决策 -->
          <div class="detail-section">
            <div class="section-label">
              <el-icon><Connection /></el-icon> 检索决策
            </div>
            <div class="section-content">
              <el-tag
                size="small"
                :type="decisionTagType(currentRecord.retrieval_decision)"
                effect="dark"
              >
                {{ decisionLabel(currentRecord.retrieval_decision) }}
              </el-tag>
              <span class="decision-reason" v-if="currentRecord.decision_reason">
                {{ currentRecord.decision_reason }}
              </span>
            </div>
          </div>

          <!-- 检索结果 -->
          <div class="detail-section" v-if="currentRecord.search_results?.length">
            <div class="section-label">
              <el-icon><Document /></el-icon> 检索到的文档块
              <span class="section-count">({{ currentRecord.search_results.length }})</span>
            </div>
            <div class="search-results-list">
              <div
                v-for="(item, idx) in currentRecord.search_results"
                :key="idx"
                class="result-item"
              >
                <div class="result-header">
                  <el-tag size="small" type="info">
                    #{{ idx + 1 }}
                    {{ item.metadata?.title || item.metadata?.file_name || '未知来源' }}
                  </el-tag>
                  <span class="result-score">
                    RRF: {{ ((item.rrf_score || 0) * 100).toFixed(1) }}%
                    <span v-if="item.retrieval_type" class="retrieval-type">
                      ({{ item.retrieval_type === 'hybrid' ? '混合' : item.retrieval_type }})
                    </span>
                  </span>
                </div>
                <div class="result-body">{{ item.content }}</div>
              </div>
            </div>
          </div>

          <!-- 引用来源 -->
          <div class="detail-section" v-if="currentRecord.sources?.length">
            <div class="section-label">
              <el-icon><Link /></el-icon> 引用来源
            </div>
            <div class="sources-list">
              <div
                v-for="(src, idx) in currentRecord.sources"
                :key="idx"
                class="source-item"
              >
                <span class="source-title">{{ src.title }}</span>
                <span class="source-score">{{ ((src.score || 0) * 100).toFixed(1) }}%</span>
              </div>
            </div>
          </div>

          <!-- AI 回答 -->
          <div class="detail-section">
            <div class="section-label">
              <el-icon><ChatLineSquare /></el-icon> AI 回答
              <span class="section-meta">
                {{ currentRecord.response_time_ms }}ms
              </span>
            </div>
            <div class="section-content answer-box" v-html="renderMarkdown(currentRecord.answer || '')"></div>
          </div>
        </div>
      </el-dialog>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Clock, Search, Delete, Timer, Document,
  QuestionFilled, Connection, Link, ChatLineSquare,
} from '@element-plus/icons-vue'
import AppLayout from '@/components/common/AppLayout.vue'
import {
  getSearchHistoryList,
  getSearchHistoryDetail,
  deleteSearchHistory,
  clearSearchHistory,
} from '@/api/searchHistory.js'
import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'

const md = new MarkdownIt({
  html: false,
  linkify: true,
  highlight(code, lang) {
    if (lang && hljs.getLanguage(lang)) {
      return hljs.highlight(code, { language: lang }).value
    }
    return code
  },
})

function renderMarkdown(text) {
  if (!text) return ''
  return md.render(text)
}

const loading = ref(false)
const clearing = ref(false)
const records = ref([])
const pagination = reactive({
  page: 1,
  pageSize: 15,
  total: 0,
})
const filters = reactive({ keyword: '', decision: '' })

const detailVisible = ref(false)
const currentRecord = ref(null)

async function loadData() {
  loading.value = true
  try {
    const res = await getSearchHistoryList(
      pagination.page,
      pagination.pageSize,
      filters.keyword,
      filters.decision,
    )
    records.value = res.items || []
    pagination.total = res.total || 0
  } catch (_) {
    ElMessage.error('加载检索历史失败')
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  pagination.page = 1
  loadData()
}

function resetFilters() {
  filters.keyword = ''
  filters.decision = ''
  handleSearch()
}

async function deleteRecord(id) {
  try {
    await deleteSearchHistory(id)
    ElMessage.success('删除成功')
    loadData()
  } catch (_) {
    ElMessage.error('删除失败')
  }
}

async function handleClearAll() {
  try {
    await ElMessageBox.confirm('确定清空所有检索历史？此操作不可恢复。', '清空确认', {
      confirmButtonText: '确定清空',
      cancelButtonText: '取消',
      type: 'warning',
    })
    clearing.value = true
    await clearSearchHistory()
    ElMessage.success('已清空全部检索历史')
    loadData()
  } catch (_) {
    // 用户取消
  } finally {
    clearing.value = false
  }
}

async function openDetail(record) {
  try {
    const res = await getSearchHistoryDetail(record.id)
    currentRecord.value = res
    detailVisible.value = true
  } catch (_) {
    ElMessage.error('加载详情失败')
  }
}

async function rateRecord(record, rating) {
  // 前端乐观更新，实际 rating 功能可通过后端扩展
  if (record.rating === rating) {
    record.rating = null
  } else {
    record.rating = rating
  }
}

function truncate(text, maxLen) {
  if (!text) return ''
  return text.length > maxLen ? text.slice(0, maxLen) + '...' : text
}

function formatTime(isoStr) {
  if (!isoStr) return ''
  const d = new Date(isoStr)
  const now = new Date()
  const diff = now - d
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)} 分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小时前`
  return d.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

function decisionLabel(decision) {
  const map = { proceed: '正常检索', retry: '二次检索', fallback: '降级回答' }
  return map[decision] || decision || '未知'
}

function decisionTagType(decision) {
  const map = { proceed: 'success', retry: 'warning', fallback: 'danger' }
  return map[decision] || 'info'
}

onMounted(loadData)
</script>

<style scoped>
.history-page {
  padding: 28px 36px;
  height: 100%;
  overflow-y: auto;
  background: #f8fafc;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.header-left h2 {
  font-size: 20px;
  font-weight: 600;
  color: #1e293b;
  margin: 0;
}

.filter-bar {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 20px;
  background: #fff;
  padding: 16px;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
}

.records-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.record-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 16px 20px;
  cursor: pointer;
  transition: all 0.2s;
}

.record-card:hover {
  border-color: #6366f1;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.1);
  transform: translateY(-1px);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 10px;
}

.question-text {
  font-size: 14px;
  font-weight: 500;
  color: #1e293b;
  flex: 1;
  line-height: 1.5;
}

.card-actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}

.card-body { margin-bottom: 10px; }

.answer-preview {
  font-size: 13px;
  color: #64748b;
  line-height: 1.6;
  background: #f8fafc;
  padding: 8px 12px;
  border-radius: 6px;
  border-left: 3px solid #6366f1;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-meta {
  display: flex;
  gap: 12px;
  align-items: center;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #94a3b8;
}

.card-time {
  font-size: 12px;
  color: #94a3b8;
}

.pagination-wrap {
  display: flex;
  justify-content: center;
  margin-top: 24px;
}

/* ===== 详情弹窗 ===== */
.detail-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
  max-height: 70vh;
  overflow-y: auto;
}

.detail-section { }

.section-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: #374151;
  margin-bottom: 10px;
}

.section-count {
  font-weight: 400;
  color: #94a3b8;
  font-size: 12px;
}

.section-meta {
  font-weight: 400;
  color: #94a3b8;
  font-size: 12px;
  margin-left: 8px;
}

.section-content {
  font-size: 14px;
  color: #475569;
  line-height: 1.7;
}

.question-box {
  background: #f8fafc;
  border-left: 3px solid #6366f1;
  padding: 10px 14px;
  border-radius: 0 6px 6px 0;
  font-weight: 500;
  color: #1e293b;
}

.decision-reason {
  margin-left: 12px;
  font-size: 13px;
  color: #64748b;
  font-style: italic;
}

.answer-box {
  background: #f8fafc;
  padding: 14px;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}

/* 检索结果列表 */
.search-results-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.result-item {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 12px 14px;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.result-score {
  font-size: 12px;
  color: #6366f1;
  font-weight: 500;
}

.retrieval-type {
  color: #94a3b8;
  font-weight: 400;
}

.result-body {
  font-size: 13px;
  color: #475569;
  line-height: 1.6;
  max-height: 80px;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 引用来源 */
.sources-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.source-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 12px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  font-size: 13px;
}

.source-title { color: #475569; }
.source-score { color: #6366f1; font-weight: 500; font-size: 12px; }
</style>
