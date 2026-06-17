<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { inventoryApi, productsApi, storesApi } from '../api'
import { currentStore } from '../store/current'
import { useIsMobile } from '../composables/useIsMobile'

const { isMobile } = useIsMobile()

const inventory = ref([]) // 当前门店库存，按商品分组
const allProducts = ref([])
const allStores = ref([])
const keyword = ref('')

// 展开成扁平行，方便表格展示和搜索
const flatRows = computed(() => {
  const rows = []
  for (const p of inventory.value) {
    for (const s of p.sizes) {
      rows.push({
        product_id: p.product_id,
        model_no: p.model_no,
        name: p.name,
        color: p.color,
        retail_price: p.retail_price,
        size: s.size,
        quantity: s.quantity,
      })
    }
  }
  if (!keyword.value) return rows
  return rows.filter((r) => `${r.model_no}${r.name}${r.color}`.includes(keyword.value))
})

function stockTagType(qty) {
  return qty === 0 ? 'danger' : qty <= 3 ? 'warning' : 'success'
}

async function loadInventory() {
  if (!currentStore.storeId) return
  inventory.value = await inventoryApi.getStoreInventory(currentStore.storeId)
}

watch(() => currentStore.storeId, loadInventory)
onMounted(async () => {
  loadInventory()
  allProducts.value = await productsApi.list()
  allStores.value = await storesApi.list()
})

// ── 入库 ──────────────────────────────────────────
const restockVisible = ref(false)
const restockForm = ref({ product_id: null, size: '', quantity: 1 })
const restockLoading = ref(false)

function openRestock() {
  restockForm.value = { product_id: null, size: '', quantity: 1 }
  restockVisible.value = true
}

async function submitRestock() {
  if (!restockForm.value.product_id || !restockForm.value.size) {
    ElMessage.warning('请选择商品并填写鞋码')
    return
  }
  restockLoading.value = true
  try {
    await inventoryApi.upsert({
      store_id: currentStore.storeId,
      product_id: restockForm.value.product_id,
      size: String(restockForm.value.size),
      quantity: restockForm.value.quantity,
    })
    ElMessage.success('入库成功')
    restockVisible.value = false
    loadInventory()
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    restockLoading.value = false
  }
}

// ── 调货 ──────────────────────────────────────────
const transferVisible = ref(false)
const transferForm = ref({ to_store_id: null, product_id: null, size: '', quantity: 1 })
const transferLoading = ref(false)

const otherStores = computed(() => allStores.value.filter((s) => s.id !== currentStore.storeId))

function openTransfer() {
  transferForm.value = { to_store_id: null, product_id: null, size: '', quantity: 1 }
  transferVisible.value = true
}

async function submitTransfer() {
  const f = transferForm.value
  if (!f.to_store_id || !f.product_id || !f.size) {
    ElMessage.warning('请填写完整调货信息')
    return
  }
  transferLoading.value = true
  try {
    await inventoryApi.transfer({
      from_store_id: currentStore.storeId,
      to_store_id: f.to_store_id,
      product_id: f.product_id,
      size: String(f.size),
      quantity: f.quantity,
    })
    ElMessage.success('调货成功')
    transferVisible.value = false
    loadInventory()
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    transferLoading.value = false
  }
}
</script>

<template>
  <el-card :body-style="isMobile ? { padding: '12px' } : {}">
    <template #header>
      <div class="toolbar" :class="{ 'toolbar-mobile': isMobile }">
        <el-input v-model="keyword" placeholder="搜索款号/名称/颜色" :style="{ width: isMobile ? '100%' : '240px' }" clearable />
        <div class="toolbar-actions">
          <el-button type="primary" @click="openRestock">入库</el-button>
          <el-button @click="openTransfer">门店调货</el-button>
        </div>
      </div>
    </template>

    <!-- 电脑：表格 -->
    <el-table v-if="!isMobile" :data="flatRows" size="small" height="600">
      <el-table-column prop="model_no" label="款号" width="100" />
      <el-table-column prop="name" label="名称" />
      <el-table-column prop="color" label="颜色" width="80" />
      <el-table-column prop="size" label="鞋码" width="70" />
      <el-table-column prop="retail_price" label="售价" width="80" />
      <el-table-column label="库存" width="90">
        <template #default="{ row }">
          <el-tag :type="stockTagType(row.quantity)">{{ row.quantity }}</el-tag>
        </template>
      </el-table-column>
    </el-table>

    <!-- 手机：卡片列表 -->
    <div v-else class="mobile-list">
      <div v-for="row in flatRows" :key="`${row.product_id}-${row.size}`" class="inv-row">
        <div class="inv-main">
          <div class="inv-name">{{ row.model_no }} {{ row.name }}</div>
          <div class="inv-sub">{{ row.color }} · {{ row.size }}码 · ¥{{ row.retail_price }}</div>
        </div>
        <el-tag :type="stockTagType(row.quantity)" size="large">{{ row.quantity }}双</el-tag>
      </div>
      <el-empty v-if="flatRows.length === 0" description="没有库存数据" />
    </div>
  </el-card>

  <el-dialog v-model="restockVisible" title="入库" :width="isMobile ? '92%' : '420px'">
    <el-form label-width="80px">
      <el-form-item label="商品">
        <el-select v-model="restockForm.product_id" placeholder="选择商品" filterable style="width: 100%">
          <el-option
            v-for="p in allProducts"
            :key="p.id"
            :label="`${p.model_no} ${p.name} ${p.color}`"
            :value="p.id"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="鞋码">
        <el-input v-model="restockForm.size" placeholder="如 27" />
      </el-form-item>
      <el-form-item label="入库数量">
        <el-input-number v-model="restockForm.quantity" :min="1" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="restockVisible = false">取消</el-button>
      <el-button type="primary" :loading="restockLoading" @click="submitRestock">确认入库</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="transferVisible" title="门店调货" :width="isMobile ? '92%' : '420px'">
    <el-form label-width="90px">
      <el-form-item label="调出门店">
        <el-input :model-value="currentStore.storeName" disabled />
      </el-form-item>
      <el-form-item label="调入门店">
        <el-select v-model="transferForm.to_store_id" placeholder="选择门店" style="width: 100%">
          <el-option v-for="s in otherStores" :key="s.id" :label="s.name" :value="s.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="商品">
        <el-select v-model="transferForm.product_id" placeholder="选择商品" filterable style="width: 100%">
          <el-option
            v-for="p in allProducts"
            :key="p.id"
            :label="`${p.model_no} ${p.name} ${p.color}`"
            :value="p.id"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="鞋码">
        <el-input v-model="transferForm.size" placeholder="如 27" />
      </el-form-item>
      <el-form-item label="调货数量">
        <el-input-number v-model="transferForm.quantity" :min="1" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="transferVisible = false">取消</el-button>
      <el-button type="primary" :loading="transferLoading" @click="submitTransfer">确认调货</el-button>
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
.toolbar-actions {
  display: flex;
  gap: 8px;
}
.toolbar-mobile .toolbar-actions {
  justify-content: flex-end;
}

.mobile-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.inv-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
}
.inv-name {
  font-weight: 600;
  font-size: 14px;
}
.inv-sub {
  color: #909399;
  font-size: 12px;
  margin-top: 4px;
}
</style>
