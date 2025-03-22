<template>
  <div id="app">
    <Login v-if="!isAuthenticated" @login-success="handleLoginSuccess" />
    <Dashboard v-else />
  </div>
</template>

<script>
import Login from './components/Login.vue'
import Dashboard from './components/Dashboard.vue'

export default {
  name: 'App',
  components: {
    Login,
    Dashboard
  },
  data() {
    return {
      isAuthenticated: false
    }
  },
  methods: {
    handleLoginSuccess(data) {
      this.isAuthenticated = true
      // 存储认证信息
      localStorage.setItem('authToken', data.token)
    }
  },
  created() {
    // 检查是否有已保存的认证信息
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
</style> 