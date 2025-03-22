<template>
  <div class="login-container">
    <div class="login-box">
      <h2>登录</h2>
      <div v-if="isDefaultCredentials" class="warning-message">
        <p>安全提示：检测到默认用户名和密码为 'admin'，存在安全风险！</p>
        <p>请立即修改：</p>
        <ol>
          <li>打开 `.env` 文件</li>
          <li>修改 `DASHBOARD_USER` 和 `DASHBOARD_PASSWORD` 变量</li>
          <li>保存并重启应用</li>
        </ol>
        <p>当前用户名: {{ username }}, 当前密码: {{ password }}</p>
      </div>
      <div class="form-group">
        <input type="text" v-model="username" placeholder="用户名" />
      </div>
      <div class="form-group">
        <input type="password" v-model="password" placeholder="密码" />
      </div>
      <div v-if="error" class="error-message">{{ error }}</div>
      <button @click="handleLogin">登录</button>
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
      isDefaultCredentials: false
    }
  },
  methods: {
    async handleLogin() {
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
          this.$emit('login-success', data)
        } else {
          this.error = data.message || '登录失败，请稍后重试'
        }
      } catch (err) {
        this.error = '登录失败，请稍后重试'
        console.error('登录错误:', err)
      }
    }
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background-color: #f5f5f5;
}

.login-box {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  width: 100%;
  max-width: 400px;
}

.form-group {
  margin-bottom: 1rem;
}

input {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
}

button {
  width: 100%;
  padding: 0.5rem;
  background-color: #4CAF50;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 1rem;
  cursor: pointer;
}

button:hover {
  background-color: #45a049;
}

.error-message {
  color: red;
  margin-bottom: 1rem;
}

.warning-message {
  background-color: #fff3cd;
  border: 1px solid #ffeeba;
  color: #856404;
  padding: 1rem;
  border-radius: 4px;
  margin-bottom: 1rem;
}

.warning-message ol {
  margin: 0.5rem 0;
  padding-left: 1.5rem;
}
</style> 