import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/admin/dashboard'
    },
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/LoginView.vue'),
      meta: { requiresGuest: true }
    },
    {
      path: '/admin',
      component: () => import('@/layouts/AdminLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          redirect: '/admin/dashboard'
        },
        {
          path: 'dashboard',
          name: 'Dashboard',
          component: () => import('@/views/admin/DashboardView.vue')
        },
        {
          path: 'reviews/mr',
          name: 'MRReviews',
          component: () => import('@/views/admin/MRReviewsView.vue')
        },
        {
          path: 'reviews/push',
          name: 'PushReviews',
          component: () => import('@/views/admin/PushReviewsView.vue')
        },
        {
          path: 'statistics',
          name: 'Statistics',
          component: () => import('@/views/admin/StatisticsView.vue')
        },
        {
          path: 'settings',
          name: 'Settings',
          component: () => import('@/views/admin/SettingsView.vue')
        }
      ]
    },
    // 兼容旧路由
    {
      path: '/dashboard',
      redirect: '/admin/dashboard'
    }
  ]
})

// Navigation guards
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()

  // If auth is not initialized yet, try to restore from localStorage
  if (!authStore.isInitialized) {
    try {
      await authStore.restoreAuth()
    } catch (error) {
      console.error('Failed to restore auth:', error)
    }
  }

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next('/login')
  } else if (to.meta.requiresGuest && authStore.isAuthenticated) {
    next('/dashboard')
  } else {
    next()
  }
})

export default router