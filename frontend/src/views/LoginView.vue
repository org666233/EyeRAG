<template>
  <div class="login-page">
    <div class="login-container">
      <!-- 左侧品牌区 -->
      <div class="brand-panel">
        <div class="brand-content">
          <div class="brand-icon">👁️</div>
          <h1>眼科医疗知识问答系统</h1>
          <p>基于 RAG 检索增强生成技术</p>
          <div class="brand-features">
            <div class="feature"><span>🔍</span> 智能语义检索</div>
            <div class="feature"><span>📚</span> 专业知识库</div>
            <div class="feature"><span>🤖</span> AI 智能问答</div>
            <div class="feature"><span>📄</span> 答案溯源</div>
          </div>
        </div>
      </div>

      <!-- 右侧表单区 -->
      <div class="form-panel">
        <div class="form-content">
          <h2>{{ isRegister ? '创建账号' : '欢迎回来' }}</h2>
          <p class="form-subtitle">{{ isRegister ? '注册一个新账号开始使用' : '登录以继续使用系统' }}</p>

          <el-form ref="formRef" :model="form" :rules="rules" @submit.prevent="handleSubmit">
            <el-form-item prop="username">
              <el-input
                v-model="form.username"
                placeholder="用户名"
                size="large"
                :prefix-icon="User"
              />
            </el-form-item>

            <el-form-item v-if="isRegister" prop="real_name">
              <el-input
                v-model="form.real_name"
                placeholder="真实姓名（选填）"
                size="large"
                :prefix-icon="UserFilled"
              />
            </el-form-item>

            <el-form-item prop="password">
              <el-input
                v-model="form.password"
                type="password"
                placeholder="密码"
                size="large"
                :prefix-icon="Lock"
                show-password
                @keydown.enter="handleSubmit"
              />
            </el-form-item>

            <el-button
              type="primary"
              size="large"
              class="submit-btn"
              :loading="loading"
              @click="handleSubmit"
            >
              {{ isRegister ? '注 册' : '登 录' }}
            </el-button>
          </el-form>

          <div class="form-footer">
            <span>{{ isRegister ? '已有账号？' : '还没有账号？' }}</span>
            <el-link type="primary" @click="isRegister = !isRegister">
              {{ isRegister ? '去登录' : '立即注册' }}
            </el-link>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { User, Lock, UserFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { login, register, setToken, setUserInfo } from '@/api/auth.js'

const router = useRouter()
const formRef = ref(null)
const loading = ref(false)
const isRegister = ref(false)

const form = reactive({
  username: '',
  password: '',
  real_name: '',
})

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '用户名3-50个字符', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少6个字符', trigger: 'blur' },
  ],
}

async function handleSubmit() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    const api = isRegister.value ? register : login
    const res = await api({
      username: form.username,
      password: form.password,
      ...(isRegister.value && form.real_name ? { real_name: form.real_name } : {}),
    })

    setToken(res.access_token)
    setUserInfo({ id: res.user_id, username: res.username, role: res.role || 'user' })

    ElMessage.success(isRegister.value ? '注册成功！' : '登录成功！')
    router.push('/chat')
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '操作失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  width: 100vw;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-container {
  display: flex;
  width: 860px;
  min-height: 520px;
  background: #fff;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

/* 左侧品牌区 */
.brand-panel {
  flex: 1;
  background: linear-gradient(135deg, #1e3a5f 0%, #0d1b2a 100%);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
}

.brand-content {
  text-align: center;
}

.brand-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.brand-panel h1 {
  font-size: 22px;
  font-weight: 600;
  margin-bottom: 8px;
}

.brand-panel p {
  font-size: 14px;
  color: #94a3b8;
  margin-bottom: 32px;
}

.brand-features {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  text-align: left;
}

.feature {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #cbd5e1;
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 8px;
}

/* 右侧表单区 */
.form-panel {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
}

.form-content {
  width: 100%;
  max-width: 320px;
}

.form-content h2 {
  font-size: 24px;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 4px;
}

.form-subtitle {
  font-size: 14px;
  color: #64748b;
  margin-bottom: 32px;
}

.submit-btn {
  width: 100%;
  height: 44px;
  font-size: 16px;
  border-radius: 8px;
  margin-top: 8px;
}

.form-footer {
  text-align: center;
  margin-top: 20px;
  font-size: 13px;
  color: #64748b;
}
</style>
