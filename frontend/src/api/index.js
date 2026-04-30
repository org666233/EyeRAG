/**
 * API 封装 - 基础接口
 */

import request from '@/utils/request'

/**
 * 健康检查
 */
export function getHealth() {
    return request.get('/health')
}
