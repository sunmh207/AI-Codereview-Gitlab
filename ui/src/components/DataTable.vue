<template>
  <table class="table table-striped">
    <thead>
      <tr>
        <th v-for="column in columns" :key="column.key">{{ column.label }}</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="item in data" :key="item.id">
        <td>{{ item.project_name }}</td>
        <td>{{ item.author }}</td>
        <td>{{ item.branch }}</td>
        <td>{{ item.target_branch }}</td>
        <td>{{ formatDate(item.updated_at) }}</td>
        <td>{{ item.commit_messages }}</td>
        <td>
          <div class="progress">
            <div class="progress-bar"
                 role="progressbar"
                 :style="{ width: `${item.score || 0}%` }"
                 :aria-valuenow="item.score || 0"
                 aria-valuemin="0"
                 aria-valuemax="100">
              {{ item.score || 0 }}
            </div>
          </div>
        </td>
        <td>
          <button class="btn btn-sm btn-info" @click="$emit('view-details', item)">
            查看
          </button>
        </td>
      </tr>
    </tbody>
  </table>
</template>

<script>
export default {
  name: 'DataTable',
  props: {
    data: {
      type: Array,
      required: true
    },
    columns: {
      type: Array,
      required: true
    }
  },
  methods: {
    formatDate(timestamp) {
      return new Date(timestamp * 1000).toLocaleString()
    }
  }
}
</script>

<style scoped>
.table {
  margin-top: 1.5rem;
  border-collapse: separate;
  border-spacing: 0;
}

.table thead th {
  border-bottom: none;
  background: #f1f1f1;
  padding: 1rem;
}

.table tbody tr {
  transition: transform 0.2s ease;
}

.table tbody tr:hover {
  transform: translateX(5px);
}

.progress {
  margin: 0.5rem 0;
}
</style> 