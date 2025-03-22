<template>
  <div class="config-container">
    <el-card class="config-card">
      <template #header>
        <div class="card-header">
          <span>配置管理</span>
          <div class="header-actions">
            <el-button type="primary" @click="handleReload" :loading="reloading">
              重载配置
            </el-button>
            <el-button type="success" @click="handleSave" :loading="saving">
              保存配置
            </el-button>
          </div>
        </div>
      </template>

      <el-form :model="configForm" label-width="120px">
        <el-form-item label="Push Review 启用">
          <el-switch v-model="configForm.PUSH_REVIEW_ENABLED" />
        </el-form-item>

        <el-form-item label="支持的文件扩展名">
          <el-input v-model="configForm.SUPPORTED_EXTENSIONS" />
        </el-form-item>

        <el-form-item label="代码审查最大长度">
          <el-input-number v-model="configForm.REVIEW_MAX_LENGTH" :min="1000" :max="10000" />
        </el-form-item>

        <el-form-item label="日报定时任务">
          <el-input v-model="configForm.REPORT_CRONTAB_EXPRESSION" placeholder="0 18 * * 1-5" />
        </el-form-item>

        <el-form-item label="GitLab URL">
          <el-input v-model="configForm.GITLAB_URL" />
        </el-form-item>

        <el-form-item label="GitLab Access Token">
          <el-input v-model="configForm.GITLAB_ACCESS_TOKEN" type="password" show-password />
        </el-form-item>

        <el-form-item label="LLM Provider">
          <el-select v-model="configForm.LLM_PROVIDER">
            <el-option label="OpenAI" value="openai" />
            <el-option label="智谱AI" value="zhipuai" />
            <el-option label="DeepSeek" value="deepseek" />
            <el-option label="Ollama" value="ollama" />
          </el-select>
        </el-form-item>

        <el-form-item label="ZhipuAI API Key">
          <el-input v-model="configForm.ZHIPUAI_API_KEY" type="password" show-password />
        </el-form-item>

        <el-form-item label="ZhipuAI Model">
          <el-input v-model="configForm.ZHIPUAI_API_MODEL" />
        </el-form-item>

        <el-form-item label="OpenAI API Key">
          <el-input v-model="configForm.OPENAI_API_KEY" type="password" show-password />
        </el-form-item>

        <el-form-item label="OpenAI Model">
          <el-input v-model="configForm.OPENAI_API_MODEL" />
        </el-form-item>

        <el-form-item label="DeepSeek API Key">
          <el-input v-model="configForm.DEEPSEEK_API_KEY" type="password" show-password />
        </el-form-item>

        <el-form-item label="DeepSeek Model">
          <el-input v-model="configForm.DEEPSEEK_API_MODEL" />
        </el-form-item>

        <el-form-item label="Ollama API URL">
          <el-input v-model="configForm.OLLAMA_API_URL" />
        </el-form-item>

        <el-form-item label="Ollama Model">
          <el-input v-model="configForm.OLLAMA_API_MODEL" />
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

export default {
  name: 'Config',
  setup() {
    const configForm = ref({})
    const reloading = ref(false)
    const saving = ref(false)

    const loadConfig = async () => {
      try {
        const response = await axios.get('/api/config')
        configForm.value = response.data
      } catch (error) {
        ElMessage.error('加载配置失败')
        console.error('加载配置失败:', error)
      }
    }

    const handleReload = async () => {
      reloading.value = true
      try {
        const response = await axios.post('/api/reload-config')
        ElMessage.success(response.data.message)
        await loadConfig() // 重新加载配置
      } catch (error) {
        ElMessage.error('重载配置失败')
        console.error('重载配置失败:', error)
      } finally {
        reloading.value = false
      }
    }

    const handleSave = async () => {
      saving.value = true
      try {
        const response = await axios.post('/api/save-config', configForm.value)
        ElMessage.success(response.data.message)
        await handleReload() // 保存后自动重载
      } catch (error) {
        ElMessage.error('保存配置失败')
        console.error('保存配置失败:', error)
      } finally {
        saving.value = false
      }
    }

    onMounted(() => {
      loadConfig()
    })

    return {
      configForm,
      reloading,
      saving,
      handleReload,
      handleSave
    }
  }
}
</script>

<style scoped>
.config-container {
  padding: 20px;
}

.config-card {
  max-width: 800px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.el-form-item {
  margin-bottom: 22px;
}
</style> 