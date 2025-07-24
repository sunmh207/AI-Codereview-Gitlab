import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import Login from '@/views/Login.vue'
import Dashboard from '@/views/Dashboard.vue'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    name: 'Dashboard',
    component: Dashboard,
    meta: { requiresAuth: true }
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()

  // 如果认证还未初始化，先初始化
  if (!authStore.authInitialized) {
    authStore.initAuth()
  }

  console.log('Route guard:', {
    to: to.path,
    requiresAuth: to.meta.requiresAuth,
    isLoggedIn: authStore.isLoggedIn,
    user: authStore.user
  })

  if (to.meta.requiresAuth && !authStore.isLoggedIn) {
    console.log('Redirecting to login: not authenticated')
    next('/login')
  } else if (to.name === 'Login' && authStore.isLoggedIn) {
    console.log('Redirecting to dashboard: already authenticated')
    next('/')
  } else {
    next()
  }
})

export default router
