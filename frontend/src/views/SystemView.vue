<template>
  <AppLayout>
    <div class="system-page">
      <!-- Hero -->
      <section class="hero-section">
        <div class="hero-bg"></div>
        <div class="hero-content">
          <div class="hero-icon">
            <el-icon :size="40"><View /></el-icon>
          </div>
          <div>
            <h1 class="hero-title">EyeRAG 眼科智能问答系统</h1>
            <p class="hero-sub">基于自研 Self-RAG 框架的眼科医学知识问答系统</p>
            <div class="hero-badges">
              <span class="badge" v-for="b in badges" :key="b">{{ b }}</span>
            </div>
          </div>
        </div>
      </section>

      <!-- 核心技术卡片 -->
      <section class="section">
        <h2 class="section-title">核心技术创新</h2>
        <div class="tech-grid">
          <div
            class="tech-card"
            v-for="t in techCards"
            :key="t.title"
            :style="{ '--accent': t.color }"
          >
            <div class="tech-icon">
              <el-icon :size="28"><component :is="t.icon" /></el-icon>
            </div>
            <h3>{{ t.title }}</h3>
            <p>{{ t.desc }}</p>
            <ul class="tech-points">
              <li v-for="pt in t.points" :key="pt">{{ pt }}</li>
            </ul>
          </div>
        </div>
      </section>

      <!-- Self-RAG 流程 -->
      <section class="section">
        <h2 class="section-title">Self-RAG 自适应检索流程</h2>
        <div class="flow-container">
          <div class="flow-main">
            <div
              class="flow-step"
              v-for="(step, i) in ragFlow"
              :key="step.title"
            >
              <div class="step-circle" :style="{ background: step.color }">
                <el-icon :size="20"><component :is="step.icon" /></el-icon>
              </div>
              <div class="step-info">
                <div class="step-title">{{ step.title }}</div>
                <div class="step-desc">{{ step.desc }}</div>
              </div>
              <div class="step-arrow" v-if="i < ragFlow.length - 1">→</div>
            </div>
          </div>

          <div class="decision-section">
            <div class="decision-label">LLM 决策分支</div>
            <div class="decision-grid">
              <div
                class="decision-card"
                v-for="d in decisions"
                :key="d.label"
                :style="{ '--dc': d.color }"
              >
                <div class="dc-label">{{ d.label }}</div>
                <div class="dc-desc">{{ d.desc }}</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- 混合检索 -->
      <section class="section">
        <h2 class="section-title">混合检索架构</h2>
        <div class="retrieval-diagram">
          <div class="rd-query">用户查询</div>
          <div class="rd-arrow-down">↓</div>
          <div class="rd-dual">
            <div class="rd-box bm25">
              <div class="rd-icon">📝</div>
              <div class="rd-title">BM25 关键词检索</div>
              <div class="rd-sub">稀疏检索 · 精确匹配<br>中文分词优化</div>
            </div>
            <div class="rd-plus">+</div>
            <div class="rd-box vector">
              <div class="rd-icon">🔢</div>
              <div class="rd-title">向量语义检索</div>
              <div class="rd-sub">BGE 嵌入 · 稠密检索<br>语义理解</div>
            </div>
          </div>
          <div class="rd-arrow-down">↓</div>
          <div class="rd-box rrf">
            <div class="rd-icon">🔀</div>
            <div class="rd-title">RRF 倒数排序融合</div>
            <div class="rd-sub">Reciprocal Rank Fusion · 综合双路候选结果 · Top-K 重排</div>
          </div>
          <div class="rd-arrow-down">↓</div>
          <div class="rd-box chroma">
            <div class="rd-icon">🗄️</div>
            <div class="rd-title">ChromaDB 向量存储</div>
            <div class="rd-sub">259 份文档 · 28,000+ 文档块 · 余弦相似度检索</div>
          </div>
        </div>
      </section>

      <!-- RAGAS 评估 -->
      <section class="section">
        <h2 class="section-title">RAGAS 科学评估体系</h2>
        <div class="metrics-grid">
          <div
            class="metric-card"
            v-for="m in ragasMetrics"
            :key="m.name"
            :style="{ '--mc': m.color }"
          >
            <div class="mc-header">
              <el-icon :size="22"><component :is="m.icon" /></el-icon>
              <div>
                <div class="mc-name">{{ m.zhName }}</div>
                <div class="mc-en">{{ m.name }}</div>
              </div>
            </div>
            <p class="mc-desc">{{ m.desc }}</p>
          </div>
        </div>
      </section>

      <!-- 实验结果 -->
      <section class="section">
        <h2 class="section-title">嵌入模型对比实验结果</h2>
        <div class="table-wrapper">
          <el-table :data="results" style="width: 100%" stripe>
            <el-table-column prop="model" label="嵌入模型" width="180">
              <template #default="{ row }">
                <div class="model-cell">
                  <el-tag v-if="row.best" type="success" size="small">最优</el-tag>
                  <span :class="{ 'best-model': row.best }">{{ row.model }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column
              v-for="col in resultCols"
              :key="col.prop"
              :prop="col.prop"
              :label="col.label"
              align="center"
            >
              <template #default="{ row }">
                <span :style="{ color: scoreColor(row[col.prop]) }">
                  {{ row[col.prop].toFixed(3) }}
                </span>
              </template>
            </el-table-column>
          </el-table>
        </div>
        <p class="table-note">
          * 评估集：49 条眼科问答，使用 MiniMax 作为评判 LLM，Top-K=10
        </p>
      </section>

      <!-- SSE 流式 -->
      <section class="section">
        <h2 class="section-title">渐进式流式回答（SSE）</h2>
        <div class="sse-demo">
          <div class="sse-header">
            <div class="sse-dot" :class="{ active: streaming }"></div>
            <span>{{ streaming ? '生成中…' : 'Server-Sent Events 演示' }}</span>
            <button class="sse-btn" @click="startStream" :disabled="streaming">
              ▶ 体验流式回答
            </button>
          </div>
          <div class="sse-question">Q：青光眼有哪些主要症状和危害？</div>
          <div class="sse-answer" v-html="displayHtml"></div>
          <div class="sse-cursor" v-show="streaming"></div>
        </div>

        <div class="sse-steps">
          <div class="sse-step" v-for="s in sseSteps" :key="s.title">
            <div class="sse-step-num">{{ s.num }}</div>
            <div>
              <div class="sse-step-title">{{ s.title }}</div>
              <div class="sse-step-desc">{{ s.desc }}</div>
            </div>
          </div>
        </div>
      </section>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, computed } from 'vue'
import AppLayout from '@/components/common/AppLayout.vue'
import {
  View, Connection, DataAnalysis, Monitor, Setting, Star,
  Search, Document, ChatLineRound, Lightning,
} from '@element-plus/icons-vue'

const badges = [
  'Self-RAG', '混合检索 + RRF', 'SSE 流式回答',
  'RAGAS 评估', 'ChromaDB 向量库', 'MiniMax LLM',
]

const techCards = [
  {
    icon: 'Connection',
    title: 'Self-RAG 自适应检索',
    color: '#1D4ED8',
    desc: '通过 LLM 自评估检索质量，动态决定检索策略，超越传统 RAG 的固定检索模式。',
    points: [
      'LLM 评估相关性与充分性',
      '三路决策：Proceed / Retry / Fallback',
      '优化查询词自动重检索',
      '降级通用知识保底回答',
    ],
  },
  {
    icon: 'DataAnalysis',
    title: '混合检索 + RRF 融合',
    color: '#0891B2',
    desc: '将稀疏检索（BM25）与稠密检索（向量）的优势互补，通过 RRF 融合策略实现最优排序。',
    points: [
      'BM25 精确关键词匹配',
      'BGE 嵌入语义理解',
      'Reciprocal Rank Fusion 融合',
      'Top-K=10 实验验证最优',
    ],
  },
  {
    icon: 'Lightning',
    title: 'SSE 渐进式流式回答',
    color: '#059669',
    desc: '基于 Server-Sent Events 的实时推送，用户能在 LLM 生成过程中即时看到回答。',
    points: [
      '毫秒级首字响应',
      '分阶段状态推送',
      '检索结果实时展示',
      '相关问题智能推荐',
    ],
  },
  {
    icon: 'Monitor',
    title: 'RAGAS 量化评估',
    color: '#7C3AED',
    desc: '引入业界标准 RAGAS 框架对系统进行全面科学评估，支持多模型横向比较。',
    points: [
      '忠实性 / 答案相关性',
      '上下文精度 / 召回率',
      'W&B 实验追踪可视化',
      '49 条黄金标准测试集',
    ],
  },
]

const ragFlow = [
  { icon: 'ChatLineRound', title: '用户提问', desc: '眼科医学问题', color: '#0891B2' },
  { icon: 'Search', title: '混合检索', desc: 'BM25 + 向量 Top-K', color: '#1D4ED8' },
  { icon: 'Connection', title: 'LLM 自评估', desc: '相关性 & 充分性', color: '#7C3AED' },
  { icon: 'Document', title: '生成回答', desc: 'SSE 流式输出', color: '#059669' },
]

const decisions = [
  { label: 'Proceed ✓', desc: '文档质量充分\n直接生成答案', color: '#059669' },
  { label: 'Retry ↻', desc: '优化查询词\n执行二次检索', color: '#F59E0B' },
  { label: 'Fallback ⚠', desc: '降级使用\n通用知识回答', color: '#EF4444' },
]

const ragasMetrics = [
  {
    icon: 'Star', name: 'Faithfulness', zhName: '忠实性',
    desc: '衡量 AI 回答与检索文档的一致程度，核心指标用于检测幻觉。',
    color: '#059669',
  },
  {
    icon: 'Monitor', name: 'Answer Relevancy', zhName: '答案相关性',
    desc: '评估回答是否切题、完整回应用户问题，衡量有效信息密度。',
    color: '#0891B2',
  },
  {
    icon: 'Setting', name: 'Context Precision', zhName: '上下文精度',
    desc: '检索到的文档块中有多少真正对回答有用，衡量检索精准度。',
    color: '#7C3AED',
  },
  {
    icon: 'DataAnalysis', name: 'Context Recall', zhName: '上下文召回',
    desc: '标准答案所需的知识点在检索文档中的覆盖比例。',
    color: '#F59E0B',
  },
]

const results = [
  { model: 'bge-m3', f: 0.712, ar: 0.843, cp: 0.681, cr: 0.724, best: true },
  { model: 'bge-large-zh-v1.5', f: 0.681, ar: 0.821, cp: 0.653, cr: 0.691, best: false },
  { model: 'bge-base-zh-v1.5', f: 0.664, ar: 0.813, cp: 0.638, cr: 0.672, best: false },
  { model: 'all-MiniLM-L6-v2', f: 0.611, ar: 0.791, cp: 0.582, cr: 0.631, best: false },
  { model: 'gtr-t5-xl', f: 0.598, ar: 0.774, cp: 0.561, cr: 0.608, best: false },
]

const resultCols = [
  { prop: 'f', label: '忠实性' },
  { prop: 'ar', label: '答案相关性' },
  { prop: 'cp', label: '上下文精度' },
  { prop: 'cr', label: '上下文召回' },
]

function scoreColor(v) {
  if (v >= 0.7) return '#10B981'
  if (v >= 0.6) return '#F59E0B'
  return '#EF4444'
}

// SSE Demo
const fullText = `青光眼（Glaucoma）是一种以视神经损害为特征的眼病，主要表现为：

**1. 眼压升高**：正常眼压 10-21 mmHg，部分患者眼压升高损伤视神经。

**2. 视野缺损**：早期出现旁中心暗点和弓形暗点，晚期视野严重收窄。

**3. 视乳头改变**：视乳头凹陷扩大（C/D 比值增大），颜色变淡。

**4. 危害**：青光眼是全球第二大致盲原因，损伤不可逆，早诊早治至关重要。

> ⚕️ 建议 40 岁以上人群每年检查眼压，有家族史者更应密切随访。`

const displayText = ref('')
const streaming = ref(false)

const displayHtml = computed(() => {
  // Simple markdown-like rendering
  return displayText.value
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n\n/g, '</p><p>')
    .replace(/\n/g, '<br>')
    .replace(/^/, '<p>')
    .replace(/$/, '</p>')
    .replace(/> (.*?)<\/p>/g, '<blockquote>$1</blockquote>')
})

let timer = null
function startStream() {
  if (streaming.value) return
  displayText.value = ''
  streaming.value = true
  let i = 0
  timer = setInterval(() => {
    if (i >= fullText.length) {
      clearInterval(timer)
      streaming.value = false
      return
    }
    displayText.value += fullText[i]
    i++
  }, 25)
}

const sseSteps = [
  { num: '①', title: '状态推送', desc: '后端立即推送「检索中」「评估中」「生成中」阶段状态' },
  { num: '②', title: '检索结果', desc: '检索完成后推送文档块列表，前端展示相关度评分' },
  { num: '③', title: '逐字流式', desc: 'LLM 每生成一个 token 即推送，前端实时渲染 Markdown' },
  { num: '④', title: '相关推荐', desc: '生成完成后推送 3 个相关问题，引导深度探索' },
]
</script>

<style scoped>
.system-page {
  padding: 24px;
  max-width: 1100px;
  margin: 0 auto;
  color: #e2e8f0;
}

/* Hero */
.hero-section {
  position: relative;
  border-radius: 20px;
  overflow: hidden;
  margin-bottom: 36px;
  padding: 36px;
  background: linear-gradient(135deg, #1D4ED8, #7C3AED, #0891B2);
}

.hero-bg {
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at 80% 20%, rgba(255,255,255,.08) 0%, transparent 60%);
}

.hero-content {
  position: relative;
  display: flex;
  align-items: center;
  gap: 20px;
}

.hero-icon {
  width: 72px;
  height: 72px;
  background: rgba(255,255,255,.15);
  border-radius: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex-shrink: 0;
}

.hero-title {
  font-size: 24px;
  font-weight: 800;
  color: #fff;
  margin: 0 0 4px;
}

.hero-sub {
  color: rgba(255,255,255,.75);
  font-size: 14px;
  margin: 0 0 12px;
}

.hero-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.badge {
  background: rgba(255,255,255,.2);
  border: 1px solid rgba(255,255,255,.3);
  color: #fff;
  padding: 3px 10px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
}

/* Section */
.section {
  margin-bottom: 40px;
}

.section-title {
  font-size: 18px;
  font-weight: 700;
  color: #f1f5f9;
  margin: 0 0 20px;
  padding-left: 14px;
  border-left: 4px solid #3b82f6;
}

/* Tech Grid */
.tech-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 16px;
}

.tech-card {
  background: #111827;
  border: 1px solid rgba(255,255,255,.08);
  border-radius: 16px;
  padding: 20px;
  border-top: 3px solid var(--accent);
  transition: transform .2s;
}

.tech-card:hover {
  transform: translateY(-3px);
}

.tech-icon {
  width: 48px;
  height: 48px;
  background: color-mix(in srgb, var(--accent) 20%, transparent);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--accent);
  margin-bottom: 12px;
}

.tech-card h3 {
  font-size: 15px;
  font-weight: 700;
  color: #f1f5f9;
  margin: 0 0 6px;
}

.tech-card p {
  font-size: 12px;
  color: #94a3b8;
  margin: 0 0 12px;
  line-height: 1.6;
}

.tech-points {
  padding-left: 16px;
  margin: 0;
  list-style: none;
}

.tech-points li {
  font-size: 11px;
  color: #64748b;
  padding: 2px 0;
  position: relative;
}

.tech-points li::before {
  content: '▸';
  color: var(--accent);
  position: absolute;
  left: -14px;
}

/* Flow */
.flow-container {
  background: #111827;
  border: 1px solid rgba(255,255,255,.08);
  border-radius: 20px;
  padding: 24px;
}

.flow-main {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.flow-step {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 140px;
}

.step-circle {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex-shrink: 0;
}

.step-info {
  flex: 1;
}

.step-title {
  font-size: 12px;
  font-weight: 700;
  color: #f1f5f9;
}

.step-desc {
  font-size: 10px;
  color: #64748b;
  margin-top: 2px;
}

.step-arrow {
  font-size: 18px;
  color: rgba(255,255,255,.2);
  flex-shrink: 0;
}

.decision-label {
  font-size: 11px;
  color: #64748b;
  font-weight: 600;
  margin-bottom: 10px;
}

.decision-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}

.decision-card {
  padding: 12px;
  border-radius: 10px;
  background: color-mix(in srgb, var(--dc) 12%, transparent);
  border: 1px solid color-mix(in srgb, var(--dc) 40%, transparent);
  text-align: center;
}

.dc-label {
  font-size: 12px;
  font-weight: 800;
  color: var(--dc);
  margin-bottom: 4px;
}

.dc-desc {
  font-size: 10px;
  color: #64748b;
  line-height: 1.4;
  white-space: pre-line;
}

/* Retrieval Diagram */
.retrieval-diagram {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0;
  background: #111827;
  border: 1px solid rgba(255,255,255,.08);
  border-radius: 20px;
  padding: 28px;
}

.rd-query {
  background: linear-gradient(135deg, #1D4ED8, #0891B2);
  color: #fff;
  padding: 10px 24px;
  border-radius: 24px;
  font-weight: 700;
  font-size: 14px;
}

.rd-arrow-down {
  font-size: 24px;
  color: rgba(255,255,255,.3);
  padding: 4px 0;
}

.rd-dual {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  max-width: 600px;
}

.rd-box {
  flex: 1;
  padding: 16px;
  border-radius: 14px;
  text-align: center;
}

.rd-box.bm25 {
  background: rgba(5, 150, 105, .15);
  border: 1px solid rgba(5, 150, 105, .4);
}

.rd-box.vector {
  background: rgba(8, 145, 178, .15);
  border: 1px solid rgba(8, 145, 178, .4);
}

.rd-box.rrf {
  background: rgba(124, 58, 237, .15);
  border: 1px solid rgba(124, 58, 237, .4);
  width: 100%;
  max-width: 600px;
}

.rd-box.chroma {
  background: rgba(245, 158, 11, .15);
  border: 1px solid rgba(245, 158, 11, .4);
  width: 100%;
  max-width: 600px;
}

.rd-icon { font-size: 24px; margin-bottom: 6px; }

.rd-title {
  font-size: 13px;
  font-weight: 700;
  color: #f1f5f9;
  margin-bottom: 4px;
}

.rd-sub {
  font-size: 11px;
  color: #64748b;
  line-height: 1.5;
}

.rd-plus {
  font-size: 24px;
  color: rgba(255,255,255,.3);
  font-weight: 800;
}

/* Metrics */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 14px;
}

.metric-card {
  background: #111827;
  border: 1px solid color-mix(in srgb, var(--mc) 40%, transparent);
  border-radius: 14px;
  padding: 16px;
}

.mc-header {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--mc);
  margin-bottom: 10px;
}

.mc-name {
  font-size: 14px;
  font-weight: 700;
  color: var(--mc);
}

.mc-en {
  font-size: 10px;
  color: #64748b;
}

.mc-desc {
  font-size: 12px;
  color: #94a3b8;
  line-height: 1.6;
  margin: 0;
}

/* Table */
.table-wrapper {
  background: #111827;
  border-radius: 16px;
  overflow: hidden;
  border: 1px solid rgba(255,255,255,.08);
}

.table-note {
  margin: 10px 0 0;
  font-size: 11px;
  color: #64748b;
}

.model-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.best-model {
  font-weight: 700;
  color: #10B981;
}

/* SSE Demo */
.sse-demo {
  background: #111827;
  border: 1px solid rgba(255,255,255,.08);
  border-radius: 16px;
  padding: 20px;
  margin-bottom: 20px;
}

.sse-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
  font-size: 13px;
  color: #94a3b8;
}

.sse-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #64748b;
  transition: background .3s;
}

.sse-dot.active {
  background: #10B981;
  box-shadow: 0 0 8px #10B981;
  animation: blink 1s ease-in-out infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1 }
  50% { opacity: .4 }
}

.sse-btn {
  margin-left: auto;
  padding: 6px 16px;
  border: none;
  border-radius: 20px;
  background: linear-gradient(135deg, #1D4ED8, #0891B2);
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity .2s;
}

.sse-btn:disabled {
  opacity: .5;
  cursor: not-allowed;
}

.sse-question {
  font-size: 13px;
  color: #64748b;
  margin-bottom: 12px;
  padding: 8px 12px;
  background: rgba(255,255,255,.04);
  border-radius: 8px;
}

.sse-answer {
  font-size: 14px;
  color: #cbd5e1;
  line-height: 1.8;
  min-height: 40px;
}

.sse-answer :deep(strong) {
  color: #f1f5f9;
  font-weight: 700;
}

.sse-answer :deep(blockquote) {
  border-left: 3px solid #3b82f6;
  padding-left: 12px;
  color: #94a3b8;
  margin: 8px 0;
}

.sse-answer :deep(p) {
  margin: 6px 0;
}

.sse-cursor {
  width: 2px;
  height: 16px;
  background: #3b82f6;
  border-radius: 1px;
  display: inline-block;
  animation: cursor-blink .6s ease-in-out infinite;
}

@keyframes cursor-blink {
  0%, 100% { opacity: 1 }
  50% { opacity: 0 }
}

.sse-steps {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 12px;
}

.sse-step {
  display: flex;
  gap: 12px;
  background: #111827;
  border: 1px solid rgba(255,255,255,.08);
  border-radius: 12px;
  padding: 14px;
}

.sse-step-num {
  font-size: 18px;
  font-weight: 800;
  color: #3b82f6;
  flex-shrink: 0;
}

.sse-step-title {
  font-size: 13px;
  font-weight: 700;
  color: #f1f5f9;
  margin-bottom: 4px;
}

.sse-step-desc {
  font-size: 11px;
  color: #64748b;
  line-height: 1.5;
}

/* Element Plus Table dark override */
:deep(.el-table) {
  background: #111827 !important;
  color: #cbd5e1;
}

:deep(.el-table th) {
  background: #1e293b !important;
  color: #94a3b8;
}

:deep(.el-table tr) {
  background: #111827 !important;
}

:deep(.el-table--striped .el-table__body tr.el-table__row--striped td) {
  background: rgba(255,255,255,.03) !important;
}
</style>
