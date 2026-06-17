<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { storesApi } from '../api'
import { useIsMobile } from '../composables/useIsMobile'

const { isMobile } = useIsMobile()

const stores = ref([])
const loading = ref(false)

async function loadStores() {
  loading.value = true
  try {
    stores.value = await storesApi.list()
  } finally {
    loading.value = false
  }
}
onMounted(loadStores)

const dialogVisible = ref(false)
const dialogTitle = ref('新建门店')
const editingId = ref(null)
const form = ref({ name: '', address: '', phone: '' })
const submitLoading = ref(false)

function openCreate() {
  dialogTitle.value = '新建门店'
  editingId.value = null
  form.value = { name: '', address: '', phone: '' }
  dialogVisible.value = true
}

function openEdit(row) {
  dialogTitle.value = '编辑门店'
  editingId.value = row.id
  form.value = { name: row.name, address: row.address, phone: row.phone }
  dialogVisible.value = true
}

async function submitForm() {
  if (!form.value.name) {
    ElMessage.warning('门店名称必填')
    return
  }
  submitLoading.value = true
  try {
    if (editingId.value) {
      await storesApi.update(editingId.value, form.value)
      ElMessage.success('修改成功')
    } else {
      await storesApi.create(form.value)
      ElMessage.success('新建成功')
    }
    dialogVisible.value = false
    loadStores()
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    submitLoading.value = false
  }
}

async function deleteStore(row) {
  try {
    await ElMessageBox.confirm(`确定删除门店"${row.name}"吗？`, '提示', { type: 'warning' })
  } catch {
    return
  }
  try {
    await storesApi.remove(row.id)
    ElMessage.success('删除成功')
    loadStores()
  } catch (e) {
    ElMessage.error(e.message)
  }
}
</script>

<template>
  <el-card v-loading="loading">
    <template #header>
      <div class="toolbar">
        <span>共 {{ stores.length }} 家门店</span>
        <el-button type="primary" @click="openCreate">新建门店</el-button>
      </div>
    </template>

    <el-table v-if="!isMobile" :data="stores" size="small">
      <el-table-column prop="name" label="门店名称" />
      <el-table-column prop="address" label="地址" />
      <el-table-column prop="phone" label="电话" width="140" />
      <el-table-column label="操作" width="140">
        <template #default="{ row }">
          <el-button size="small" text type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button size="small" text type="danger" @click="deleteStore(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div v-else class="mobile-list">
      <div v-for="s in stores" :key="s.id" class="store-row">
        <div class="store-main">
          <div class="store-name">{{ s.name }}</div>
          <div class="store-sub">{{ s.address || '未填地址' }} · {{ s.phone || '未填电话' }}</div>
        </div>
        <div class="store-actions">
          <el-button size="small" text type="primary" @click="openEdit(s)">编辑</el-button>
          <el-button size="small" text type="danger" @click="deleteStore(s)">删除</el-button>
        </div>
      </div>
    </div>
  </el-card>

  <el-dialog v-model="dialogVisible" :title="dialogTitle" :width="isMobile ? '92%' : '420px'">
    <el-form label-width="80px">
      <el-form-item label="门店名称" required>
        <el-input v-model="form.name" />
      </el-form-item>
      <el-form-item label="地址">
        <el-input v-model="form.address" />
      </el-form-item>
      <el-form-item label="电话">
        <el-input v-model="form.phone" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="submitLoading" @click="submitForm">保存</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.mobile-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.store-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
}
.store-name {
  font-weight: 600;
  font-size: 14px;
}
.store-sub {
  color: #909399;
  font-size: 12px;
  margin-top: 4px;
}
.store-actions {
  flex-shrink: 0;
}
</style>
