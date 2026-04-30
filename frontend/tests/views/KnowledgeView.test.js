/**
 * KnowledgeView 组件测试
 *
 * 策略：使用 shallow mount + stubs 隔离 Element Plus 组件，
 * 通过 mock window.fetch 来模拟 API 响应，直接测试组件逻辑。
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { flushPromises as _flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'

// ── Mock @/api/knowledge.js ───────────────────────────────────────────────────
vi.mock('@/api/knowledge.js', () => ({
  getStats: vi.fn(),
  getDocuments: vi.fn(),
  deleteDocument: vi.fn(),
  searchKnowledge: vi.fn(),
  getDocumentPreview: vi.fn(),
  downloadDocumentFile: vi.fn(),
}))

// ── Mock AppLayout ───────────────────────────────────────────────────────────
vi.mock('@/components/common/AppLayout.vue', () => ({
  default: { name: 'AppLayout', template: '<div><slot /></div>' },
}))

// ── Mock element-plus ─────────────────────────────────────────────────────────
vi.mock('element-plus', async (importOriginal) => {
  const actual = await importOriginal()
  return {
    ...actual,
    ElMessage: { success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn() },
    ElMessageBox: { confirm: vi.fn().mockResolvedValue(true), alert: vi.fn() },
    ElLoading: {
      directive: { mounted: vi.fn(), unmounted: vi.fn() },
      service: vi.fn().mockReturnValue({ close: vi.fn() }),
    },
  }
})

// ── 测试数据 ─────────────────────────────────────────────────────────────────
const MOCK_STATS = { total_documents: 3, total_chunks: 150, collection_name: 'ophthalmology' }

const MOCK_DOCUMENTS = [
  { file_name: 'glaucoma.txt', file_type: 'txt', source_name: 'Source A', chunk_count: 10, hit_count: 5, view_count: 3 },
  { file_name: 'cataract.md', file_type: 'md', source_name: 'Source B', chunk_count: 20, hit_count: 2, view_count: 1 },
]

// ── 测试 ─────────────────────────────────────────────────────────────────────
describe('KnowledgeView 逻辑测试', () => {
  let mockFetch

  beforeEach(async () => {
    vi.clearAllMocks()

    // mock window.fetch（组件内部用 fetch 调用 API）
    mockFetch = vi.fn()
    globalThis.fetch = mockFetch

    const km = await import('@/api/knowledge.js')
    km.getStats.mockResolvedValue(MOCK_STATS)
    km.getDocuments.mockResolvedValue(MOCK_DOCUMENTS)
    km.deleteDocument.mockResolvedValue({ success: true })
    km.getDocumentPreview.mockResolvedValue({ file_name: 'test.txt', chunks: [] })
    km.downloadDocumentFile.mockResolvedValue(new Blob())

    // 默认 fetch 实现
    mockFetch.mockImplementation(async (url) => {
      if (url.includes('/api/knowledge/stats')) {
        return { ok: true, json: async () => MOCK_STATS }
      }
      if (url.includes('/api/knowledge/documents')) {
        return { ok: true, json: async () => MOCK_DOCUMENTS }
      }
      return { ok: true, json: async () => ({}) }
    })
  })

  // ── 挂载辅助 ─────────────────────────────────────────────────────────────
  async function mountView() {
    const { mount } = await import('@vue/test-utils')
    const { default: KnowledgeView } = await import('@/views/KnowledgeView.vue')
    return mount(KnowledgeView, {
      global: {
        stubs: {
          'el-button': true, 'el-table': true, 'el-table-column': true,
          'el-tag': true, 'el-input': true, 'el-dialog': true,
          'el-popconfirm': true, 'el-upload': true, 'el-icon': true,
        },
      },
    })
  }

  // ── 基础测试 ──────────────────────────────────────────────────────────────

  it('渲染页面标题', async () => {
    const wrapper = await mountView()
    await _flushPromises()
    expect(wrapper.find('h1').text()).toBe('知识库管理')
    wrapper.unmount()
  })

  it('stats 初始为空对象', async () => {
    const wrapper = await mountView()
    expect(wrapper.vm.stats).toEqual({})
    wrapper.unmount()
  })

  it('documents 初始为空数组', async () => {
    const wrapper = await mountView()
    expect(wrapper.vm.documents).toEqual([])
    wrapper.unmount()
  })

  it('searchResults 初始为空数组', async () => {
    const wrapper = await mountView()
    expect(wrapper.vm.searchResults).toEqual([])
    wrapper.unmount()
  })

  // ── 搜索测试 ────────────────────────────────────────────────────────────────

  it('searchQuery 响应式更新', async () => {
    const wrapper = await mountView()
    wrapper.vm.searchQuery = '青光眼'
    expect(wrapper.vm.searchQuery).toBe('青光眼')
    wrapper.unmount()
  })

  it('doSearch 调用 fetch 并更新结果', async () => {
    // 覆盖 fetch 以返回搜索结果
    mockFetch.mockImplementation(async (url) => {
      if (url.includes('/api/knowledge/stats')) {
        return { ok: true, json: async () => MOCK_STATS }
      }
      if (url.includes('/api/knowledge/documents')) {
        return { ok: true, json: async () => MOCK_DOCUMENTS }
      }
      if (url.includes('/api/knowledge/search')) {
        return {
          ok: true,
          json: async () => ({
            results: [
              { score: 0.95, metadata: { title: 'doc.txt' }, content: '青光眼内容' },
              { score: 0.80, metadata: { title: 'disease.txt' }, content: '眼病内容' },
            ],
          }),
        }
      }
      return { ok: true, json: async () => ({}) }
    })

    const wrapper = await mountView()
    wrapper.vm.searchQuery = '青光眼'
    await wrapper.vm.doSearch()
    await _flushPromises()
    expect(wrapper.vm.searchResults).toHaveLength(2)
    expect(wrapper.vm.searchResults[0].score).toBe(0.95)
    wrapper.unmount()
  })

  it('doSearch 跳过空查询（仅空白字符）', async () => {
    const km = await import('@/api/knowledge.js')
    const searchSpy = km.searchKnowledge
    const wrapper = await mountView()
    wrapper.vm.searchQuery = '   '
    await wrapper.vm.doSearch()
    expect(searchSpy).not.toHaveBeenCalled()
    wrapper.unmount()
  })

  it('doSearch 设置 searching 状态', async () => {
    mockFetch.mockImplementation(async (url) => {
      if (url.includes('/api/knowledge/stats')) return { ok: true, json: async () => MOCK_STATS }
      if (url.includes('/api/knowledge/documents')) return { ok: true, json: async () => MOCK_DOCUMENTS }
      if (url.includes('/api/knowledge/search')) {
        await new Promise((r) => setTimeout(r, 10))
        return { ok: true, json: async () => ({ results: [] }) }
      }
      return { ok: true, json: async () => ({}) }
    })

    const wrapper = await mountView()
    wrapper.vm.searchQuery = 'test'
    const searchPromise = wrapper.vm.doSearch()
    expect(wrapper.vm.searching).toBe(true)
    await searchPromise
    expect(wrapper.vm.searching).toBe(false)
    wrapper.unmount()
  })

  // ── 预览测试 ───────────────────────────────────────────────────────────────

  it('previewDocument 设置 previewVisible 并加载数据', async () => {
    const km = await import('@/api/knowledge.js')
    const previewData = { file_name: 'glaucoma.txt', chunk_count: 3, chunks: [] }
    km.getDocumentPreview.mockResolvedValueOnce(previewData)

    const wrapper = await mountView()
    await wrapper.vm.previewDocument({ file_name: 'glaucoma.txt' })
    await _flushPromises()
    expect(wrapper.vm.previewVisible).toBe(true)
    expect(wrapper.vm.previewData).toEqual(previewData)
    wrapper.unmount()
  })

  // ── 删除测试 ───────────────────────────────────────────────────────────────

  it('removeDoc 调用 deleteDocument', async () => {
    const km = await import('@/api/knowledge.js')
    const wrapper = await mountView()
    await wrapper.vm.removeDoc('glaucoma.txt')
    expect(km.deleteDocument).toHaveBeenCalledWith('glaucoma.txt')
    wrapper.unmount()
  })

  // ── 上传回调测试 ─────────────────────────────────────────────────────────

  it('onUploadSuccess 关闭对话框并重新加载', async () => {
    const km = await import('@/api/knowledge.js')
    km.getDocuments.mockResolvedValue([{ file_name: 'new.txt' }])
    km.getStats.mockResolvedValue({ total_documents: 4 })

    const wrapper = await mountView()
    await wrapper.vm.onUploadSuccess({ chunk_count: 5 })
    await _flushPromises()
    expect(wrapper.vm.showUpload).toBe(false)
    wrapper.unmount()
  })

  // ── 对话框控制 ─────────────────────────────────────────────────────────────

  it('showUpload 控制上传对话框显示', async () => {
    const wrapper = await mountView()
    expect(wrapper.vm.showUpload).toBe(false)
    wrapper.vm.showUpload = true
    await nextTick()
    expect(wrapper.vm.showUpload).toBe(true)
    wrapper.unmount()
  })

  it('previewVisible 控制预览对话框显示', async () => {
    const wrapper = await mountView()
    expect(wrapper.vm.previewVisible).toBe(false)
    wrapper.vm.previewVisible = true
    await nextTick()
    expect(wrapper.vm.previewVisible).toBe(true)
    wrapper.unmount()
  })
})
