<template>
  <AppLayout>
    <div class="stats-page">
      <div class="page-header">
        <el-icon :size="24" color="#6366f1"><DataAnalysis /></el-icon>
        <h2>数据看板</h2>
      </div>

      <div v-loading="loading">
        <!-- 核心指标卡片 -->
        <div class="metric-cards">
          <div class="metric-card">
            <div class="metric-icon" style="background:#eff6ff">💬</div>
            <div class="metric-info">
              <div class="metric-value">{{ overview.questions }}</div>
              <div class="metric-label">累计提问</div>
            </div>
          </div>
          <div class="metric-card">
            <div class="metric-icon" style="background:#f0fdf4">🗂️</div>
            <div class="metric-info">
              <div class="metric-value">{{ overview.conversations }}</div>
              <div class="metric-label">对话会话</div>
            </div>
          </div>
          <div class="metric-card">
            <div class="metric-icon" style="background:#fffbeb">⭐</div>
            <div class="metric-info">
              <div class="metric-value">{{ overview.favorites }}</div>
              <div class="metric-label">收藏回答</div>
            </div>
          </div>
          <div class="metric-card">
            <div class="metric-icon" style="background:#fdf4ff">👍</div>
            <div class="metric-info">
              <div class="metric-value">{{ overview.feedback?.helpful_rate ?? 0 }}%</div>
              <div class="metric-label">回答满意率</div>
            </div>
          </div>
        </div>

        <div class="charts-row">
          <!-- 近 7 天趋势 -->
          <div class="chart-card">
            <div class="chart-title">📈 近 7 天提问趋势</div>
            <div class="bar-chart">
              <div
                v-for="item in trend"
                :key="item.date"
                class="bar-group"
              >
                <div
                  class="bar"
                  :style="{ height: barHeight(item.questions) + 'px' }"
                  :title="`${item.questions} 次`"
                ></div>
                <div class="bar-label">{{ item.date }}</div>
                <div class="bar-value">{{ item.questions }}</div>
              </div>
            </div>
          </div>

          <!-- 反馈分布 -->
          <div class="chart-card">
            <div class="chart-title">💬 回答反馈分布</div>
            <div class="feedback-stats">
              <div class="feedback-row">
                <span class="feedback-label">👍 有用</span>
                <div class="progress-bar">
                  <div
                    class="progress-fill helpful"
                    :style="{ width: helpfulPercent + '%' }"
                  ></div>
                </div>
                <span class="feedback-count">{{ overview.feedback?.helpful ?? 0 }}</span>
              </div>
              <div class="feedback-row">
                <span class="feedback-label">👎 没用</span>
                <div class="progress-bar">
                  <div
                    class="progress-fill not-helpful"
                    :style="{ width: (100 - helpfulPercent) + '%' }"
                  ></div>
                </div>
                <span class="feedback-count">{{ overview.feedback?.not_helpful ?? 0 }}</span>
              </div>
              <div class="feedback-total">共 {{ overview.feedback?.total ?? 0 }} 次评价</div>
            </div>

            <!-- 知识库状态 -->
            <div class="chart-title" style="margin-top: 24px">📚 知识库状态</div>
            <div class="kb-stats">
              <div class="kb-item">
                <span class="kb-label">文档数</span>
                <span class="kb-value">{{ overview.knowledge_base?.document_count ?? 0 }}</span>
              </div>
              <div class="kb-item">
                <span class="kb-label">向量块数</span>
                <span class="kb-value">{{ overview.knowledge_base?.chunk_count ?? 0 }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { DataAnalysis } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import AppLayout from '@/components/common/AppLayout.vue'
import { getOverview, getTrend } from '@/api/stats.js'

const loading = ref(false)
const overview = ref({})
const trend = ref([])

const helpfulPercent = computed(() => {
  const fb = overview.value.feedback
  if (!fb || fb.total === 0) return 0
  return Math.round((fb.helpful / fb.total) * 100)
})

const maxTrend = computed(() => Math.max(...trend.value.map(t => t.questions), 1))

function barHeight(count) {
  return Math.max(4, (count / maxTrend.value) * 120)
}

async function load() {
  loading.value = true
  try {
    const [ov, tr] = await Promise.all([getOverview(), getTrend()])
    overview.value = ov
    trend.value = tr
  } catch (_) {
    ElMessage.error('加载统计数据失败')
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.stats-page {
  padding: 28px 36px;
  height: 100%;
  overflow-y: auto;
  background: #f8fafc;
}

.page-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 28px;
}

.page-header h2 {
  font-size: 20px;
  font-weight: 600;
  color: #1e293b;
  margin: 0;
}

/* ===== 指标卡 ===== */
.metric-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.metric-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  transition: box-shadow 0.2s;
}

.metric-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.08); }

.metric-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
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

/* ===== 图表行 ===== */
.charts-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.chart-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 20px;
}

.chart-title {
  font-size: 14px;
  font-weight: 600;
  color: #374151;
  margin-bottom: 16px;
}

/* ===== 柱状图 ===== */
.bar-chart {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  height: 150px;
  padding-top: 10px;
}

.bar-group {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.bar {
  width: 100%;
  max-width: 36px;
  background: linear-gradient(to top, #6366f1, #818cf8);
  border-radius: 4px 4px 0 0;
  transition: height 0.6s ease;
  cursor: pointer;
}

.bar:hover { background: linear-gradient(to top, #4f46e5, #6366f1); }

.bar-label {
  font-size: 11px;
  color: #94a3b8;
}

.bar-value {
  font-size: 11px;
  color: #64748b;
  font-weight: 500;
}

/* ===== 反馈分布 ===== */
.feedback-stats { display: flex; flex-direction: column; gap: 12px; }

.feedback-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.feedback-label { width: 60px; font-size: 13px; color: #475569; flex-shrink: 0; }

.progress-bar {
  flex: 1;
  height: 10px;
  background: #f1f5f9;
  border-radius: 99px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  border-radius: 99px;
  transition: width 0.6s ease;
}

.progress-fill.helpful { background: linear-gradient(to right, #34d399, #10b981); }
.progress-fill.not-helpful { background: linear-gradient(to right, #fca5a5, #f87171); }

.feedback-count { width: 28px; text-align: right; font-size: 13px; color: #64748b; }

.feedback-total {
  font-size: 12px;
  color: #94a3b8;
  text-align: right;
}

/* ===== 知识库统计 ===== */
.kb-stats { display: flex; gap: 24px; }

.kb-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.kb-label { font-size: 12px; color: #94a3b8; }

.kb-value {
  font-size: 22px;
  font-weight: 700;
  color: #6366f1;
}
</style>
