<template>
  <div id="app">
    <Login v-if="!isAuthenticated" @login-success="handleLoginSuccess" />
    <div v-else>
      <el-container>
        <el-header>
          <div class="header-content">
            <h2>AI代码审查系统</h2>
            <el-button type="text" @click="handleLogout">退出登录</el-button>
          </div>
        </el-header>
        <el-main>
          <router-view @exit-config="handleExitConfig"></router-view>
        </el-main>
      </el-container>
    </div>
  </div>
</template>

<script>
import Login from './components/Login.vue'

export default {
  name: 'App',
  components: {
    Login
  },
  data() {
    return {
      isAuthenticated: false
    }
  },
  methods: {
    handleLoginSuccess(data) {
      this.isAuthenticated = true
      localStorage.setItem('authToken', data.token)
      this.$router.push('/')
    },
    handleLogout() {
      this.isAuthenticated = false
      localStorage.removeItem('authToken')
      this.$router.push('/login')
    },
    handleExitConfig() {
      this.$router.push('/')
    }
  },
  created() {
    const token = localStorage.getItem('authToken')
    if (token) {
      this.isAuthenticated = true
    }
  }
}
</script>

<style>
#app {
  font-family: Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: #2c3e50;
  margin: 0;
  padding: 0;
  min-height: 100vh;
  background-color: #f5f5f5;
}

* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

.el-header {
  background-color: #fff;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  padding: 0 20px;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 100%;
}

.el-main {
  padding: 20px;
}
</style> 