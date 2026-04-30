<template>
  <AppLayout>
    <div class="knowledge-view">
      <!-- 页面头部 -->
      <div class="page-header">
        <div class="header-info">
          <h1>知识库管理</h1>
          <p>管理眼科医疗知识文档，支持上传、删除、预览和下载</p>
        </div>
        <el-button type="primary" :icon="Upload" @click="showUpload = true">
          上传文档
        </el-button>
      </div>

      <!-- 统计卡片 -->
      <div class="stats-row">
        <div class="stat-card">
          <div class="stat-value">{{ stats.total_documents || 0 }}</div>
          <div class="stat-label">文档总数</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ stats.total_chunks || 0 }}</div>
          <div class="stat-label">向量块数</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ stats.collection_name || '-' }}</div>
          <div class="stat-label">向量集合名称</div>
        </div>
      </div>

      <!-- 搜索测试 -->
      <div class="search-section">
        <h3>🔍 检索测试</h3>
        <div class="search-bar">
          <el-input
            v-model="searchQuery"
            placeholder="输入检索测试查询，如：什么是青光眼？"
            @keydown.enter="doSearch"
            clearable
          >
            <template #append>
              <el-button :icon="Search" @click="doSearch" :loading="searching">
                检索
              </el-button>
            </template>
          </el-input>
        </div>
        <div v-if="searchResults.length > 0" class="search-results">
          <div v-for="(r, i) in searchResults" :key="i" class="result-item">
            <div class="result-header">
              <el-tag size="small" type="primary">{{ (r.score * 100).toFixed(1) }}%</el-tag>
              <span class="result-source">{{ r.metadata?.title || r.metadata?.file_name }}</span>
            </div>
            <div class="result-content">{{ r.content }}</div>
          </div>
        </div>
      </div>

      <!-- 文档列表 -->
      <div class="docs-section">
        <h3>📚 已入库文档 ({{ documents.length }})</h3>
        <el-table :data="documents" stripe style="width: 100%" v-loading="loadingDocs">
          <el-table-column prop="file_name" label="文件名" min-width="220" />
          <el-table-column prop="file_type" label="类型" width="80" align="center">
            <template #default="{ row }">
              <el-tag size="small">{{ row.file_type }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="source_name" label="来源" width="120" />
          <el-table-column prop="chunk_count" label="块数" width="70" align="center" sortable />
          <el-table-column prop="hit_count" label="命中次数" width="100" align="center" sortable>
            <template #default="{ row }">
              <span class="stat-num">{{ row.hit_count ?? 0 }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="view_count" label="浏览次数" width="100" align="center" sortable>
            <template #default="{ row }">
              <span class="stat-num">{{ row.view_count ?? 0 }}</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="210" align="center">
            <template #default="{ row }">
              <div style="display:flex;align-items:center;justify-content:center;flex-wrap:nowrap;gap:2px;">
                <el-button size="small" text type="primary" :icon="View" @click="previewDocument(row)">预览</el-button>
                <el-button size="small" text :icon="Download" @click="handleDownload(row.file_name)">下载</el-button>
                <el-popconfirm title="确定删除此文档?" @confirm="removeDoc(row.file_name)">
                  <template #reference>
                    <el-button type="danger" size="small" text :icon="Delete">删除</el-button>
                  </template>
                </el-popconfirm>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- 上传对话框 -->
      <el-dialog v-model="showUpload" title="上传文档" width="500px">
        <el-upload
          ref="uploadRef"
          drag
          action="/api/knowledge/upload"
          :on-success="onUploadSuccess"
          :on-error="onUploadError"
          accept=".pdf,.txt,.md,.markdown"
          :limit="5"
        >
          <el-icon class="el-icon--upload"><Upload /></el-icon>
          <div class="el-upload__text">拖拽文件到此处，或 <em>点击上传</em></div>
          <template #tip>
            <div class="el-upload__tip">支持 PDF/TXT/Markdown 格式，单次最多5个文件</div>
          </template>
        </el-upload>
      </el-dialog>

      <!-- 文档预览对话框 -->
      <el-dialog
        v-model="previewVisible"
        :title="`📖 ${previewData?.file_name || ''}`"
        width="820px"
        top="4vh"
        destroy-on-close
        :body-style="{ maxHeight: '74vh', overflowY: 'auto', padding: '20px' }"
      >
        <div v-if="previewData" class="preview-content">
          <!-- 文档统计 -->
          <div class="preview-stats">
            <div class="pstat">
              <span class="pstat-label">文本块</span>
              <span class="pstat-value">{{ previewData.chunk_count }}</span>
            </div>
            <div class="pstat">
              <span class="pstat-label">总字符数</span>
              <span class="pstat-value">{{ previewData.total_chars?.toLocaleString() }}</span>
            </div>
            <div class="pstat">
              <span class="pstat-label">浏览次数</span>
              <span class="pstat-value">{{ previewData.view_count }}</span>
            </div>
            <div class="pstat">
              <span class="pstat-label">来源</span>
              <span class="pstat-value">{{ previewData.source_name || '-' }}</span>
            </div>
          </div>

          <!-- 文本块列表 -->
          <div style="font-size:12px;color:#94a3b8;margin-bottom:8px;">
            共 {{ previewData.chunks?.length ?? 0 }} 个文本块
          </div>
          <div style="display:flex;flex-direction:column;gap:10px;">
            <div
              v-for="chunk in previewData.chunks"
              :key="chunk.chunk_index"
              style="border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;"
            >
              <div style="display:flex;justify-content:space-between;align-items:center;padding:7px 14px;background:#f8fafc;border-bottom:1px solid #e2e8f0;">
                <el-tag size="small" type="info">块 #{{ chunk.chunk_index }}</el-tag>
                <span style="font-size:12px;color:#94a3b8;">{{ chunk.content?.length ?? 0 }} 字</span>
              </div>
              <!-- v-text 直接设置 textContent，绕过 Vue 模板插值，避免英文文档中的 {{ }} wikitext 被错误解析 -->
              <div
                v-text="chunk.content || '（空）'"
                style="margin:0;padding:12px 14px;font-size:13px;color:#1e293b;line-height:1.8;white-space:pre-wrap;word-break:break-word;background:#fff;"
              ></div>
            </div>
          </div>
        </div>
        <template #footer>
          <el-button @click="previewVisible = false">关闭</el-button>
          <el-button
            type="primary"
            :icon="Download"
            @click="handleDownload(previewData?.file_name)"
          >
            下载文档
          </el-button>
        </template>
      </el-dialog>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Upload, Search, Delete, View, Download } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import AppLayout from '@/components/common/AppLayout.vue'
import {
  getStats,
  getDocuments,
  deleteDocument,
  searchKnowledge,
  getDocumentPreview,
  downloadDocumentFile,
} from '@/api/knowledge.js'

const stats = ref({})
const documents = ref([])
const loadingDocs = ref(false)
const showUpload = ref(false)
const searchQuery = ref('')
const searchResults = ref([])
const searching = ref(false)

// 预览相关
const previewVisible = ref(false)
const previewData = ref(null)
const previewLoading = ref(false)

async function loadStats() {
  try {
    const res = await fetch('/api/knowledge/stats')
    stats.value = await res.json()
  } catch (_) {}
}

async function loadDocuments() {
  loadingDocs.value = true
  try {
    const res = await fetch('/api/knowledge/documents')
    documents.value = await res.json()
  } catch (_) {} finally {
    loadingDocs.value = false
  }
}

async function doSearch() {
  if (!searchQuery.value.trim()) return
  searching.value = true
  try {
    const res = await fetch('/api/knowledge/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: searchQuery.value, top_k: 5 }),
    })
    const data = await res.json()
    searchResults.value = data.results || []
  } catch (e) {
    ElMessage.error('检索失败')
  } finally {
    searching.value = false
  }
}

async function removeDoc(fileName) {
  try {
    await deleteDocument(fileName)
    ElMessage.success('删除成功')
    loadDocuments()
    loadStats()
  } catch (e) {
    ElMessage.error('删除失败')
  }
}

async function previewDocument(row) {
  previewLoading.value = true
  previewVisible.value = true
  previewData.value = null
  try {
    previewData.value = await getDocumentPreview(row.file_name)
  } catch (e) {
    ElMessage.error('加载预览失败')
    previewVisible.value = false
  } finally {
    previewLoading.value = false
  }
}

function handleDownload(fileName) {
  if (!fileName) return
  downloadDocumentFile(fileName).catch(() => ElMessage.error('下载失败'))
}

function onUploadSuccess(res) {
  ElMessage.success(`导入成功: ${res.chunk_count} 个文本块`)
  showUpload.value = false
  loadDocuments()
  loadStats()
}

function onUploadError() {
  ElMessage.error('上传失败')
}

onMounted(() => {
  loadStats()
  loadDocuments()
})
</script>

<style scoped>
.knowledge-view {
  padding: 24px 32px;
  max-width: 1100px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.page-header h1 {
  font-size: 22px;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 4px;
}

.page-header p {
  font-size: 14px;
  color: #64748b;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 28px;
}

.stat-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 20px;
  text-align: center;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #2563eb;
  margin-bottom: 4px;
}

.stat-label {
  font-size: 13px;
  color: #64748b;
}

.stat-num {
  font-weight: 600;
  color: #6366f1;
}

.search-section,
.docs-section {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 20px;
}

.search-section h3,
.docs-section h3 {
  font-size: 16px;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 16px;
}

.search-bar {
  margin-bottom: 16px;
}

.search-results {
  border-top: 1px solid #e2e8f0;
  padding-top: 12px;
}

.result-item {
  padding: 12px;
  border: 1px solid #f1f5f9;
  border-radius: 8px;
  margin-bottom: 8px;
  background: #fafbfc;
}

.result-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.result-source {
  font-size: 13px;
  font-weight: 500;
  color: #475569;
}

.result-content {
  font-size: 13px;
  color: #64748b;
  line-height: 1.6;
  max-height: 80px;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 预览弹窗 */
.preview-stats {
  display: flex;
  gap: 24px;
  padding: 12px 16px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.pstat {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.pstat-label {
  font-size: 11px;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.pstat-value {
  font-size: 16px;
  font-weight: 600;
  color: #1e293b;
}

.chunks-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 60vh;
  overflow-y: auto;
}

.chunk-item {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  overflow: hidden;
}

.chunk-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 14px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
}

.chunk-meta {
  font-size: 12px;
  color: #94a3b8;
}

.chunk-content {
  padding: 14px;
  font-size: 13px;
  color: #475569;
  line-height: 1.8;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>

<!-- chunk 预览样式用全局 style，避免 el-dialog teleport 导致 scoped 失效 -->
<style>
.pchunk-item {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  overflow: hidden;
  margin-bottom: 0;
}
.pchunk-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 14px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
}
.pchunk-meta {
  font-size: 12px;
  color: #94a3b8;
}
.pchunk-content {
  padding: 14px;
  font-size: 13px;
  color: #334155;
  line-height: 1.8;
  white-space: pre-wrap;
  word-break: break-all;
  background: #ffffff;
}
</style>
