<template>
  <div class="login-container">
    <div class="login-card">
      <div class="login-header">
        <div class="login-icon">🤖</div>
        <h1 class="login-title">AI代码审查平台</h1>
        <p class="login-subtitle">基于大模型的自动化代码审查工具</p>
      </div>

      <!-- Security warning for default credentials -->
      <el-alert
        v-if="showDefaultCredentialsWarning"
        title="安全提示"
        type="warning"
        :closable="false"
        show-icon
        style="margin-bottom: 20px;"
      >
        <template #default>
          <p>检测到默认用户名和密码为 'admin'，存在安全风险！</p>
          <br />
          <p>请立即修改：</p>
          <ol style="margin: 10px 0; padding-left: 20px;">
            <li>打开 <code>.env</code> 文件</li>
            <li>修改 <code>DASHBOARD_USER</code> 和 <code>DASHBOARD_PASSWORD</code> 变量</li>
            <li>保存并重启应用</li>
          </ol>
          <p>当前用户名: <code>admin</code>, 当前密码: <code>admin</code></p>
        </template>
      </el-alert>

      <el-form
        ref="loginFormRef"
        :model="loginForm"
        :rules="loginRules"
        size="large"
        @submit.prevent="handleLogin"
      >
        <el-form-item prop="username">
          <el-input
            v-model="loginForm.username"
            placeholder="用户名"
            :prefix-icon="User"
            clearable
            @keyup.enter="handleLogin"
          />
        </el-form-item>

        <el-form-item prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="密码"
            :prefix-icon="Lock"
            show-password
            clearable
            @keyup.enter="handleLogin"
          />
        </el-form-item>

        <el-form-item>
          <el-checkbox v-model="loginForm.rememberMe">
            记住密码
          </el-checkbox>
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            size="large"
            style="width: 100%;"
            :loading="loading"
            @click="handleLogin"
          >
            {{ loading ? '登录中...' : '登 录' }}
          </el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ElMessage, type FormInstance } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'

const router = useRouter()
const authStore = useAuthStore()

const loginFormRef = ref<FormInstance>()
const loading = ref(false)
const showDefaultCredentialsWarning = ref(false)

// Form data
const loginForm = ref({
  username: '',
  password: '',
  rememberMe: false
})

// Form validation rules
const loginRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' }
  ]
}

// Load saved credentials
const loadSavedCredentials = () => {
  const savedUsername = localStorage.getItem('saved_username')
  const savedPassword = localStorage.getItem('saved_password')

  if (savedUsername) {
    loginForm.value.username = savedUsername
    loginForm.value.rememberMe = true
  }
  if (savedPassword) {
    loginForm.value.password = savedPassword
  }

  // Show warning if using default credentials
  if (savedUsername === 'admin' || loginForm.value.username === 'admin') {
    showDefaultCredentialsWarning.value = true
  }
}

// Handle login
const handleLogin = async () => {
  if (!loginFormRef.value) return

  try {
    const valid = await loginFormRef.value.validate()
    if (!valid) return

    loading.value = true

    await authStore.login(loginForm.value.username, loginForm.value.password)

    // Save credentials if remember me is checked
    if (loginForm.value.rememberMe) {
      localStorage.setItem('saved_username', loginForm.value.username)
      localStorage.setItem('saved_password', loginForm.value.password)
    } else {
      localStorage.removeItem('saved_username')
      localStorage.removeItem('saved_password')
    }

    ElMessage.success('登录成功')
    router.push('/dashboard')
  } catch (error: any) {
    ElMessage.error(error.message || '登录失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadSavedCredentials()
})
</script>

<style scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.login-card {
  width: 100%;
  max-width: 400px;
  padding: 40px;
  background: white;
  border-radius: 15px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
}

.login-header {
  text-align: center;
  margin-bottom: 30px;
}

.login-icon {
  font-size: 60px;
  margin-bottom: 20px;
}

.login-title {
  font-size: 28px;
  font-weight: bold;
  color: #2E4053;
  margin-bottom: 10px;
}

.login-subtitle {
  color: #7f8c8d;
  font-size: 14px;
}

code {
  background-color: #f1f2f6;
  padding: 2px 4px;
  border-radius: 3px;
  font-family: 'Courier New', monospace;
}

@media (max-width: 768px) {
  .login-container {
    padding: 16px;
  }

  .login-card {
    padding: 30px 20px;
  }

  .login-title {
    font-size: 24px;
  }

  .login-icon {
    font-size: 50px;
  }
}
</style>