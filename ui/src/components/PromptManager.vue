<template>
  <div class="prompt-manager">
    <div class="header">
      <h1>Prompt Templates</h1>
      <div class="header-right">
        <el-button icon="el-icon-back" @click="handleBack">返回</el-button>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-container">
      <el-skeleton :rows="5" animated />
    </div>

    <!-- 错误提示 -->
    <el-alert
      v-if="error"
      :title="error"
      type="error"
      show-icon
      @close="error = ''"
    />

    <!-- 空状态 -->
    <el-empty v-if="!loading && prompts.length === 0" description="暂无提示模板">
      <el-button type="primary" @click="showCreateDialog">创建第一个模板</el-button>
    </el-empty>

    <!-- 提示模板列表 -->
    <el-table
      v-if="!loading && prompts.length > 0"
      :data="prompts"
      style="width: 100%"
      border
    >
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="name" label="名称" width="180">
        <template #default="{ row }">
          <el-input
            v-model="row.name"
            placeholder="模板名称"
            @blur="updatePrompt(row)"
          />
        </template>
      </el-table-column>
      <el-table-column prop="content" label="内容">
        <template #default="{ row }">
          <div class="content-editor">
            <el-input
              v-model="row.content"
              type="textarea"
              :rows="6"
              :autosize="{ minRows: 4, maxRows: 15 }"
              placeholder="模板内容"
            />
            <div class="content-actions">
              <el-button
                type="primary"
                size="small"
                @click="updatePrompt(row)"
                icon="el-icon-check"
              >
                保存
              </el-button>
            </div>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="150" align="center">
        <template #default="{ row }">
          <el-button
            type="danger"
            size="small"
            @click="confirmDelete(row)"
            icon="el-icon-delete"
          >
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 创建模板对话框 -->
    <el-dialog
      title="创建新模板"
      v-model="dialogVisible"
      width="50%"
      @close="resetForm"
    >
      <el-form :model="newPrompt" :rules="rules" ref="promptForm" label-width="80px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="newPrompt.name" placeholder="请输入模板名称"></el-input>
        </el-form-item>
        <el-form-item label="内容" prop="content">
          <el-input
            v-model="newPrompt.content"
            type="textarea"
            :rows="5"
            placeholder="请输入模板内容"
          ></el-input>
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="createPrompt" :loading="submitting">
            创建
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script>
export default {
  data() {
    return {
      prompts: [],
      loading: false,
      submitting: false,
      error: '',
      dialogVisible: false,
      newPrompt: {
        name: '',
        content: ''
      },
      rules: {
        name: [
          { required: true, message: '请输入模板名称', trigger: 'blur' },
          { min: 2, max: 50, message: '长度在 2 到 50 个字符', trigger: 'blur' }
        ],
        content: [
          { required: true, message: '请输入模板内容', trigger: 'blur' }
        ]
      }
    };
  },
  created() {
    this.fetchPrompts();
  },
  methods: {
    // 处理返回操作
    handleBack() {
        this.$router.push('/');
    },
    
    // 获取所有提示模板
    fetchPrompts() {
      this.loading = true;
      this.error = '';
      
      fetch('/api/prompt-templates')
        .then(response => {
          if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
          }
          return response.json();
        })
        .then(data => {
          // 将对象转换为数组格式
          const promptsArray = [];
          for (const [key, value] of Object.entries(data)) {
            promptsArray.push({
              id: key,
              name: key,
              content: value
            });
          }
          this.prompts = promptsArray;
          this.loading = false;
        })
        .catch(error => {
          console.error('Error fetching prompt templates:', error);
          this.error = '获取提示模板失败: ' + error.message;
          this.loading = false;
        });
    },
    
    // 显示创建对话框
    showCreateDialog() {
      this.dialogVisible = true;
    },
    
    // 重置表单
    resetForm() {
      if (this.$refs.promptForm) {
        this.$refs.promptForm.resetFields();
      }
      this.newPrompt = {
        name: '',
        content: ''
      };
    },
    
    // 创建新提示模板
    createPrompt() {
      this.$refs.promptForm.validate(valid => {
        if (!valid) return;
        
        this.submitting = true;
        
        // 创建一个新的对象，用于保存到后端
        const templateData = {};
        templateData[this.newPrompt.name] = this.newPrompt.content;
        
        fetch('/api/prompt-templates', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(templateData),
        })
          .then(response => {
            if (!response.ok) {
              throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.json();
          })
          .then(() => {
            // 添加到本地数组
            this.prompts.push({
              id: this.newPrompt.name,
              name: this.newPrompt.name,
              content: this.newPrompt.content
            });
            this.dialogVisible = false;
            this.$message({
              type: 'success',
              message: '创建成功!'
            });
          })
          .catch(error => {
            console.error('Error creating prompt:', error);
            this.$message({
              type: 'error',
              message: '创建失败: ' + error.message
            });
          })
          .finally(() => {
            this.submitting = false;
          });
      });
    },
    
    // 更新提示模板
    updatePrompt(prompt) {
      if (!prompt.name || !prompt.content) {
        this.$message({
          type: 'warning',
          message: '名称和内容不能为空'
        });
        return;
      }
      
      // 创建一个新的对象，只包含需要更新的模板
      const templateData = {};
      templateData[prompt.name] = prompt.content;
      
      fetch('/api/prompt-templates', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(templateData),
      })
        .then(response => {
          if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
          }
          // 更新本地数据
          const index = this.prompts.findIndex(p => p.id === prompt.id);
          if (index !== -1) {
            this.prompts[index] = {
              id: prompt.name,
              name: prompt.name,
              content: prompt.content
            };
          }
          this.$message({
            type: 'success',
            message: '更新成功!'
          });
        })
        .catch(error => {
          console.error('Error updating prompt:', error);
          this.$message({
            type: 'error',
            message: '更新失败: ' + error.message
          });
        });
    },
    
    // 确认删除
    confirmDelete(prompt) {
      this.$confirm(`确定要删除模板 "${prompt.name || prompt.id}" 吗?`, '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(() => {
        this.deletePrompt(prompt.id);
      }).catch(() => {
        this.$message({
          type: 'info',
          message: '已取消删除'
        });
      });
    },
    
    // 删除提示模板
    deletePrompt(id, showMessage = true) {
      return fetch(`/api/prompt-templates/${id}`, {
        method: 'DELETE',
      })
        .then(response => {
          if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
          }
          this.prompts = this.prompts.filter(prompt => prompt.id !== id);
          if (showMessage) {
            this.$message({
              type: 'success',
              message: '删除成功!'
            });
          }
          return Promise.resolve();
        })
        .catch(error => {
          console.error('Error deleting prompt:', error);
          this.$message({
            type: 'error',
            message: '删除失败: ' + error.message
          });
          return Promise.reject(error);
        });
    }
  }
};
</script>

<style scoped>
.prompt-manager {
  padding: 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header-left {
  display: flex;
  align-items: center;
}

h1 {
  font-size: 24px;
  margin: 0;
  flex-grow: 1;
  text-align: center;
}

.loading-container {
  padding: 20px 0;
}

.el-table {
  margin-top: 20px;
}

.content-editor {
  display: flex;
  flex-direction: column;
  width: 100%;
}

.content-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 8px;
}

/* 确保表格内容区域有足够的高度 */
.el-table__body-wrapper {
  min-height: 400px;
}

/* 调整表格最大高度，确保在屏幕上有合理的显示 */
.el-table {
  max-height: calc(100vh - 200px);
  overflow-y: auto;
}
</style>
