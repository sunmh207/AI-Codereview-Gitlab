<template>
  <el-container class="admin-layout">
    <!-- 侧边栏 -->
    <el-aside :width="sidebarCollapsed ? '64px' : '200px'" class="admin-sidebar">
      <div class="sidebar-header">
        <div v-if="!sidebarCollapsed" class="logo">
          <el-icon><Service /></el-icon>
          <span>AI代码审查</span>
        </div>
        <el-button
          :icon="sidebarCollapsed ? Expand : Fold"
          circle
          size="small"
          @click="toggleSidebar"
          class="collapse-btn"
        />
      </div>
      
      <el-menu
        :default-active="activeMenu"
        :collapse="sidebarCollapsed"
        :unique-opened="true"
        router
        class="sidebar-menu"
      >
        <el-menu-item index="/admin/dashboard">
          <el-icon><Monitor /></el-icon>
          <template #title>仪表盘</template>
        </el-menu-item>
        
        <el-sub-menu index="reviews">
          <template #title>
            <el-icon><Document /></el-icon>
            <span>代码审查</span>
          </template>
          <el-menu-item index="/admin/reviews/mr">
            <el-icon><FolderOpened /></el-icon>
            <template #title>合并请求</template>
          </el-menu-item>
          <el-menu-item v-if="pushReviewEnabled" index="/admin/reviews/push">
            <el-icon><Upload /></el-icon>
            <template #title>代码推送</template>
          </el-menu-item>
        </el-sub-menu>
        
        <el-menu-item index="/admin/statistics">
          <el-icon><TrendCharts /></el-icon>
          <template #title>统计分析</template>
        </el-menu-item>
        
        <el-menu-item index="/admin/settings">
          <el-icon><Setting /></el-icon>
          <template #title>系统设置</template>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <!-- 主内容区 -->
    <el-container class="admin-main">
      <!-- 顶部导航 -->
      <el-header class="admin-header">
        <div class="header-left">
          <el-breadcrumb separator="/">
            <el-breadcrumb-item v-for="item in breadcrumbs" :key="item.path" :to="item.path">
              {{ item.title }}
            </el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        
        <div class="header-right">
          <el-dropdown @command="handleUserCommand">
            <span class="user-dropdown">
              <el-avatar :size="32" :icon="UserFilled" />
              <span class="username">{{ authStore.username }}</span>
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">
                  <el-icon><User /></el-icon>
                  个人资料
                </el-dropdown-item>
                <el-dropdown-item command="settings">
                  <el-icon><Setting /></el-icon>
                  设置
                </el-dropdown-item>
                <el-dropdown-item divided command="logout">
                  <el-icon><SwitchButton /></el-icon>
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <!-- 内容区域 -->
      <el-main class="admin-content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Service, Expand, Fold, Monitor, Document, TrendCharts, Setting,
  UserFilled, User, ArrowDown, SwitchButton, Upload, FolderOpened
} from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

// 侧边栏状态
const sidebarCollapsed = ref(false)
const pushReviewEnabled = ref(true) // 从配置获取

// 当前激活的菜单
const activeMenu = computed(() => route.path)

// 面包屑导航
const breadcrumbs = computed(() => {
  const pathSegments = route.path.split('/').filter(Boolean)
  const breadcrumbMap: Record<string, string> = {
    'admin': '管理后台',
    'dashboard': '仪表盘',
    'reviews': '代码审查',
    'mr': '合并请求',
    'push': '代码推送',
    'statistics': '统计分析',
    'settings': '系统设置'
  }
  
  return pathSegments.map((segment, index) => ({
    title: breadcrumbMap[segment] || segment,
    path: '/' + pathSegments.slice(0, index + 1).join('/')
  }))
})

// 切换侧边栏
const toggleSidebar = () => {
  sidebarCollapsed.value = !sidebarCollapsed.value
}

// 用户操作处理
const handleUserCommand = async (command: string) => {
  switch (command) {
    case 'profile':
      ElMessage.info('个人资料功能开发中...')
      break
    case 'settings':
      router.push('/admin/settings')
      break
    case 'logout':
      try {
        await ElMessageBox.confirm('确定要退出登录吗？', '提示', {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning'
        })
        await authStore.logout()
        ElMessage.success('已退出登录')
        router.push('/login')
      } catch (error) {
        // 用户取消或退出失败
      }
      break
  }
}

// 监听路由变化，自动收起移动端侧边栏
watch(() => route.path, () => {
  if (window.innerWidth <= 768) {
    sidebarCollapsed.value = true
  }
})
</script>

<style scoped>
.admin-layout {
  height: 100vh;
}

.admin-sidebar {
  background: #001529;
  transition: width 0.3s;
}

.sidebar-header {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  border-bottom: 1px solid #1f1f1f;
}

.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  color: white;
  font-size: 16px;
  font-weight: bold;
}

.collapse-btn {
  background: transparent;
  border: 1px solid #434343;
  color: #fff;
}

.collapse-btn:hover {
  background: #1890ff;
  border-color: #1890ff;
}

.sidebar-menu {
  border: none;
  background: #001529;
}

.sidebar-menu :deep(.el-menu-item) {
  color: rgba(255, 255, 255, 0.65);
}

.sidebar-menu :deep(.el-menu-item:hover) {
  background-color: #1890ff;
  color: #fff;
}

.sidebar-menu :deep(.el-menu-item.is-active) {
  background-color: #1890ff;
  color: #fff;
}

.sidebar-menu :deep(.el-sub-menu__title) {
  color: rgba(255, 255, 255, 0.65);
}

.sidebar-menu :deep(.el-sub-menu__title:hover) {
  color: #fff;
}

.admin-main {
  background: #f0f2f5;
}

.admin-header {
  background: white;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  height: 60px;
}

.header-left {
  flex: 1;
}

.header-right {
  display: flex;
  align-items: center;
}

.user-dropdown {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 8px 12px;
  border-radius: 6px;
  transition: background-color 0.3s;
}

.user-dropdown:hover {
  background-color: #f5f5f5;
}

.username {
  font-size: 14px;
  color: #333;
}

.admin-content {
  padding: 24px;
  overflow-y: auto;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .admin-sidebar {
    position: fixed;
    z-index: 1000;
    height: 100vh;
  }
  
  .admin-main {
    margin-left: 0;
  }
  
  .admin-header {
    padding: 0 16px;
  }
  
  .admin-content {
    padding: 16px;
  }
}
</style>