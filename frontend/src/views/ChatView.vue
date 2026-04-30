<template>
  <AppLayout>
    <div class="chat-container">
      <!-- 左侧会话列表 -->
      <aside class="conversation-sidebar">
        <div class="sidebar-header">
          <el-button type="primary" class="new-chat-btn" @click="createNewChat">
            <el-icon><Plus /></el-icon>
            新对话
          </el-button>
        </div>
        <div class="conversation-list">
          <div
            v-for="conv in conversations"
            :key="conv.id"
            class="conv-item"
            :class="{ active: conv.id === currentConvId }"
            @click="switchConversation(conv.id)"
          >
            <el-icon><ChatLineSquare /></el-icon>
            <span class="conv-title">{{ conv.title || '新对话' }}</span>
            <div class="conv-actions">
              <el-icon class="conv-action-btn" @click.stop="exportCurrentConv(conv)" title="导出">
                <Download />
              </el-icon>
              <el-icon class="conv-action-btn conv-delete" @click.stop="removeConversation(conv.id)" title="删除">
                <Delete />
              </el-icon>
            </div>
          </div>
          <div v-if="conversations.length === 0" class="conv-empty">
            暂无对话记录
          </div>
        </div>
      </aside>

      <!-- 右侧聊天区域 -->
      <main class="chat-main">
        <!-- 消息列表 -->
        <div class="messages-area" ref="messagesRef">
          <!-- 欢迎界面 -->
          <div v-if="messages.length === 0" class="welcome-screen">
            <div class="welcome-icon"><el-icon :size="56"><View /></el-icon></div>
            <h2>眼科医疗知识问答系统</h2>
            <p>基于 RAG 技术，为您提供专业的眼科医疗知识问答服务</p>
            <div class="suggest-questions">
              <div
                v-for="q in suggestQuestions"
                :key="q"
                class="suggest-item"
                @click="askQuestion(q)"
              >
                {{ q }}
              </div>
            </div>
          </div>

          <!-- 消息流 -->
          <div v-for="(msg, idx) in messages" :key="idx" class="message-wrapper" :class="msg.role">
            <div class="message-avatar">
              <span v-if="msg.role === 'user'"><el-icon :size="20"><User /></el-icon></span>
              <span v-else><el-icon :size="20"><ChatDotRound /></el-icon></span>
            </div>
            <div class="message-body">
              <!-- 用户消息 -->
              <div v-if="msg.role === 'user'" class="message-text user-text">{{ msg.content }}</div>

              <!-- AI 回答 -->
              <div v-else>
                <!-- 检索决策提示 -->
                <div v-if="msg.retrievalDecision && msg.retrievalDecision !== 'proceed'" class="retrieval-badge" :class="msg.retrievalDecision">
                  <el-icon v-if="msg.retrievalDecision === 'fallback'" :size="14"><Warning /></el-icon>
                  <el-icon v-else-if="msg.retrievalDecision === 'retry'" :size="14"><RefreshRight /></el-icon>
                  <span>{{ retrievalDecisionText(msg.retrievalDecision) }}</span>
                </div>

                <!-- 渐进式答案：结论 + 可展开详情 -->
                <div v-if="msg.conclusion && msg.detail" class="progressive-answer">
                  <!-- 结论层（默认展开） -->
                  <div class="answer-conclusion">
                    <div class="conclusion-label"><el-icon><Top /></el-icon> 简要结论</div>
                    <div class="conclusion-text" v-html="renderMarkdown(msg.conclusion, msg.sources)"></div>
                    <el-button
                      text size="small"
                      class="expand-btn"
                      @click="toggleDetail(msg)"
                    >
                      <el-icon><ArrowDown /></el-icon>
                      {{ msg.detailExpanded ? '收起详细解释' : '查看详细解释' }}
                    </el-button>
                  </div>
                  <!-- 详情层（可折叠） -->
                  <div v-show="msg.detailExpanded" class="answer-detail">
                    <div class="detail-label"><el-icon><Reading /></el-icon> 详细解释</div>
                    <div class="detail-text" v-html="renderMarkdown(msg.detail, msg.sources)"></div>
                  </div>
                </div>

                <!-- 加载阶段状态指示 -->
                <div v-else-if="msg.phase" class="loading-phase">
                  <div class="phase-dots"><span></span><span></span><span></span></div>
                  <span class="phase-text">{{ phaseText(msg.phase) }}</span>
                </div>

                <!-- 非渐进式答案（直接渲染） -->
                <div v-else class="message-text assistant-text" v-html="renderMarkdown(msg.content, msg.sources)"></div>

                <!-- 引用来源 -->
                <div v-if="msg.sources && msg.sources.length > 0" class="sources-panel">
                  <div class="sources-title">
                    <el-icon><Document /></el-icon> 参考来源
                  </div>
                  <div class="sources-list">
                    <el-tag
                      v-for="(src, i) in msg.sources"
                      :key="i"
                      size="small"
                      type="info"
                      effect="plain"
                      class="source-tag"
                      :title="src.url || src.source"
                    >
                      📄 {{ src.title }} ({{ (src.score * 100).toFixed(0) }}%)
                    </el-tag>
                  </div>
                </div>

                <!-- 操作栏：反馈 + 收藏 + PDF 导出 -->
                <div v-if="msg.id" class="msg-actions">
                  <el-tooltip content="有用" placement="top">
                    <el-button
                      size="small" text
                      :type="msg.feedback === 1 ? 'success' : ''"
                      @click="handleFeedback(msg, 1)"
                    >
                      <el-icon><Promotion /></el-icon>
                    </el-button>
                  </el-tooltip>
                  <el-tooltip content="没用" placement="top">
                    <el-button
                      size="small" text
                      :type="msg.feedback === 0 ? 'danger' : ''"
                      @click="handleFeedback(msg, 0)"
                    >
                      <el-icon><CloseBold /></el-icon>
                    </el-button>
                  </el-tooltip>
                  <el-tooltip content="收藏" placement="top">
                    <el-button
                      size="small" text
                      :type="msg.favorited ? 'warning' : ''"
                      @click="handleFavorite(msg)"
                    >
                      <el-icon><Star /></el-icon>
                    </el-button>
                  </el-tooltip>
                  <el-tooltip content="导出 PDF" placement="top">
                    <el-button size="small" text @click="exportMsgToPDF(msg, idx)">
                      <el-icon><Download /></el-icon>
                    </el-button>
                  </el-tooltip>
                </div>

                <!-- 相关问题推荐 -->
                <div v-if="msg.relatedQuestions && msg.relatedQuestions.length > 0" class="related-panel">
                  <div class="related-title"><el-icon><WarnTriangleFilled /></el-icon> 相关问题</div>
                  <div class="related-list">
                    <div
                      v-for="q in msg.relatedQuestions"
                      :key="q"
                      class="related-item"
                      @click="askQuestion(q)"
                    >
                      {{ q }}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

        </div>

        <!-- 输入区域 -->
        <div class="input-area">
          <div class="input-wrapper">
            <el-input
              v-model="inputText"
              type="textarea"
              :autosize="{ minRows: 1, maxRows: 4 }"
              placeholder="请输入您的眼科问题..."
              @keydown.enter.exact.prevent="handleSend"
              :disabled="isLoading"
              resize="none"
            />
            <el-button
              type="primary"
              class="send-btn"
              :icon="Promotion"
              :disabled="!inputText.trim() || isLoading"
              @click="handleSend"
              circle
            />
          </div>
          <div class="input-hint">
            按 Enter 发送 · 支持眼科疾病、治疗、诊断等问题
          </div>
        </div>
      </main>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, nextTick, onMounted, watch, reactive } from 'vue'
import {
  ChatLineSquare, Plus, Delete, Promotion, Document,
  Download, Star, CloseBold, ArrowDown, RefreshRight, Warning,
  View, User, ChatDotRound, Top, Reading, WarnTriangleFilled,
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'
import AppLayout from '@/components/common/AppLayout.vue'
import { sendMessageStream, getConversations, getConversation, deleteConversation, exportConversation, saveMessages } from '@/api/chat.js'
import { submitFeedback } from '@/api/feedback.js'
import { addFavorite, removeFavorite, checkFavorite } from '@/api/favorites.js'

// Markdown 渲染器
const md = new MarkdownIt({
  highlight(str, lang) {
    if (lang && hljs.getLanguage(lang)) {
      try { return hljs.highlight(str, { language: lang }).value } catch (_) {}
    }
    return ''
  },
  html: true,
  linkify: true,
  typographer: true,
})

// 脚注引用后处理：markdown-it 输出后，把 [^N] 替换为上标（此时已是纯文本，不会冲突）
function processCitations(html) {
  return html.replace(/\[\^(\d+)\]/g, '<sup class="cite-ref">[$1]</sup>')
}

function renderMarkdown(text, sources) {
  if (!text) return ''
  let html = md.render(text)
  // 脚注后处理（处理 [^N] 引用标记）
  if (sources && sources.length > 0) {
    html = processCitations(html)
  }
  return html
}
const inputText = ref('')
const messages = ref([])
const conversations = ref([])
const currentConvId = ref(null)
const isLoading = ref(false)
const messagesRef = ref(null)
const currentController = ref(null)
const currentConvData = ref(null)
const isStreaming = ref(false)

// 推荐问题
const suggestQuestions = [
  '什么是青光眼？有哪些症状？',
  '糖尿病视网膜病变如何治疗？',
  '白内障手术后需要注意什么？',
  '干眼症的原因和预防方法？',
  '近视发展到多少度需要手术？',
  '什么是黄斑变性？如何早期发现？',
]

function scrollToBottom() {
  nextTick(() => {
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  })
}

// 展开/收起详情
function toggleDetail(msg) {
  msg.detailExpanded = !msg.detailExpanded
  scrollToBottom()
}

// 加载阶段文字
function phaseText(phase) {
  return phase === 'searching' ? '正在检索知识库...' : '正在生成回答...'
}

// 检索决策提示文字
function retrievalDecisionText(decision) {
  const map = {
    proceed: '已检索到相关参考资料',
    retry: '检索结果不足，已进行二次检索',
    fallback: '知识库暂无相关资料，基于通用知识回答',
  }
  return map[decision] || ''
}

// 渐进式答案解析函数（用于历史消息回显）
function parseProgressiveFromContent(rawText) {
  if (!rawText) return { conclusion: '', detail: '', parsed: false }
  const conclusionMatch = rawText.match(/##\s*简要结论\s*([\s\S]*?)(?=##\s*详细解释|$)/i)
  const detailMatch = rawText.match(/##\s*详细解释\s*([\s\S]*?)$/i)
  if (conclusionMatch && detailMatch) {
    return {
      conclusion: conclusionMatch[1].trim(),
      detail: detailMatch[1].trim(),
      parsed: true,
    }
  }
  return { conclusion: '', detail: '', parsed: false }
}

function createNewChat() {
  currentConvId.value = null
  currentConvData.value = null
  messages.value = []
  inputText.value = ''
}

function askQuestion(q) {
  inputText.value = q
  handleSend()
}

function handleSend() {
  const question = inputText.value.trim()
  if (!question || isLoading.value) return

  messages.value.push({ role: 'user', content: question })
  inputText.value = ''
  isLoading.value = true
  isStreaming.value = true
  scrollToBottom()

  const assistantMsg = reactive({
    role: 'assistant',
    content: '',
    sources: [],
    relatedQuestions: [],
    feedback: null,
    favorited: false,
    id: null,
    conclusion: '',
    detail: '',
    detailExpanded: false,
    detailParsed: false,
    retrievalDecision: null,
    phase: 'searching',
    _buffer: '',
  })
  messages.value.push(assistantMsg)

  // 防止 SSE 'done' 事件被重复处理
  let doneHandled = false

  // 渐进式答案解析
  function parseProgressive(rawText) {
    const conclusionMatch = rawText.match(/##\s*简要结论\s*([\s\S]*?)(?=##\s*详细解释|$)/i)
    const detailMatch = rawText.match(/##\s*详细解释\s*([\s\S]*?)$/i)
    if (conclusionMatch && detailMatch) {
      assistantMsg.conclusion = conclusionMatch[1].trim()
      assistantMsg.detail = detailMatch[1].trim()
      assistantMsg.content = rawText
    } else {
      assistantMsg.conclusion = ''
      assistantMsg.detail = ''
      assistantMsg.content = rawText
    }
    assistantMsg.detailExpanded = false
    assistantMsg.detailParsed = true
  }

  currentController.value = sendMessageStream(
    { question, conversation_id: currentConvId.value, top_k: 5 },
    {
      onContent(chunk) {
        assistantMsg.phase = null
        assistantMsg.content += chunk
        assistantMsg._buffer += chunk
        if (!assistantMsg.detailParsed) {
          parseProgressive(assistantMsg._buffer)
        }
        scrollToBottom()
      },
      onSources(sources, convId, retrievalDecision, searchResults, contextCount) {
        assistantMsg.sources = sources || []
        if (convId) currentConvId.value = convId
        if (retrievalDecision) assistantMsg.retrievalDecision = retrievalDecision
        assistantMsg.phase = 'thinking'
      },
      onRelated(questions) {
        assistantMsg.relatedQuestions = questions || []
      },
      async onDone(fullText, responseTimeMs) {
        // 防止重复触发
        if (doneHandled) return
        doneHandled = true

        assistantMsg.phase = null
        parseProgressive(fullText)
        assistantMsg.content = fullText
        isLoading.value = false
        isStreaming.value = false
        scrollToBottom()

        // 显式调用后端保存接口
        try {
          const res = await saveMessages({
            conversation_id: currentConvId.value,
            question,
            answer: fullText,
            sources: assistantMsg.sources,
            retrieval_decision: assistantMsg.retrievalDecision,
            search_results: [],
            context_count: assistantMsg.sources.length,
            response_time_ms: responseTimeMs || 0,
          })
          if (res.conversation_id) {
            currentConvId.value = res.conversation_id
          }
          if (res.message_id) {
            assistantMsg.id = res.message_id
          }
        } catch (_) {}

        await loadConversations()
      },
      onError(err) {
        if (doneHandled) return
        doneHandled = true
        isLoading.value = false
        isStreaming.value = false
        assistantMsg.phase = null
        assistantMsg.content = `抱歉，请求出错: ${err.message}\n\n请确认后端已启动并已配置 LLM_API_KEY。`
        ElMessage.error('请求失败，请检查网络或API配置')
      },
    }
  )
}

// 切换会话
async function switchConversation(convId) {
  if (isStreaming.value) return  // 流进行中禁止切换，避免覆盖消息
  currentConvId.value = convId
  try {
    const data = await getConversation(convId)
    currentConvData.value = data
    messages.value = (data.messages || []).map(m => {
      const parsed = parseProgressiveFromContent(m.content || '')
      return {
        role: m.role,
        content: m.content,
        sources: m.sources || [],
        relatedQuestions: [],
        id: m.id,
        feedback: null,
        favorited: false,
        conclusion: parsed.conclusion,
        detail: parsed.detail,
        detailExpanded: false,
        detailParsed: parsed.parsed,
        retrievalDecision: null,
      }
    })
    scrollToBottom()
  } catch (e) {
    ElMessage.error('加载会话失败')
  }
}

// 删除会话
async function removeConversation(convId) {
  try {
    await deleteConversation(convId)
    conversations.value = conversations.value.filter(c => c.id !== convId)
    if (currentConvId.value === convId) createNewChat()
    ElMessage.success('会话已删除')
  } catch (e) {
    ElMessage.error('删除失败')
  }
}

// 导出会话
async function exportCurrentConv(conv) {
  try {
    const data = await getConversation(conv.id)
    exportConversation(data)
  } catch (_) {
    ElMessage.error('导出失败')
  }
}

// 加载会话列表
async function loadConversations() {
  try {
    conversations.value = await getConversations()
  } catch (_) {}
}

// ── 反馈 ──────────────────────────────────────
async function handleFeedback(msg, rating) {
  if (!msg.id) return
  try {
    await submitFeedback(msg.id, rating)
    msg.feedback = rating
    ElMessage.success(rating === 1 ? '感谢您的正向反馈！' : '感谢反馈，我们会持续改进')
  } catch (_) {
    ElMessage.error('反馈提交失败')
  }
}

// ── 收藏 ──────────────────────────────────────
async function handleFavorite(msg) {
  if (!msg.id) return
  try {
    if (msg.favorited) {
      // 取消收藏需要 favorite_id，先查
      const res = await checkFavorite(msg.id)
      if (res.favorite_id) {
        await removeFavorite(res.favorite_id)
        msg.favorited = false
        ElMessage.success('已取消收藏')
      }
    } else {
      await addFavorite(msg.id)
      msg.favorited = true
      ElMessage.success('收藏成功')
    }
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '操作失败')
  }
}

// ── PDF 导出 ──────────────────────────────────────
function exportMsgToPDF(msg, idx) {
  let question = ''
  for (let i = idx - 1; i >= 0; i--) {
    if (messages.value[i].role === 'user') {
      question = messages.value[i].content
      break
    }
  }

  const rawContent = msg.content || ''
  const answerId = rawContent
  const htmlContent = md.render(answerId)
  const sources = msg.sources || []
  const date = new Date().toLocaleString('zh-CN')

  const sourcesHtml = sources.length > 0 ? `
    <div class="sources-block">
      <div class="block-label">参考来源</div>
      <ul class="sources-list">
        ${sources.map((s, i) => `<li><span class="src-num">[${i + 1}]</span> ${s.title}（相关度 ${(s.score * 100).toFixed(0)}%）</li>`).join('')}
      </ul>
    </div>` : ''

  const html = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>眼科问答报告</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", Arial, sans-serif;
    font-size: 14px;
    line-height: 1.8;
    color: #1e293b;
    background: #fff;
    padding: 48px 56px;
    max-width: 800px;
    margin: 0 auto;
  }
  .report-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    padding-bottom: 16px;
    margin-bottom: 28px;
    border-bottom: 2px solid #3b82f6;
  }
  .brand { font-size: 18px; font-weight: 700; color: #1e40af; }
  .brand-sub { font-size: 11px; color: #64748b; margin-top: 2px; }
  .report-date { font-size: 12px; color: #94a3b8; }
  .block-label {
    font-size: 11px;
    font-weight: 700;
    color: #3b82f6;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 8px;
  }
  .question-block {
    background: #f0f7ff;
    border-left: 4px solid #3b82f6;
    border-radius: 0 8px 8px 0;
    padding: 14px 18px;
    margin-bottom: 24px;
  }
  .question-text {
    font-size: 16px;
    font-weight: 600;
    color: #1e293b;
    line-height: 1.6;
  }
  .answer-block { margin-bottom: 24px; }
  .answer-content { color: #1e293b; }
  .answer-content h1, .answer-content h2 {
    font-size: 15px; font-weight: 700;
    color: #1e293b; margin: 18px 0 8px;
    padding-bottom: 4px; border-bottom: 1px solid #e2e8f0;
  }
  .answer-content h3 { font-size: 14px; font-weight: 600; margin: 14px 0 6px; }
  .answer-content p { margin-bottom: 10px; }
  .answer-content ul, .answer-content ol { padding-left: 20px; margin-bottom: 10px; }
  .answer-content li { margin-bottom: 4px; }
  .answer-content strong { font-weight: 700; color: #0f172a; }
  .answer-content em { color: #475569; }
  .answer-content code {
    background: #f1f5f9; padding: 1px 5px;
    border-radius: 3px; font-family: monospace; font-size: 12px;
  }
  .answer-content blockquote {
    border-left: 3px solid #3b82f6; padding: 8px 14px;
    background: #f8fafc; margin: 10px 0; color: #475569;
  }
  .sources-block {
    margin-bottom: 24px;
    padding: 14px 18px;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
  }
  .sources-list { padding-left: 0; list-style: none; }
  .sources-list li { font-size: 12px; color: #475569; padding: 3px 0; }
  .src-num { color: #3b82f6; font-weight: 600; margin-right: 6px; }
  .report-footer {
    margin-top: 32px;
    padding-top: 14px;
    border-top: 1px solid #e2e8f0;
    font-size: 11px;
    color: #94a3b8;
    text-align: center;
  }
  @media print {
    body { padding: 0; }
    @page { margin: 20mm 18mm; }
  }
</style>
</head>
<body>
  <div class="report-header">
    <div>
      <div class="brand">EyeRAG</div>
      <div class="brand-sub">眼科医疗知识问答系统</div>
    </div>
    <div class="report-date">导出时间：${date}</div>
  </div>

  <div class="question-block">
    <div class="block-label">问题</div>
    <div class="question-text">${question.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</div>
  </div>

  <div class="answer-block">
    <div class="block-label">AI 回答</div>
    <div class="answer-content">${htmlContent}</div>
  </div>

  ${sourcesHtml}

  <div class="report-footer">
    本内容由 EyeRAG 眼科医疗知识问答系统基于 RAG 检索增强生成技术自动生成，仅供参考，不构成正式医疗建议。
  </div>
</body>
</html>`

  const win = window.open('', '_blank', 'width=900,height=700')
  if (!win) {
    ElMessage.warning('请允许弹出窗口以导出 PDF')
    return
  }
  win.document.write(html)
  win.document.close()
  win.focus()
  setTimeout(() => win.print(), 600)
}

onMounted(() => {
  loadConversations()
})

watch(() => messages.value.length, scrollToBottom)
</script>

<style scoped>
.chat-container {
  display: flex;
  height: 100%;
  background: #f4f6f9;
}

/* ===== 左侧会话栏 ===== */
.conversation-sidebar {
  width: 220px;
  background: #fafbfc;
  border-right: 1px solid #edf0f5;
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  padding: 16px;
  border-bottom: 1px solid #e8ecf1;
}

.new-chat-btn {
  width: 100%;
  border-radius: 8px;
  font-size: 14px;
  height: 40px;
}

.conversation-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.conv-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  color: #475569;
  font-size: 13px;
  transition: all 0.2s;
  margin-bottom: 2px;
}

.conv-item:hover { background: #f1f5f9; }

.conv-item.active {
  background: #eff6ff;
  color: #2563eb;
  font-weight: 500;
}

.conv-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.conv-actions {
  display: flex;
  gap: 2px;
  opacity: 0;
  transition: opacity 0.2s;
}

.conv-item:hover .conv-actions { opacity: 1; }

.conv-action-btn {
  color: #94a3b8;
  font-size: 14px;
  padding: 2px;
  border-radius: 4px;
  cursor: pointer;
}

.conv-action-btn:hover { color: #64748b; background: #e2e8f0; }
.conv-delete:hover { color: #ef4444 !important; }

.conv-empty {
  text-align: center;
  padding: 40px 16px;
  color: #94a3b8;
  font-size: 13px;
}

/* ===== 主聊天区域 ===== */
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.messages-area {
  flex: 1;
  overflow-y: auto;
  padding: 24px 0;
}

/* ===== 欢迎界面 ===== */
.welcome-screen {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 40px;
  text-align: center;
}

.welcome-icon { font-size: 56px; margin-bottom: 16px; }
.welcome-screen h2 { font-size: 22px; color: #1e293b; margin-bottom: 8px; }
.welcome-screen p { color: #64748b; margin-bottom: 32px; }

.suggest-questions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  max-width: 600px;
}

.suggest-item {
  background: #fff;
  border: 1px solid #e8ecf2;
  border-radius: 10px;
  padding: 11px 14px;
  font-size: 13px;
  color: #4b5563;
  cursor: pointer;
  transition: all 0.18s;
  text-align: left;
  line-height: 1.5;
  border-left: 3px solid transparent;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}

.suggest-item:hover {
  border-left-color: #3b82f6;
  border-color: #bfdbfe;
  color: #1d4ed8;
  background: #f8faff;
  box-shadow: 0 3px 8px rgba(59,130,246,0.1);
  transform: translateY(-1px);
}

/* ===== 消息气泡 ===== */
.message-wrapper {
  display: flex;
  gap: 12px;
  padding: 12px 24px;
  max-width: 900px;
  margin: 0 auto;
  width: 100%;
}

.message-wrapper.user { flex-direction: row-reverse; }

.message-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #f1f5f9;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
  color: #64748b;
}

.message-body { flex: 1; min-width: 0; }

.message-text {
  display: inline-block;
  padding: 12px 16px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.7;
  max-width: 100%;
  word-break: break-word;
}

.user-text {
  background: #3b82f6;
  color: #fff;
  border-radius: 12px 12px 4px 12px;
  text-align: left;
}

.user .message-body {
  text-align: right;
}

.assistant-text {
  background: #fff;
  color: #1e293b;
  border: 1px solid #e8ecf1;
  border-radius: 4px 12px 12px 12px;
  box-shadow: 0 2px 6px rgba(0,0,0,0.06);
}

/* ===== 来源面板 ===== */
.sources-panel {
  margin-top: 10px;
  padding: 10px 14px;
  background: #f8fafc;
  border-radius: 8px;
  border: 1px solid #e8ecf1;
}

.sources-title {
  font-size: 12px;
  color: #64748b;
  margin-bottom: 6px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.sources-list { display: flex; flex-wrap: wrap; gap: 6px; }

.source-tag { cursor: default; }

/* ===== 操作栏（反馈+收藏） ===== */
.msg-actions {
  display: flex;
  gap: 4px;
  margin-top: 8px;
  padding-left: 2px;
}

/* ===== 相关问题推荐 ===== */
.related-panel {
  margin-top: 12px;
  padding: 12px 14px;
  background: linear-gradient(135deg, #eff6ff, #f0fdf4);
  border-radius: 10px;
  border: 1px solid #bfdbfe;
}

.related-title {
  font-size: 12px;
  color: #3b82f6;
  font-weight: 600;
  margin-bottom: 8px;
}

.related-list { display: flex; flex-direction: column; gap: 6px; }

.related-item {
  font-size: 13px;
  color: #1e40af;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
  transition: background 0.2s;
}

.related-item:hover { background: rgba(59,130,246,0.1); }

/* ===== 加载阶段指示 ===== */
.loading-phase {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  background: #fff;
  border: 1px solid #e8ecf1;
  border-radius: 4px 12px 12px 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}

.phase-dots {
  display: flex;
  align-items: center;
  gap: 4px;
}

.phase-dots span {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #3b82f6;
  animation: phaseBounce 1.4s infinite ease-in-out;
}

.phase-dots span:nth-child(1) { animation-delay: 0s; }
.phase-dots span:nth-child(2) { animation-delay: 0.2s; }
.phase-dots span:nth-child(3) { animation-delay: 0.4s; }

.phase-text {
  font-size: 13px;
  color: #64748b;
  font-style: italic;
}

@keyframes phaseBounce {
  0%, 80%, 100% { transform: scale(0.7); opacity: 0.4; }
  40% { transform: scale(1.1); opacity: 1; }
}

/* ===== 输入区域 ===== */
.input-area {
  padding: 14px 24px 16px;
  border-top: 1px solid #edf0f5;
  background: #fff;
  box-shadow: 0 -2px 12px rgba(0,0,0,0.04);
}

.input-wrapper {
  display: flex;
  gap: 10px;
  align-items: flex-end;
}

.send-btn { flex-shrink: 0; }

.input-hint {
  font-size: 11px;
  color: #94a3b8;
  margin-top: 6px;
  text-align: center;
}

/* ===== 检索决策提示 ===== */
.retrieval-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: 20px;
  font-size: 11px;
  margin-bottom: 8px;
  font-weight: 500;
}
.retrieval-badge.proceed {
  background: #f0fdf4;
  color: #15803d;
  border: 1px solid #bbf7d0;
}
.retrieval-badge.retry {
  background: #fffbeb;
  color: #b45309;
  border: 1px solid #fde68a;
}
.retrieval-badge.fallback {
  background: #fef2f2;
  color: #b91c1c;
  border: 1px solid #fecaca;
}

/* ===== 渐进式答案 ===== */
.progressive-answer {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.answer-conclusion {
  background: #fff;
  border: 1px solid #e8ecf1;
  border-radius: 12px 12px 0 0;
  padding: 14px 16px;
}

.conclusion-label {
  font-size: 11px;
  color: #3b82f6;
  font-weight: 600;
  margin-bottom: 8px;
  letter-spacing: 0.5px;
}

.conclusion-text {
  font-size: 14px;
  line-height: 1.7;
  color: #1e293b;
}
/* 结论内 markdown 样式 */
.conclusion-text :deep(p) { margin: 0 0 8px; }
.conclusion-text :deep(p:last-child) { margin-bottom: 0; }
.conclusion-text :deep(ul), .conclusion-text :deep(ol) { padding-left: 18px; margin: 6px 0; }
.conclusion-text :deep(li) { margin-bottom: 3px; }
.conclusion-text :deep(strong) { color: #1e293b; }
.conclusion-text :deep(code) { background: #e2e8f0; padding: 1px 5px; border-radius: 3px; font-size: 12px; }

.expand-btn {
  margin-top: 10px;
  color: #3b82f6;
  font-size: 12px;
}

.answer-detail {
  background: #fafafa;
  border: 1px solid #e8ecf1;
  border-top: none;
  border-radius: 0 0 12px 12px;
  padding: 14px 16px;
}

.detail-label {
  font-size: 11px;
  color: #64748b;
  font-weight: 600;
  margin-bottom: 8px;
  letter-spacing: 0.5px;
}

.detail-text {
  font-size: 14px;
  line-height: 1.7;
  color: #374151;
}
/* 详情内 markdown 样式 */
.detail-text :deep(p) { margin: 0 0 8px; }
.detail-text :deep(p:last-child) { margin-bottom: 0; }
.detail-text :deep(ul), .detail-text :deep(ol) { padding-left: 18px; margin: 6px 0; }
.detail-text :deep(li) { margin-bottom: 3px; }
.detail-text :deep(strong) { color: #1e293b; }
.detail-text :deep(code) { background: #e2e8f0; padding: 1px 5px; border-radius: 3px; font-size: 12px; }
.detail-text :deep(table) { width: 100%; border-collapse: collapse; font-size: 13px; }
.detail-text :deep(th) { background: #f1f5f9; padding: 8px 12px; text-align: left; border-bottom: 1px solid #e8ecf1; }
.detail-text :deep(td) { padding: 8px 12px; border-bottom: 1px solid #f1f5f9; }

/* ===== 脚注引用样式 ===== */
.cite-ref {
  color: #3b82f6;
  font-weight: 600;
  font-size: 11px;
  vertical-align: super;
  cursor: default;
}

/* ===== Markdown 样式 ===== */
.assistant-text :deep(p) { margin: 0 0 10px; }
.assistant-text :deep(p:last-child) { margin-bottom: 0; }
.assistant-text :deep(h1),
.assistant-text :deep(h2),
.assistant-text :deep(h3),
.assistant-text :deep(h4) {
  color: #1e293b;
  margin: 16px 0 8px;
  font-weight: 600;
}
.assistant-text :deep(h1) { font-size: 18px; }
.assistant-text :deep(h2) { font-size: 16px; border-bottom: 1px solid #e8ecf1; padding-bottom: 6px; }
.assistant-text :deep(h3) { font-size: 15px; }
.assistant-text :deep(h4) { font-size: 14px; }
.assistant-text :deep(ul),
.assistant-text :deep(ol) {
  padding-left: 20px;
  margin: 8px 0;
}
.assistant-text :deep(li) { margin-bottom: 5px; line-height: 1.6; }
.assistant-text :deep(li p) { margin: 0; }
.assistant-text :deep(code) {
  background: #f1f5f9;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13px;
  font-family: 'JetBrains Mono', 'Fira Code', 'Courier New', monospace;
}
.assistant-text :deep(pre) {
  background: #1e293b;
  color: #e2e8f0;
  padding: 16px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 12px 0;
}
.assistant-text :deep(pre code) {
  background: none;
  padding: 0;
  color: inherit;
  font-size: 13px;
}
.assistant-text :deep(strong) { color: #0f172a; font-weight: 600; }
.assistant-text :deep(em) { color: #475569; font-style: italic; }
.assistant-text :deep(blockquote) {
  margin: 10px 0;
  padding: 10px 14px;
  border-left: 3px solid #3b82f6;
  background: #f8fafc;
  border-radius: 0 6px 6px 0;
  color: #475569;
}
.assistant-text :deep(blockquote p) { margin: 0; }
.assistant-text :deep(hr) { border: none; border-top: 1px solid #e8ecf1; margin: 16px 0; }
.assistant-text :deep(a) { color: #3b82f6; text-decoration: none; }
.assistant-text :deep(a:hover) { text-decoration: underline; }
.assistant-text :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 12px 0;
  font-size: 13px;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid #e8ecf1;
}
.assistant-text :deep(thead tr) { background: #f1f5f9; }
.assistant-text :deep(th) {
  padding: 10px 14px;
  text-align: left;
  font-weight: 600;
  color: #374151;
  border-bottom: 2px solid #e8ecf1;
}
.assistant-text :deep(td) {
  padding: 9px 14px;
  border-bottom: 1px solid #f1f5f9;
  color: #475569;
  line-height: 1.5;
}
.assistant-text :deep(tbody tr:last-child td) { border-bottom: none; }
.assistant-text :deep(tbody tr:hover) { background: #fafafa; }
</style>
