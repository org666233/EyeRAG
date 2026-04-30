/**
 * Vitest 全局设置
 * mock 所有外部依赖，使测试文件可以专注于业务逻辑。
 */
import { vi } from 'vitest'

// Browser globals
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(() => ({
    matches: false,
    media: '',
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})
