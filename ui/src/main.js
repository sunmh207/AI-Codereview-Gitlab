import { createApp } from 'vue'
import App from './App.vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import 'bootstrap/dist/css/bootstrap.min.css'
import 'bootstrap/dist/js/bootstrap.bundle.min.js'
import axios from 'axios'

// 配置axios默认值
axios.defaults.baseURL = (import.meta.env && import.meta.env.VITE_APP_API_URL) || window.location.origin
axios.defaults.withCredentials = true

const app = createApp(App)
app.use(ElementPlus)
app.mount('#app') 