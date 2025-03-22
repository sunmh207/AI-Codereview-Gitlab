<template>
  <div class="login-container">
    <div class="login-box">
      <h2>登录</h2>
      <div v-if="showWarning" class="warning-message">
        <div class="warning-icon">⚠️</div>
        <div class="warning-content">
          <h3>安全提示</h3>
          <p>检测到默认用户名和密码为 'admin'，存在安全风险！</p>
          <p>请立即修改：</p>
          <ol>
            <li>打开 `.env` 文件</li>
            <li>修改 `DASHBOARD_USER` 和 `DASHBOARD_PASSWORD` 变量</li>
            <li>保存并重启应用</li>
          </ol>
          <p class="credentials-info">当前用户名: <code>{{ username }}</code>, 当前密码: <code>{{ password }}</code></p>
          <div class="warning-actions">
            <button class="warning-button" @click="confirmContinue">确认继续使用</button>
          </div>
        </div>
      </div>
      <div class="form-group">
        <label for="username">用户名</label>
        <input 
          id="username"
          type="text" 
          v-model="username" 
          placeholder="请输入用户名"
          @keyup.enter="handleLogin"
        />
      </div>
      <div class="form-group">
        <label for="password">密码</label>
        <input 
          id="password"
          type="password" 
          v-model="password" 
          placeholder="请输入密码"
          @keyup.enter="handleLogin"
        />
      </div>
      <div v-if="error" class="error-message">{{ error }}</div>
      <button @click="handleLogin" :disabled="isLoading">
        {{ isLoading ? '登录中...' : '登录' }}
      </button>
    </div>
  </div>
</template>

<script>
export default {
  name: 'Login',
  data() {
    return {
      username: '',
      password: '',
      error: '',
      isLoading: false,
      isDefaultCredentials: false,
      showWarning: false
    }
  },
  created() {
    // 检查是否为默认凭证
    this.checkDefaultCredentials()
  },
  methods: {
    checkDefaultCredentials() {
      return this.username === 'admin' && this.password === 'admin'
    },
    async handleLogin() {
      if (!this.username || !this.password) {
        this.error = '请输入用户名和密码'
        return
      }
      
      this.isLoading = true
      this.error = ''
      
      try {
        const response = await fetch('/login', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            username: this.username,
            password: this.password
          })
        })
        
        const data = await response.json()
        
        if (response.ok) {
          // 检查是否为默认凭证
          this.isDefaultCredentials = this.checkDefaultCredentials()
          if (this.isDefaultCredentials) {
            // 如果是默认凭证，显示警告信息
            this.showWarning = true
            return
          }
          // 如果不是默认凭证，直接登录成功
          this.$emit('login-success', data)
        } else {
          this.error = data.message || '登录失败，请稍后重试'
        }
      } catch (err) {
        this.error = '登录失败，请稍后重试'
        console.error('登录错误:', err)
      } finally {
        this.isLoading = false
      }
    },
    // 确认继续使用默认凭证
    confirmContinue() {
      this.showWarning = false
      this.$emit('login-success', {
        username: this.username,
        password: this.password
      })
    }
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background-color: #f5f5f5;
  padding: 1rem;
}

.login-box {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  width: 100%;
  max-width: 400px;
}

h2 {
  text-align: center;
  color: #333;
  margin-bottom: 2rem;
}

.form-group {
  margin-bottom: 1.5rem;
}

label {
  display: block;
  margin-bottom: 0.5rem;
  color: #666;
  font-weight: 500;
}

input {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
  transition: border-color 0.2s;
}

input:focus {
  outline: none;
  border-color: #4CAF50;
  box-shadow: 0 0 0 2px rgba(76, 175, 80, 0.1);
}

button {
  width: 100%;
  padding: 0.75rem;
  background-color: #4CAF50;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 1rem;
  cursor: pointer;
  transition: background-color 0.2s;
}

button:hover:not(:disabled) {
  background-color: #45a049;
}

button:disabled {
  background-color: #cccccc;
  cursor: not-allowed;
}

.error-message {
  color: #dc3545;
  margin-bottom: 1rem;
  padding: 0.5rem;
  background-color: #f8d7da;
  border: 1px solid #f5c6cb;
  border-radius: 4px;
}

.warning-message {
  background-color: #fff3cd;
  border: 1px solid #ffeeba;
  color: #856404;
  padding: 1rem;
  border-radius: 4px;
  margin-bottom: 1.5rem;
  display: flex;
  gap: 1rem;
}

.warning-icon {
  font-size: 1.5rem;
  flex-shrink: 0;
}

.warning-content {
  flex-grow: 1;
}

.warning-content h3 {
  margin: 0 0 0.5rem 0;
  color: #856404;
  font-size: 1.1rem;
}

.warning-message p {
  margin: 0.5rem 0;
  line-height: 1.5;
}

.warning-message ol {
  margin: 0.5rem 0;
  padding-left: 1.5rem;
}

.warning-message li {
  margin: 0.25rem 0;
  line-height: 1.5;
}

.credentials-info {
  margin-top: 1rem;
  padding-top: 0.5rem;
  border-top: 1px solid rgba(133, 100, 4, 0.2);
}

.credentials-info code {
  background-color: rgba(133, 100, 4, 0.1);
  padding: 0.2rem 0.4rem;
  border-radius: 3px;
  font-family: monospace;
}

.warning-actions {
  margin-top: 1rem;
  text-align: right;
}

.warning-button {
  background-color: #856404;
  color: white;
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
  width: auto;
}

.warning-button:hover {
  background-color: #6b5203;
}
</style> 