<template>
  <div id="app">
    <router-view />
  </div>
</template>

<script setup lang="ts">
// Auth restoration is now handled in router guards
// to avoid race conditions with navigation
</script>

<style>
#app {
  height: 100vh;
  width: 100vw;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', '微软雅黑', Arial, sans-serif;
  background-color: #f0f2f5;
}
</style>