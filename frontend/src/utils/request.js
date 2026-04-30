/**
 * Axios 请求封装
 * 功能: 自动附加 JWT Token, 统一错误处理, 401 自动跳转登录
 */

import axios from 'axios'
import { ElMessage } from 'element-plus'
import { getToken, clearAuth } from '@/api/auth.js'

const request = axios.create({
    baseURL: '/api',
    timeout: 30000,
})

// 请求拦截器 - 自动附加 Token
request.interceptors.request.use(
    (config) => {
        const token = getToken()
        if (token) {
            config.headers.Authorization = `Bearer ${token}`
        }
        return config
    },
    (error) => Promise.reject(error)
)

// 响应拦截器 - 统一错误处理
request.interceptors.response.use(
    (response) => response.data,
    (error) => {
        const status = error.response?.status
        const message = error.response?.data?.detail || error.message

        if (status === 401) {
            clearAuth()
            window.location.href = '/login'
            ElMessage.error('登录已过期，请重新登录')
        } else if (status === 403) {
            ElMessage.error('权限不足')
        } else if (status === 422) {
            ElMessage.error('请求参数错误')
        } else {
            ElMessage.error(message || '请求失败')
        }

        return Promise.reject(error)
    }
)

export default request
