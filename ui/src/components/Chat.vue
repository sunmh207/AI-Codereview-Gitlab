<template>
  <div class="chat-container">
    <div class="header">
      <h2>AI 助手</h2>
      <div class="header-buttons">
        <button class="context-button" @click="toggleContext" :class="{ 'active': useContext }">
          <span class="context-icon">💬</span>
          {{ useContext ? '启用上下文' : '禁用上下文' }}
        </button>
        <button class="config-button" @click="showPromptConfig = true">
          <span class="config-icon">⚙️</span>
          提示词配置
        </button>
        <button class="back-button" @click="goBack">
          <span class="back-icon">←</span>
          返回
        </button>
      </div>
    </div>

    <div class="chat-messages" ref="messagesContainer">
      <div v-for="(message, index) in messages" :key="index" 
           :class="['message', message.role === 'user' ? 'user-message' : 'assistant-message']">
        <div class="message-content">
          <div v-if="message.role === 'assistant'" class="avatar">🤖</div>
          <div v-else class="avatar">👤</div>
          <div class="text">{{ message.content }}</div>
        </div>
      </div>
    </div>

    <div class="input-container">
      <textarea 
        v-model="userInput" 
        @keydown.enter.prevent="sendMessage"
        placeholder="输入您的问题..."
        :disabled="isLoading"
      ></textarea>
      <button 
        @click="sendMessage" 
        :disabled="isLoading || !userInput.trim()"
        class="send-button"
      >
        {{ isLoading ? '发送中...' : '发送' }}
      </button>
    </div>

    <!-- 提示词配置对话框 -->
    <el-dialog
      v-model="showPromptConfig"
      title="提示词配置"
      width="50%"
    >
      <el-form :model="promptConfig" label-width="120px">
        <el-form-item label="System Message">
          <el-input
            type="textarea"
            v-model="promptConfig.system_message"
            :rows="4"
            placeholder="输入系统提示词，用于设定AI助手的角色和行为"
          />
        </el-form-item>
        <el-form-item label="User Message">
          <el-input
            type="textarea"
            v-model="promptConfig.user_message"
            :rows="4"
            placeholder="输入用户提示词模板，使用 {message} 作为用户输入的占位符"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showPromptConfig = false">取消</el-button>
          <el-button type="primary" @click="savePromptConfig">
            保存
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ElMessage } from 'element-plus'

export default {
  name: 'ChatComponent',
  data() {
    return {
      messages: [],
      userInput: '',
      isLoading: false,
      showPromptConfig: false,
      useContext: false,
      promptConfig: {
        system_message: '',
        user_message: ''
      }
    }
  },
  methods: {
    goBack() {
      this.$router.push({
        path: '/',
        replace: true
      })
    },
    async sendMessage() {
      if (this.isLoading || !this.userInput.trim()) return

      const userMessage = this.userInput.trim()
      
      if (!this.useContext) {
        this.messages = []
      }
      
      this.messages.push({
        role: 'user',
        content: userMessage
      })
      this.userInput = ''
      this.isLoading = true

      try {
        const response = await fetch('/api/chat', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            message: userMessage,
            system_message: this.promptConfig.system_message,
            user_message: this.promptConfig.user_message,
            use_context: this.useContext
          })
        })

        if (!response.ok) {
          throw new Error('Network response was not ok')
        }

        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        let assistantMessage = ''

        this.messages.push({
          role: 'assistant',
          content: ''
        })

        let done = false
        while (!done) {
          const { done: isDone, value } = await reader.read()
          done = isDone

          const chunk = decoder.decode(value)
          const lines = chunk.split('\n')
          
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6))
                if (data.content) {
                  assistantMessage += data.content
                  this.messages[this.messages.length - 1].content = assistantMessage
                  this.$nextTick(() => {
                    this.scrollToBottom()
                  })
                }
              } catch (e) {
                console.error('Error parsing SSE data:', e)
              }
            }
          }
        }
      } catch (error) {
        console.error('Error:', error)
        this.messages.push({
          role: 'assistant',
          content: '抱歉，发生了一些错误，请稍后重试。'
        })
      } finally {
        this.isLoading = false
        this.saveChatHistory()
      }
    },
    scrollToBottom() {
      const container = this.$refs.messagesContainer
      container.scrollTop = container.scrollHeight
    },
    savePromptConfig() {
      localStorage.setItem('chat_prompt_config', JSON.stringify(this.promptConfig))
      this.showPromptConfig = false
      ElMessage.success('提示词配置已保存')
    },
    toggleContext() {
      this.useContext = !this.useContext
      if (!this.useContext) {
        this.messages = []
        localStorage.removeItem('chat_history')
      }
    },
    saveChatHistory() {
      localStorage.setItem('chat_history', JSON.stringify(this.messages))
    }
  },
  mounted() {
    this.scrollToBottom()
    const savedConfig = localStorage.getItem('chat_prompt_config')
    if (savedConfig) {
      this.promptConfig = JSON.parse(savedConfig)
    }
    const savedHistory = localStorage.getItem('chat_history')
    if (savedHistory) {
      this.messages = JSON.parse(savedHistory)
    }
  }
}
</script>

<style scoped>
.chat-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  padding: 20px;
  background-color: #f5f5f5;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header-buttons {
  display: flex;
  gap: 10px;
}

.context-button {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background-color: #2196F3;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: background-color 0.3s;
}

.context-button:hover {
  background-color: #1976D2;
}

.context-button.active {
  background-color: #1565C0;
}

.context-icon {
  font-size: 16px;
}

.config-button {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background-color: #4CAF50;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: background-color 0.3s;
}

.config-button:hover {
  background-color: #45a049;
}

.config-icon {
  font-size: 16px;
}

.back-button {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background-color: #666;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: background-color 0.3s;
}

.back-button:hover {
  background-color: #555;
}

.back-icon {
  font-size: 16px;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background-color: white;
  border-radius: 8px;
  margin-bottom: 20px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.message {
  margin-bottom: 20px;
}

.message-content {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  max-width: 80%;
}

.user-message .message-content {
  margin-left: auto;
  flex-direction: row-reverse;
}

.avatar {
  font-size: 24px;
  min-width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #f0f0f0;
  border-radius: 50%;
}

.text {
  padding: 12px 16px;
  border-radius: 12px;
  background-color: #f0f0f0;
  word-wrap: break-word;
}

.user-message .text {
  background-color: #4CAF50;
  color: white;
}

.input-container {
  display: flex;
  gap: 12px;
  padding: 20px;
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

textarea {
  flex: 1;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  resize: none;
  height: 60px;
  font-family: inherit;
}

.send-button {
  padding: 0 24px;
  background-color: #4CAF50;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: background-color 0.3s;
}

.send-button:hover:not(:disabled) {
  background-color: #45a049;
}

.send-button:disabled {
  background-color: #cccccc;
  cursor: not-allowed;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>