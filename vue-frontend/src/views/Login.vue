<template>
  <div class="login-container">
    <div class="login-box">
      <div class="platform-icon">🤖</div>
      <h1 class="login-title">AI代码审查平台</h1>
      
      <!-- 安全提示 -->
      <el-alert
        v-if="showSecurityWarning"
        title="安全提示"
        type="warning"
        :closable="false"
        show-icon
        class="security-alert"
      >
        <template #default>
          <div>
            检测到默认用户名和密码为 'admin'，存在安全风险！<br>
            请立即修改：<br>
            1. 打开 `.env` 文件<br>
            2. 修改 `DASHBOARD_USER` 和 `DASHBOARD_PASSWORD` 变量<br>
            3. 保存并重启应用<br>
            <strong>当前用户名: admin, 当前密码: admin</strong>
          </div>
        </template>
      </el-alert>

      <el-form
        ref="loginFormRef"
        :model="loginForm"
        :rules="rules"
        class="login-form"
        @submit.prevent="handleLogin"
      >
        <el-form-item prop="username">
          <el-input
            v-model="loginForm.username"
            placeholder="👤 用户名"
            size="large"
            :prefix-icon="User"
          />
        </el-form-item>
        
        <el-form-item prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="🔑 密码"
            size="large"
            :prefix-icon="Lock"
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        
        <el-form-item>
          <el-checkbox v-model="loginForm.remember">
            记住密码
          </el-checkbox>
        </el-form-item>
        
        <el-form-item>
          <el-button
            type="primary"
            size="large"
            :loading="loading"
            class="login-button"
            @click="handleLogin"
          >
            登 录
          </el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import type { LoginForm } from '@/types'

const router = useRouter()
const authStore = useAuthStore()

const loginFormRef = ref<FormInstance>()
const loading = ref(false)

const loginForm = reactive<LoginForm>({
  username: 'admin',
  password: 'admin',
  remember: false
})

const rules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' }
  ]
}

const showSecurityWarning = computed(() => {
  return loginForm.username === 'admin' && loginForm.password === 'admin'
})

const handleLogin = async () => {
  if (!loginFormRef.value) return

  try {
    await loginFormRef.value.validate()
    loading.value = true

    const result = await authStore.login(loginForm)

    if (result.success) {
      ElMessage.success(result.message || '登录成功')
      router.push('/')
    } else {
      ElMessage.error(result.message || '登录失败')
    }
  } catch (error) {
    console.error('Login validation failed:', error)
    ElMessage.error('登录过程中发生错误')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background-color: #f0f2f6;
  padding: 20px;
}

.login-box {
  background: white;
  border-radius: 15px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  padding: 40px;
  width: 100%;
  max-width: 400px;
}

.platform-icon {
  font-size: 3.5rem;
  text-align: center;
  margin-bottom: 0.5rem;
}

.login-title {
  text-align: center;
  color: #2E4053;
  margin: 0.5rem 0 2rem 0;
  font-size: 2.2rem;
  font-weight: bold;
}

.security-alert {
  margin-bottom: 20px;
}

.login-form {
  margin-top: 20px;
}

.login-button {
  width: 100%;
  border-radius: 20px;
  padding: 12px;
  font-size: 16px;
  background-color: #4CAF50;
  border-color: #4CAF50;
}

.login-button:hover {
  background-color: #45a049;
  border-color: #45a049;
}
</style>
