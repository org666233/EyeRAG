/**
 * LoginView 组件测试
 * 采用逻辑层测试策略：mock 所有外部依赖，直接测试组件暴露的逻辑。
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'
import { defineComponent, h, ref } from 'vue'

// ── Mock @/api/auth.js ───────────────────────────────────────────────────────
const mockLogin = vi.fn()
const mockRegister = vi.fn()
const mockSetToken = vi.fn()
const mockSetUserInfo = vi.fn()
vi.mock('@/api/auth.js', () => ({
  login: (...args) => mockLogin(...args),
  register: (...args) => mockRegister(...args),
  setToken: (...args) => mockSetToken(...args),
  setUserInfo: (...args) => mockSetUserInfo(...args),
}))

// ── Mock @/utils/request ──────────────────────────────────────────────────────
vi.mock('@/utils/request', () => ({
  default: { get: vi.fn(), post: vi.fn() },
}))

// ── Mock vue-router ─────────────────────────────────────────────────────────
const mockRouterPush = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: mockRouterPush }),
  useRoute: () => ({ path: '/login' }),
}))

// ── Mock element-plus ─────────────────────────────────────────────────────────
vi.mock('element-plus', async (importOriginal) => {
  const actual = await importOriginal()
  return {
    ...actual,
    ElMessage: { success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn() },
    ElMessageBox: { confirm: vi.fn().mockResolvedValue(true), alert: vi.fn() },
  }
})

// ── 可配置 validate 的 el-form stub ──────────────────────────────────────────
function makeElFormStub(validateFn) {
  return defineComponent({
    name: 'ElFormStub',
    props: ['model', 'rules'],
    setup(props, { expose }) {
      expose({
        validate: async () => {
          if (validateFn) return validateFn()
          return true
        },
        validateField: async () => true,
        resetFields: vi.fn(),
        clearValidate: vi.fn(),
        $el: {},
      })
      return () => h('form')
    },
  })
}

// ── 测试数据 ─────────────────────────────────────────────────────────────────
const VALID_LOGIN_RESPONSE = {
  access_token: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9',
  user_id: 1,
  username: 'testuser',
  role: 'user',
}

const VALID_REGISTER_RESPONSE = {
  access_token: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9',
  user_id: 2,
  username: 'newuser',
  role: 'user',
}

// ── 挂载辅助 ─────────────────────────────────────────────────────────────────
async function mountLoginView(validateFn = () => true) {
  const { mount } = await import('@vue/test-utils')
  const { default: LoginView } = await import('@/views/LoginView.vue')

  return mount(LoginView, {
    global: {
      stubs: {
        'el-form': makeElFormStub(validateFn),
        'el-form-item': { template: '<div><slot /></div>' },
        'el-input': { template: '<input />' },
        'el-button': { template: '<button><slot /></button>' },
        'el-link': { template: '<span><slot /></span>' },
      },
      mocks: {
        $router: { push: mockRouterPush },
      },
    },
  })
}

// ── 测试 ─────────────────────────────────────────────────────────────────────
describe('LoginView 逻辑测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('表单基础状态', () => {
    it('form 对象初始状态正确', async () => {
      const wrapper = await mountLoginView()
      expect(wrapper.vm.form.username).toBe('')
      expect(wrapper.vm.form.password).toBe('')
      expect(wrapper.vm.form.real_name).toBe('')
      expect(wrapper.vm.isRegister).toBe(false)
      expect(wrapper.vm.loading).toBe(false)
      wrapper.unmount()
    })

    it('表单数据响应式更新', async () => {
      const wrapper = await mountLoginView()
      wrapper.vm.form.username = 'alice'
      wrapper.vm.form.password = 'secret123'
      expect(wrapper.vm.form.username).toBe('alice')
      expect(wrapper.vm.form.password).toBe('secret123')
      wrapper.unmount()
    })
  })

  describe('模式切换', () => {
    it('isRegister 初始为 false（登录模式）', async () => {
      const wrapper = await mountLoginView()
      expect(wrapper.vm.isRegister).toBe(false)
      wrapper.unmount()
    })

    it('切换到注册模式', async () => {
      const wrapper = await mountLoginView()
      wrapper.vm.isRegister = true
      await nextTick()
      expect(wrapper.vm.isRegister).toBe(true)
      wrapper.unmount()
    })

    it('注册模式包含 real_name 字段', async () => {
      const wrapper = await mountLoginView()
      expect(wrapper.vm.form).toHaveProperty('real_name')
      wrapper.unmount()
    })
  })

  describe('提交逻辑', () => {
    it('登录成功后跳转到 /chat', async () => {
      mockLogin.mockResolvedValueOnce(VALID_LOGIN_RESPONSE)
      const wrapper = await mountLoginView(() => true)

      wrapper.vm.form.username = 'testuser'
      wrapper.vm.form.password = 'password123'
      await wrapper.vm.handleSubmit()
      await flushPromises()

      expect(mockRouterPush).toHaveBeenCalledWith('/chat')
      expect(mockSetToken).toHaveBeenCalledWith(VALID_LOGIN_RESPONSE.access_token)
      wrapper.unmount()
    })

    it('注册成功后跳转到 /chat', async () => {
      mockRegister.mockResolvedValueOnce(VALID_REGISTER_RESPONSE)
      const wrapper = await mountLoginView(() => true)

      wrapper.vm.isRegister = true
      wrapper.vm.form.username = 'newuser'
      wrapper.vm.form.password = 'password123'
      await wrapper.vm.handleSubmit()
      await flushPromises()

      expect(mockRouterPush).toHaveBeenCalledWith('/chat')
      wrapper.unmount()
    })

    it('登录失败不跳转', async () => {
      mockLogin.mockRejectedValueOnce(new Error('用户名或密码错误'))
      const wrapper = await mountLoginView(() => true)

      wrapper.vm.form.username = 'baduser'
      wrapper.vm.form.password = 'badpass'
      await wrapper.vm.handleSubmit()
      await flushPromises()

      expect(mockRouterPush).not.toHaveBeenCalled()
      wrapper.unmount()
    })

    it('表单验证失败时不提交', async () => {
      mockLogin.mockResolvedValueOnce(VALID_LOGIN_RESPONSE)
      const wrapper = await mountLoginView(() => false)

      wrapper.vm.form.username = 'ab'
      wrapper.vm.form.password = 'pass'
      await wrapper.vm.handleSubmit()
      await flushPromises()

      expect(mockLogin).not.toHaveBeenCalled()
      expect(mockRouterPush).not.toHaveBeenCalled()
      wrapper.unmount()
    })

  })
})
