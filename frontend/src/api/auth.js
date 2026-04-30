/**
 * 认证 API 模块
 */

import request from '@/utils/request'

const BASE = '/auth'

export function register(data) {
    return request.post(`${BASE}/register`, data)
}

export function login(data) {
    return request.post(`${BASE}/login`, data)
}

export function getMe() {
    return request.get(`${BASE}/me`)
}

/** Token 管理 */
export function setToken(token) {
    localStorage.setItem('token', token)
}

export function getToken() {
    return localStorage.getItem('token')
}

export function removeToken() {
    localStorage.removeItem('token')
}

export function setUserInfo(user) {
    localStorage.setItem('userInfo', JSON.stringify(user))
}

export function getUserInfo() {
    const s = localStorage.getItem('userInfo')
    return s ? JSON.parse(s) : null
}

export function clearAuth() {
    removeToken()
    localStorage.removeItem('userInfo')
}
