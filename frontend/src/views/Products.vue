<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { productsApi } from '../api'
import { useIsMobile } from '../composables/useIsMobile'

const { isMobile } = useIsMobile()

const products = ref([])
const keyword = ref('')
const loading = ref(false)

const filtered = computed(() => {
  if (!keyword.value) return products.value
  return products.value.filter((p) => `${p.model_no}${p.name}${p.color}`.includes(keyword.value))
})

async function loadProducts() {
  loading.value = true
  try {
    products.value = await productsApi.list()
  } finally {
    loading.value = false
  }
}
onMounted(loadProducts)

// ── 新建/编辑 ──────────────────────────────────────
const dialogVisible = ref(false)
const dialogTitle = ref('新建商品')
const editingId = ref(null)
const form = ref({ model_no: '', name: '', color: '', cost_price: null, retail_price: null, image_url: '' })
const submitLoading = ref(false)

function openCreate() {
  dialogTitle.value = '新建商品'
  editingId.value = null
  form.value = { model_no: '', name: '', color: '', cost_price: null, retail_price: null, image_url: '' }
  dialogVisible.value = true
}

function openEdit(row) {
  dialogTitle.value = '编辑商品'
  editingId.value = row.id
  form.value = {
    model_no: row.model_no,
    name: row.name,
    color: row.color,
    cost_price: row.cost_price,
    retail_price: row.retail_price,
    image_url: row.image_url,
  }
  dialogVisible.value = true
}

async function submitForm() {
  if (!form.value.model_no || !form.value.name) {
    ElMessage.warning('款号和名称必填')
    return
  }
  submitLoading.value = true
  try {
    if (editingId.value) {
      await productsApi.update(editingId.value, form.value)
      ElMessage.success('修改成功')
    } else {
      await productsApi.create(form.value)
      ElMessage.success('新建成功，记得去"库存管理"给它入库')
    }
    dialogVisible.value = false
    loadProducts()
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    submitLoading.value = false
  }
}

async function deleteProduct(row) {
  try {
    await ElMessageBox.confirm(`确定删除"${row.model_no} ${row.name}"吗？`, '提示', { type: 'warning' })
  } catch {
    return
  }
  try {
    await productsApi.remove(row.id)
    ElMessage.success('删除成功')
    loadProducts()
  } catch (e) {
    ElMessage.error(e.message)
  }
}
</script>

<template>
  <el-card v-loading="loading" :body-style="isMobile ? { padding: '12px' } : {}">
    <template #header>
      <div class="toolbar" :class="{ 'toolbar-mobile': isMobile }">
        <el-input v-model="keyword" placeholder="搜索款号/名称/颜色" :style="{ width: isMobile ? '100%' : '240px' }" clearable />
        <el-button type="primary" @click="openCreate">新建商品</el-button>
      </div>
    </template>

    <!-- 电脑：表格 -->
    <el-table v-if="!isMobile" :data="filtered" size="small" height="600">
      <el-table-column prop="model_no" label="款号" width="100" />
      <el-table-column prop="name" label="名称" />
      <el-table-column prop="color" label="颜色" width="90" />
      <el-table-column prop="cost_price" label="进价" width="80">
        <template #default="{ row }">¥{{ row.cost_price ?? '-' }}</template>
      </el-table-column>
      <el-table-column prop="retail_price" label="售价" width="80">
        <template #default="{ row }">¥{{ row.retail_price ?? '-' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="140">
        <template #default="{ row }">
          <el-button size="small" text type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button size="small" text type="danger" @click="deleteProduct(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 手机：卡片列表 -->
    <div v-else class="mobile-list">
      <div v-for="p in filtered" :key="p.id" class="product-row">
        <div class="product-main">
          <div class="product-row-name">{{ p.model_no }} {{ p.name }}</div>
          <div class="product-row-sub">{{ p.color }} · 进价¥{{ p.cost_price ?? '-' }} · 售价¥{{ p.retail_price ?? '-' }}</div>
        </div>
        <div class="product-actions">
          <el-button size="small" text type="primary" @click="openEdit(p)">编辑</el-button>
          <el-button size="small" text type="danger" @click="deleteProduct(p)">删除</el-button>
        </div>
      </div>
      <el-empty v-if="filtered.length === 0" description="没有商品数据" />
    </div>
  </el-card>

  <el-dialog v-model="dialogVisible" :title="dialogTitle" :width="isMobile ? '92%' : '420px'">
    <el-form label-width="80px">
      <el-form-item label="款号" required>
        <el-input v-model="form.model_no" placeholder="如 BD2406" />
      </el-form-item>
      <el-form-item label="名称" required>
        <el-input v-model="form.name" placeholder="如 巴布豆秋季运动鞋" />
      </el-form-item>
      <el-form-item label="颜色">
        <el-input v-model="form.color" placeholder="如 白色" />
      </el-form-item>
      <el-form-item label="进价">
        <el-input-number v-model="form.cost_price" :min="0" :precision="2" />
      </el-form-item>
      <el-form-item label="售价">
        <el-input-number v-model="form.retail_price" :min="0" :precision="2" />
      </el-form-item>
      <el-form-item label="图片链接">
        <el-input v-model="form.image_url" placeholder="可不填" />
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
.toolbar-mobile {
  flex-direction: column;
  align-items: stretch;
  gap: 10px;
}
.mobile-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.product-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
}
.product-row-name {
  font-weight: 600;
  font-size: 14px;
}
.product-row-sub {
  color: #909399;
  font-size: 12px;
  margin-top: 4px;
}
.product-actions {
  flex-shrink: 0;
}
</style>
