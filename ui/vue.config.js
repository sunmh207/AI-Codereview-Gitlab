const { defineConfig } = require('@vue/cli-service')

module.exports = defineConfig({
  transpileDependencies: true,
  outputDir: 'dist',
  publicPath: '/',
  lintOnSave: false,
  devServer: {
    proxy: {
      '/api': {
        target: process.env.VITE_APP_API_URL || 'http://localhost:5001',
        changeOrigin: true,
        pathRewrite: {
          '^/api': ''
        }
      }
    }
  }
}) 