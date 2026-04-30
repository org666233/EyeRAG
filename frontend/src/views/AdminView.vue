<template>
  <AppLayout>
    <div class="admin-page">
      <div class="page-header">
        <div class="header-left">
          <el-icon :size="22" color="#6366f1"><Setting /></el-icon>
          <h2>系统管理后台</h2>
        </div>
      </div>

      <el-tabs v-model="activeTab" class="admin-tabs">
        <!-- ═══ 系统分析 ═══ -->
        <el-tab-pane label="系统分析" name="analysis">
          <div v-loading="overviewLoading">
            <!-- 概览指标 -->
            <div class="metric-cards">
              <div class="metric-card">
                <div class="metric-icon" style="background:#eff6ff;color:#3b82f6"><el-icon :size="22"><UserFilled /></el-icon></div>
                <div class="metric-info">
                  <div class="metric-value">{{ overview.total_users ?? 0 }}</div>
                  <div class="metric-label">注册用户</div>
                </div>
              </div>
              <div class="metric-card">
                <div class="metric-icon" style="background:#f0fdf4;color:#10b981"><el-icon :size="22"><ChatDotRound /></el-icon></div>
                <div class="metric-info">
                  <div class="metric-value">{{ overview.total_questions ?? 0 }}</div>
                  <div class="metric-label">总提问数</div>
                </div>
              </div>
              <div class="metric-card">
                <div class="metric-icon" style="background:#fffbeb;color:#f59e0b"><el-icon :size="22"><Search /></el-icon></div>
                <div class="metric-info">
                  <div class="metric-value">{{ overview.total_searches ?? 0 }}</div>
                  <div class="metric-label">检索记录</div>
                </div>
              </div>
              <div class="metric-card">
                <div class="metric-icon" style="background:#fdf4ff;color:#a855f7"><el-icon :size="22"><Promotion /></el-icon></div>
                <div class="metric-info">
                  <div class="metric-value">{{ overview.feedback?.helpful_rate ?? 0 }}%</div>
                  <div class="metric-label">满意率</div>
                </div>
              </div>
            </div>

            <!-- 图表行 1: 决策分布 + 反馈趋势 -->
            <div class="charts-row">
              <div class="chart-card">
                <div class="chart-title">检索决策分布
                  <el-select v-model="decisionDays" size="small" style="margin-left:12px;width:100px" @change="loadDecisionDistribution">
                    <el-option label="近7天" :value="7" />
                    <el-option label="近30天" :value="30" />
                    <el-option label="近90天" :value="90" />
                  </el-select>
                </div>
                <v-chart class="pie-chart" :option="decisionPieOption" autoresize />
              </div>
              <div class="chart-card">
                <div class="chart-title">每日反馈趋势
                  <el-select v-model="feedbackDays" size="small" style="margin-left:12px;width:100px" @change="loadFeedbackTrend">
                    <el-option label="近7天" :value="7" />
                    <el-option label="近30天" :value="30" />
                  </el-select>
                </div>
                <v-chart class="line-chart" :option="feedbackTrendOption" autoresize />
              </div>
            </div>

            <!-- 图表行 2: 响应耗时 + 来源质量 -->
            <div class="charts-row">
              <div class="chart-card">
                <div class="chart-title">响应耗时趋势</div>
                <v-chart class="line-chart" :option="responseTimeOption" autoresize />
              </div>
              <div class="chart-card">
                <div class="chart-title">各来源文档检索质量</div>
                <v-chart class="bar-chart" :option="sourceQualityOption" autoresize />
              </div>
            </div>

            <!-- Top 查询热榜 -->
            <div class="chart-card">
              <div class="chart-title">Top 查询热榜</div>
              <el-table :data="topQueries" stripe size="small" max-height="300">
                <el-table-column type="index" label="#" width="60" align="center" />
                <el-table-column prop="question" label="问题" min-width="300" show-overflow-tooltip />
                <el-table-column prop="count" label="查询次数" width="120" align="center" sortable />
                <el-table-column label="平均响应" width="120" align="center">
                  <template #default="{ row }">{{ row.avg_ms }} ms</template>
                </el-table-column>
              </el-table>
            </div>
          </div>
        </el-tab-pane>

        <!-- ═══ 模型配置 ═══ -->
        <el-tab-pane label="模型配置" name="model">
          <div v-loading="modelLoading" class="model-config-panel">
            <!-- LLM 配置 -->
            <div class="config-section">
              <div class="config-section-title">LLM 大语言模型配置</div>
              <div class="config-section-desc">切换后下次请求即生效，无需重启服务</div>
              <div class="config-row">
                <label>推理提供商</label>
                <el-select v-model="modelForm.llm_provider" style="width:200px">
                  <el-option label="DeepSeek" value="deepseek" />
                  <el-option label="MiniMax" value="minimax" />
                </el-select>
              </div>
              <div class="config-row">
                <label>DeepSeek 模型名</label>
                <el-input v-model="modelForm.llm_model_name" style="width:280px" placeholder="deepseek-chat" />
              </div>
              <div class="config-row">
                <label>MiniMax 模型名</label>
                <el-input v-model="modelForm.minimax_model_name" style="width:280px" placeholder="MiniMax-M2.7" />
              </div>
              <el-button type="primary" :loading="modelSaving" @click="saveModelConfig" style="margin-top:8px">
                保存 LLM 配置
              </el-button>
            </div>

            <!-- 嵌入模型信息 -->
            <div class="config-section">
              <div class="config-section-title">嵌入模型 / 向量库</div>
              <div class="config-section-desc">
                嵌入模型已在启动时加载，切换需修改 .env 并重启服务
              </div>
              <div class="config-info-grid">
                <div class="info-item">
                  <span class="info-label">当前模型</span>
                  <span class="info-value">{{ modelConfig.embedding_model?.model_name || '-' }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">模型类型</span>
                  <span class="info-value">{{ modelConfig.embedding_model?.model_type || '-' }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">向量维度</span>
                  <span class="info-value">{{ modelConfig.embedding_model?.embedding_dim || '-' }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">ChromaDB 集合</span>
                  <span class="info-value">{{ modelConfig.chroma_collection || '-' }}</span>
                </div>
              </div>

              <div class="config-section-title" style="margin-top:20px;font-size:13px">可用本地模型（./model 目录）</div>
              <div class="model-tags">
                <el-tag
                  v-for="m in modelConfig.available_embedding_models"
                  :key="m"
                  :type="modelConfig.embedding_model?.model_name?.includes(m) ? 'primary' : 'info'"
                  effect="plain"
                >
                  {{ m }}
                </el-tag>
                <span v-if="!modelConfig.available_embedding_models?.length" style="color:#94a3b8;font-size:13px">
                  未检测到本地模型目录
                </span>
              </div>
            </div>
          </div>
        </el-tab-pane>

        <!-- ═══ 用户管理 ═══ -->
        <el-tab-pane label="用户管理" name="users">
          <div class="users-header">
            <el-input
              v-model="userKeyword"
              placeholder="搜索用户名/姓名/邮箱..."
              clearable
              style="width:260px"
              :prefix-icon="Search"
              @keydown.enter="loadUsers"
            />
            <el-button :icon="Search" @click="loadUsers">搜索</el-button>
            <el-button :icon="Refresh" @click="loadUsers">刷新</el-button>
          </div>

          <el-table :data="users" v-loading="usersLoading" stripe>
            <el-table-column prop="id" label="ID" width="70" align="center" />
            <el-table-column prop="username" label="用户名" width="140" />
            <el-table-column prop="real_name" label="姓名" width="120" />
            <el-table-column prop="email" label="邮箱" width="180" />
            <el-table-column label="角色" width="100" align="center">
              <template #default="{ row }">
                <el-tag :type="row.role === 'admin' ? 'danger' : 'info'" size="small">
                  {{ row.role === 'admin' ? '管理员' : '普通用户' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="80" align="center">
              <template #default="{ row }">
                <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">
                  {{ row.is_active ? '正常' : '禁用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="question_count" label="提问数" width="100" align="center" sortable />
            <el-table-column prop="favorite_count" label="收藏数" width="100" align="center" />
            <el-table-column label="注册时间" width="160">
              <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="140" align="center">
              <template #default="{ row }">
                <el-button
                  size="small"
                  text
                  :type="row.is_active ? 'warning' : 'success'"
                  @click="toggleActive(row)"
                >
                  {{ row.is_active ? '禁用' : '启用' }}
                </el-button>
                <el-popconfirm
                  :title="`确定删除用户 ${row.username}?`"
                  @confirm="handleDeleteUser(row.id)"
                >
                  <template #reference>
                    <el-button size="small" text type="danger">删除</el-button>
                  </template>
                </el-popconfirm>
              </template>
            </el-table-column>
          </el-table>

          <div class="pagination-wrap" v-if="userTotal > 0">
            <el-pagination
              v-model:current-page="userPage"
              :page-size="userPageSize"
              :total="userTotal"
              layout="prev, pager, next, total"
              background
              @current-change="loadUsers"
            />
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Setting, Search, Refresh, UserFilled, ChatDotRound, Promotion } from '@element-plus/icons-vue'
import AppLayout from '@/components/common/AppLayout.vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { PieChart, LineChart, BarChart } from 'echarts/charts'
import {
  TitleComponent, TooltipComponent, LegendComponent, GridComponent,
} from 'echarts/components'

import {
  getAdminOverview,
  getDecisionDistribution,
  getResponseTimeTrend,
  getFeedbackTrend,
  getTopQueries,
  getDecisionBySource,
  getUserList,
  toggleUserActive,
  deleteUser,
  getModelConfig,
  updateModelConfig,
} from '@/api/admin.js'

use([CanvasRenderer, PieChart, LineChart, BarChart,
  TitleComponent, TooltipComponent, LegendComponent, GridComponent])

// ── Tab 控制 ──
const activeTab = ref('analysis')

// ── 概览 ──
const overviewLoading = ref(false)
const overview = ref({})

// ── 检索决策分布 ──
const decisionDays = ref(30)
const decisionDist = ref([])

const decisionPieOption = computed(() => ({
  tooltip: { trigger: 'item', formatter: '{b}: {c}次 ({d}%)' },
  legend: { orient: 'vertical', right: 16, top: 'center', textStyle: { fontSize: 12 } },
  series: [{
    type: 'pie',
    radius: ['40%', '70%'],
    center: ['35%', '50%'],
    label: { show: true, formatter: '{b}\n{d}%' },
    data: decisionDist.value.map(d => ({
      value: d.count,
      name: d.label,
      itemStyle: {
        color: d.decision === 'proceed' ? '#10b981'
          : d.decision === 'retry' ? '#f59e0b'
          : d.decision === 'fallback' ? '#ef4444' : '#94a3b8',
      },
    })),
  }],
}))

// ── 反馈趋势 ──
const feedbackDays = ref(7)
const feedbackTrend = ref([])

const feedbackTrendOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { data: ['有用', '没用'], bottom: 0 },
  grid: { left: 50, right: 20, top: 10, bottom: 40 },
  xAxis: { type: 'category', data: feedbackTrend.value.map(d => d.date), axisLabel: { fontSize: 11 } },
  yAxis: { type: 'value', axisLabel: { fontSize: 11 } },
  series: [
    {
      name: '有用',
      type: 'line',
      smooth: true,
      data: feedbackTrend.value.map(d => d.helpful),
      lineStyle: { color: '#10b981' },
      itemStyle: { color: '#10b981' },
      areaStyle: { color: 'rgba(16,185,129,0.1)' },
    },
    {
      name: '没用',
      type: 'line',
      smooth: true,
      data: feedbackTrend.value.map(d => d.not_helpful),
      lineStyle: { color: '#ef4444' },
      itemStyle: { color: '#ef4444' },
    },
  ],
}))

// ── 响应耗时 ──
const responseTimeTrend = ref([])

const responseTimeOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { data: ['平均', '最大', '最小'], bottom: 0 },
  grid: { left: 60, right: 20, top: 10, bottom: 40 },
  xAxis: { type: 'category', data: responseTimeTrend.value.map(d => d.date), axisLabel: { fontSize: 11 } },
  yAxis: { type: 'value', name: 'ms', axisLabel: { fontSize: 11 } },
  series: [
    { name: '平均', type: 'line', smooth: true, data: responseTimeTrend.value.map(d => d.avg_ms), lineStyle: { color: '#6366f1' }, itemStyle: { color: '#6366f1' } },
    { name: '最大', type: 'line', smooth: true, data: responseTimeTrend.value.map(d => d.max_ms), lineStyle: { color: '#ef4444', type: 'dashed' }, itemStyle: { color: '#ef4444' } },
    { name: '最小', type: 'line', smooth: true, data: responseTimeTrend.value.map(d => d.min_ms), lineStyle: { color: '#10b981', type: 'dashed' }, itemStyle: { color: '#10b981' } },
  ],
}))

// ── 来源质量 ──
const sourceQuality = ref([])

const sourceQualityOption = computed(() => ({
  tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
  legend: { data: ['正常检索', '二次检索', '降级回答'], bottom: 0, textStyle: { fontSize: 11 } },
  grid: { left: 120, right: 20, top: 10, bottom: 50 },
  xAxis: { type: 'value' },
  yAxis: { type: 'category', data: sourceQuality.value.map(s => s.source), axisLabel: { fontSize: 11, width: 110, overflow: 'truncate' } },
  series: [
    { name: '正常检索', type: 'bar', stack: 'total', data: sourceQuality.value.map(s => s.proceed), itemStyle: { color: '#10b981' } },
    { name: '二次检索', type: 'bar', stack: 'total', data: sourceQuality.value.map(s => s.retry), itemStyle: { color: '#f59e0b' } },
    { name: '降级回答', type: 'bar', stack: 'total', data: sourceQuality.value.map(s => s.fallback), itemStyle: { color: '#ef4444' } },
  ],
}))

// ── Top 查询 ──
const topQueries = ref([])

// ── 模型配置 ──
const modelLoading = ref(false)
const modelSaving = ref(false)
const modelConfig = ref({})
const modelForm = ref({ llm_provider: 'deepseek', llm_model_name: '', minimax_model_name: '' })

async function loadModelConfig() {
  modelLoading.value = true
  try {
    modelConfig.value = await getModelConfig()
    modelForm.value.llm_provider = modelConfig.value.llm_provider || 'deepseek'
    modelForm.value.llm_model_name = modelConfig.value.llm_model_name || ''
    modelForm.value.minimax_model_name = modelConfig.value.minimax_model_name || ''
  } catch (_) { ElMessage.error('加载模型配置失败') }
  finally { modelLoading.value = false }
}

async function saveModelConfig() {
  modelSaving.value = true
  try {
    await updateModelConfig({
      llm_provider: modelForm.value.llm_provider,
      llm_model_name: modelForm.value.llm_model_name,
      minimax_model_name: modelForm.value.minimax_model_name,
    })
    ElMessage.success('LLM 配置已保存，下次问答请求生效')
    await loadModelConfig()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '保存失败')
  } finally {
    modelSaving.value = false
  }
}

// ── 用户管理 ──
const usersLoading = ref(false)
const users = ref([])
const userKeyword = ref('')
const userPage = ref(1)
const userPageSize = ref(20)
const userTotal = ref(0)

// ── 数据加载 ──
async function loadOverview() {
  overviewLoading.value = true
  try {
    overview.value = await getAdminOverview()
  } catch (_) { ElMessage.error('加载概览失败') }
  finally { overviewLoading.value = false }
}

async function loadDecisionDistribution() {
  try {
    const res = await getDecisionDistribution(decisionDays.value)
    decisionDist.value = res.items || []
  } catch (_) {}
}

async function loadResponseTimeTrend() {
  try {
    responseTimeTrend.value = await getResponseTimeTrend(7)
  } catch (_) {}
}

async function loadFeedbackTrend() {
  try {
    feedbackTrend.value = await getFeedbackTrend(feedbackDays.value)
  } catch (_) {}
}

async function loadSourceQuality() {
  try {
    sourceQuality.value = await getDecisionBySource(30)
  } catch (_) {}
}

async function loadTopQueries() {
  try {
    topQueries.value = await getTopQueries(20, 30)
  } catch (_) {}
}

async function loadUsers() {
  usersLoading.value = true
  try {
    const res = await getUserList(userPage.value, userPageSize.value, userKeyword.value)
    users.value = res.items || []
    userTotal.value = res.total || 0
  } catch (_) { ElMessage.error('加载用户列表失败') }
  finally { usersLoading.value = false }
}

async function toggleActive(row) {
  try {
    await toggleUserActive(row.id)
    row.is_active = !row.is_active
    ElMessage.success(row.is_active ? '已启用' : '已禁用')
  } catch (e) {
    ElMessage.error(e.detail || '操作失败')
  }
}

async function handleDeleteUser(userId) {
  try {
    await deleteUser(userId)
    ElMessage.success('删除成功')
    loadUsers()
  } catch (e) {
    ElMessage.error(e.detail || '删除失败')
  }
}

function formatDate(iso) {
  if (!iso) return '-'
  return new Date(iso).toLocaleString('zh-CN')
}

onMounted(() => {
  loadOverview()
  loadDecisionDistribution()
  loadResponseTimeTrend()
  loadFeedbackTrend()
  loadSourceQuality()
  loadTopQueries()
  loadUsers()
  loadModelConfig()
})
</script>

<style scoped>
.admin-page {
  padding: 28px 36px;
  height: 100%;
  overflow-y: auto;
  background: #f8fafc;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
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

.admin-tabs {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 20px;
}

/* 概览卡片 */
.metric-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.metric-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
}

.metric-icon {
  width: 48px;
  height: 48px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.metric-value {
  font-size: 28px;
  font-weight: 700;
  color: #1e293b;
  line-height: 1;
}

.metric-label {
  font-size: 13px;
  color: #64748b;
  margin-top: 4px;
}

/* 图表 */
.charts-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 16px;
}

.chart-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 16px;
}

.chart-title {
  font-size: 14px;
  font-weight: 600;
  color: #374151;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
}

.pie-chart,
.line-chart,
.bar-chart {
  width: 100%;
  height: 220px;
}

/* 用户管理 */
.users-header {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-bottom: 16px;
}

.pagination-wrap {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}

/* 模型配置 */
.model-config-panel {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.config-section {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 20px 24px;
}

.config-section-title {
  font-size: 15px;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 4px;
}

.config-section-desc {
  font-size: 12px;
  color: #94a3b8;
  margin-bottom: 16px;
}

.config-row {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 12px;
}

.config-row label {
  font-size: 13px;
  color: #475569;
  width: 120px;
  flex-shrink: 0;
}

.config-info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 4px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 3px;
  background: #fff;
  padding: 10px 14px;
  border-radius: 8px;
  border: 1px solid #e8ecf1;
}

.info-label {
  font-size: 11px;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.info-value {
  font-size: 13px;
  color: #1e293b;
  font-weight: 500;
  word-break: break-all;
}

.model-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}
</style>
