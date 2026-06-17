<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { purchasesApi, suppliersApi, productsApi } from '../api'
import { currentStore } from '../store/current'
import { isOwner } from '../store/auth'
import { useIsMobile } from '../composables/useIsMobile'

const { isMobile } = useIsMobile()

const activeTab = ref('purchases')

// ── 基础数据 ──────────────────────────────────────
const suppliers = ref([])
const allProducts = ref([])

onMounted(async () => {
  await Promise.all([
    loadPurchases(),
    suppliersApi.list().then((r) => (suppliers.value = r)),
    productsApi.list().then((r) => (allProducts.value = r)),
  ])
})

// ── 进货单列表 ──────────────────────────────────────
const purchases = ref([])
const purchasesLoading = ref(false)
const filterDate = ref('')
const filterSupplierId = ref(null)
const filterStoreId = ref(null)

async function loadPurchases() {
  purchasesLoading.value = true
  try {
    const params = {}
    if (filterDate.value) params.date_str = filterDate.value
    if (filterSupplierId.value) params.supplier_id = filterSupplierId.value
    if (isOwner() && filterStoreId.value) params.store_id = filterStoreId.value
    purchases.value = await purchasesApi.list(params)
  } finally {
    purchasesLoading.value = false
  }
}

async function loadSuppliers() {
  suppliers.value = await suppliersApi.list()
}

// ── 进货单详情 ──────────────────────────────────────
const detailVisible = ref(false)
const detailData = ref(null)

function viewDetail(row) {
  detailData.value = row
  detailVisible.value = true
}

async function confirmPurchase(row) {
  try {
    await ElMessageBox.confirm(
      `确认入库进货单 ${row.order_no}？共 ${row.total_qty} 件，库存将自动增加。`,
      '确认入库',
      { confirmButtonText: '确认入库', cancelButtonText: '取消', type: 'warning' },
    )
  } catch {
    return
  }
  try {
    await purchasesApi.confirm(row.id)
    ElMessage.success('入库成功，库存已更新')
    detailVisible.value = false
    loadPurchases()
  } catch (e) {
    ElMessage.error(e.message)
  }
}

async function deletePurchase(row) {
  try {
    await ElMessageBox.confirm(`删除草稿进货单 ${row.order_no}？`, '确认删除', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }
  try {
    await purchasesApi.remove(row.id)
    ElMessage.success('已删除')
    detailVisible.value = false
    loadPurchases()
  } catch (e) {
    ElMessage.error(e.message)
  }
}

// ── 新建进货单 ──────────────────────────────────────
const createVisible = ref(false)
const createLoading = ref(false)
const createForm = ref({ supplier_id: null, note: '', items: [] })

function openCreate() {
  createForm.value = { supplier_id: null, note: '', items: [newItem()] }
  createVisible.value = true
}

function newItem() {
  return { product_id: null, size: '', quantity: 1, cost_price: 0 }
}

function addItem() {
  createForm.value.items.push(newItem())
}

function removeItem(idx) {
  createForm.value.items.splice(idx, 1)
}

function onProductChange(idx) {
  const item = createForm.value.items[idx]
  const product = allProducts.value.find((p) => p.id === item.product_id)
  if (product && product.cost_price) {
    item.cost_price = product.cost_price
  }
}

const createSummary = computed(() => ({
  qty: createForm.value.items.reduce((s, i) => s + (i.quantity || 0), 0),
  amount: createForm.value.items.reduce((s, i) => s + (i.quantity || 0) * (i.cost_price || 0), 0),
}))

async function submitCreate() {
  const validItems = createForm.value.items.filter((i) => i.product_id && i.size && i.quantity > 0)
  if (validItems.length === 0) {
    ElMessage.warning('请至少填写一条有效明细（需选商品、填鞋码）')
    return
  }
  createLoading.value = true
  try {
    await purchasesApi.create({
      store_id: currentStore.storeId,
      supplier_id: createForm.value.supplier_id || null,
      note: createForm.value.note,
      items: validItems,
    })
    ElMessage.success('进货单已保存（草稿），回到列表点「确认入库」后库存会自动增加')
    createVisible.value = false
    loadPurchases()
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    createLoading.value = false
  }
}

// ── 供应商管理 ──────────────────────────────────────
const supplierFormVisible = ref(false)
const supplierFormLoading = ref(false)
const supplierForm = ref({ name: '', contact_name: '', phone: '', address: '', remark: '' })
const editingSupplierId = ref(null)

function openNewSupplier() {
  supplierForm.value = { name: '', contact_name: '', phone: '', address: '', remark: '' }
  editingSupplierId.value = null
  supplierFormVisible.value = true
}

function openEditSupplier(s) {
  supplierForm.value = {
    name: s.name,
    contact_name: s.contact_name || '',
    phone: s.phone || '',
    address: s.address || '',
    remark: s.remark || '',
  }
  editingSupplierId.value = s.id
  supplierFormVisible.value = true
}

async function submitSupplier() {
  if (!supplierForm.value.name) {
    ElMessage.warning('供应商名称必填')
    return
  }
  supplierFormLoading.value = true
  try {
    if (editingSupplierId.value) {
      await suppliersApi.update(editingSupplierId.value, supplierForm.value)
    } else {
      await suppliersApi.create(supplierForm.value)
    }
    ElMessage.success('保存成功')
    supplierFormVisible.value = false
    loadSuppliers()
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    supplierFormLoading.value = false
  }
}

async function deleteSupplier(s) {
  try {
    await ElMessageBox.confirm(`删除供应商「${s.name}」？`, '确认', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }
  try {
    await suppliersApi.remove(s.id)
    ElMessage.success('已删除')
    loadSuppliers()
  } catch (e) {
    ElMessage.error(e.message)
  }
}
</script>

<template>
  <el-tabs v-model="activeTab">
    <!-- ── 进货单 Tab ─────────────────────────────── -->
    <el-tab-pane label="进货单" name="purchases">
      <div class="toolbar" :class="{ 'toolbar-mobile': isMobile }">
        <div class="filters">
          <el-date-picker
            v-model="filterDate"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="按日期"
            clearable
            style="width: 140px"
            @change="loadPurchases"
          />
          <el-select
            v-model="filterSupplierId"
            placeholder="按供应商"
            clearable
            style="width: 140px"
            @change="loadPurchases"
          >
            <el-option v-for="s in suppliers" :key="s.id" :label="s.name" :value="s.id" />
          </el-select>
        </div>
        <el-button type="primary" @click="openCreate">新建进货单</el-button>
      </div>

      <!-- 电脑：表格 -->
      <el-table v-if="!isMobile" v-loading="purchasesLoading" :data="purchases" size="small" style="margin-top: 12px">
        <el-table-column prop="order_no" label="单号" width="150" />
        <el-table-column prop="store_name" label="收货门店" width="130" />
        <el-table-column prop="supplier_name" label="供应商" width="120" />
        <el-table-column prop="total_qty" label="件数" width="70" align="center" />
        <el-table-column label="进货金额" width="100">
          <template #default="{ row }">¥{{ row.total_amount }}</template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === 'confirmed' ? 'success' : 'warning'" size="small">
              {{ row.status === 'confirmed' ? '已入库' : '草稿' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="140" />
        <el-table-column label="操作" min-width="160">
          <template #default="{ row }">
            <el-button size="small" text @click="viewDetail(row)">详情</el-button>
            <el-button
              v-if="row.status === 'draft'"
              size="small"
              text
              type="primary"
              @click="confirmPurchase(row)"
            >确认入库</el-button>
            <el-button
              v-if="row.status === 'draft'"
              size="small"
              text
              type="danger"
              @click="deletePurchase(row)"
            >删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 手机：卡片列表 -->
      <div v-else v-loading="purchasesLoading" class="mobile-list">
        <div
          v-for="row in purchases"
          :key="row.id"
          class="purchase-row"
          @click="viewDetail(row)"
        >
          <div class="purchase-main">
            <div class="purchase-top">
              <span class="purchase-no">{{ row.order_no }}</span>
              <el-tag :type="row.status === 'confirmed' ? 'success' : 'warning'" size="small">
                {{ row.status === 'confirmed' ? '已入库' : '草稿' }}
              </el-tag>
            </div>
            <div class="purchase-sub">{{ row.supplier_name }} · {{ row.store_name }}</div>
            <div class="purchase-sub">{{ row.created_at }}</div>
          </div>
          <div class="purchase-right">
            <div class="purchase-amount">¥{{ row.total_amount }}</div>
            <div class="purchase-qty">{{ row.total_qty }}件</div>
          </div>
        </div>
        <el-empty v-if="purchases.length === 0 && !purchasesLoading" description="暂无进货记录" />
      </div>
    </el-tab-pane>

    <!-- ── 供应商 Tab ─────────────────────────────── -->
    <el-tab-pane label="供应商" name="suppliers">
      <div style="margin-bottom: 12px">
        <el-button type="primary" @click="openNewSupplier">新建供应商</el-button>
      </div>
      <el-table :data="suppliers" size="small">
        <el-table-column prop="name" label="供应商名称" />
        <el-table-column prop="contact_name" label="联系人" width="100" />
        <el-table-column prop="phone" label="电话" width="130" />
        <el-table-column prop="address" label="地址" />
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button size="small" text @click="openEditSupplier(row)">编辑</el-button>
            <el-button size="small" text type="danger" @click="deleteSupplier(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="suppliers.length === 0" description="暂无供应商，先新建一个" />
    </el-tab-pane>
  </el-tabs>

  <!-- ── 进货单详情 Dialog ──────────────────────────── -->
  <el-dialog v-model="detailVisible" title="进货单详情" :width="isMobile ? '95%' : '680px'">
    <template v-if="detailData">
      <el-descriptions :column="isMobile ? 1 : 2" size="small" border>
        <el-descriptions-item label="单号">{{ detailData.order_no }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="detailData.status === 'confirmed' ? 'success' : 'warning'">
            {{ detailData.status === 'confirmed' ? '已入库' : '草稿' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="收货门店">{{ detailData.store_name }}</el-descriptions-item>
        <el-descriptions-item label="供应商">{{ detailData.supplier_name }}</el-descriptions-item>
        <el-descriptions-item label="操作人">{{ detailData.operator_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="入库时间">{{ detailData.confirmed_at || '未入库' }}</el-descriptions-item>
        <el-descriptions-item label="备注" :span="isMobile ? 1 : 2">{{ detailData.note || '-' }}</el-descriptions-item>
      </el-descriptions>

      <el-divider />

      <div class="detail-title">
        进货明细 &nbsp;
        <span class="detail-summary">共 {{ detailData.total_qty }} 件 · 合计 ¥{{ detailData.total_amount }}</span>
      </div>
      <el-table :data="detailData.items" size="small" style="margin-top: 8px">
        <el-table-column prop="product_name" label="商品" />
        <el-table-column prop="size" label="鞋码" width="65" />
        <el-table-column prop="quantity" label="数量" width="65" align="center" />
        <el-table-column label="进价" width="80">
          <template #default="{ row }">¥{{ row.cost_price }}</template>
        </el-table-column>
        <el-table-column label="小计" width="80">
          <template #default="{ row }">¥{{ row.subtotal }}</template>
        </el-table-column>
      </el-table>
    </template>
    <template #footer>
      <el-button @click="detailVisible = false">关闭</el-button>
      <template v-if="detailData?.status === 'draft'">
        <el-button type="danger" plain @click="deletePurchase(detailData)">删除草稿</el-button>
        <el-button type="primary" @click="confirmPurchase(detailData)">确认入库</el-button>
      </template>
    </template>
  </el-dialog>

  <!-- ── 新建进货单 Dialog ──────────────────────────── -->
  <el-dialog v-model="createVisible" title="新建进货单" :width="isMobile ? '95%' : '740px'" destroy-on-close>
    <el-form label-width="80px" style="margin-bottom: 0">
      <el-form-item label="供应商">
        <el-select
          v-model="createForm.supplier_id"
          placeholder="选择供应商（可不填，散货直接入）"
          clearable
          style="width: 100%"
        >
          <el-option v-for="s in suppliers" :key="s.id" :label="s.name" :value="s.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="备注">
        <el-input v-model="createForm.note" placeholder="批次/发货单号/备注（可不填）" />
      </el-form-item>
    </el-form>

    <el-divider content-position="left">进货明细</el-divider>

    <div class="items-header">
      <span class="col-product">商品</span>
      <span class="col-size">鞋码</span>
      <span class="col-qty">数量</span>
      <span class="col-price">进货价</span>
      <span class="col-sub">小计</span>
      <span class="col-del"></span>
    </div>

    <div v-for="(item, idx) in createForm.items" :key="idx" class="item-row">
      <el-select
        v-model="item.product_id"
        placeholder="选商品"
        filterable
        class="col-product"
        @change="() => onProductChange(idx)"
      >
        <el-option
          v-for="p in allProducts"
          :key="p.id"
          :label="`${p.model_no} ${p.name} ${p.color}`"
          :value="p.id"
        />
      </el-select>
      <el-input v-model="item.size" placeholder="码" class="col-size" />
      <el-input-number
        v-model="item.quantity"
        :min="1"
        controls-position="right"
        class="col-qty"
      />
      <el-input-number
        v-model="item.cost_price"
        :min="0"
        :precision="2"
        controls-position="right"
        class="col-price"
      />
      <span class="col-sub item-subtotal">
        ¥{{ ((item.quantity || 0) * (item.cost_price || 0)).toFixed(2) }}
      </span>
      <el-button
        text
        type="danger"
        class="col-del"
        :disabled="createForm.items.length === 1"
        @click="removeItem(idx)"
      >删</el-button>
    </div>

    <el-button text type="primary" style="margin-top: 8px" @click="addItem">+ 添加一行</el-button>

    <div class="create-summary">
      合计：<strong>{{ createSummary.qty }} 件</strong> &nbsp;·&nbsp; <strong>¥{{ createSummary.amount.toFixed(2) }}</strong>
    </div>

    <template #footer>
      <el-button @click="createVisible = false">取消</el-button>
      <el-button type="primary" :loading="createLoading" @click="submitCreate">保存进货单</el-button>
    </template>
  </el-dialog>

  <!-- ── 供应商表单 Dialog ───────────────────────────── -->
  <el-dialog
    v-model="supplierFormVisible"
    :title="editingSupplierId ? '编辑供应商' : '新建供应商'"
    :width="isMobile ? '92%' : '400px'"
  >
    <el-form label-width="80px">
      <el-form-item label="名称" required>
        <el-input v-model="supplierForm.name" placeholder="如 巴布豆总部" />
      </el-form-item>
      <el-form-item label="联系人">
        <el-input v-model="supplierForm.contact_name" placeholder="业务员姓名" />
      </el-form-item>
      <el-form-item label="电话">
        <el-input v-model="supplierForm.phone" />
      </el-form-item>
      <el-form-item label="地址">
        <el-input v-model="supplierForm.address" />
      </el-form-item>
      <el-form-item label="备注">
        <el-input v-model="supplierForm.remark" type="textarea" :rows="2" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="supplierFormVisible = false">取消</el-button>
      <el-button type="primary" :loading="supplierFormLoading" @click="submitSupplier">保存</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  flex-wrap: wrap;
}
.toolbar-mobile {
  flex-direction: column;
  align-items: stretch;
}
.toolbar-mobile .el-button {
  width: 100%;
}
.filters {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

/* 手机卡片 */
.mobile-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 12px;
}
.purchase-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  cursor: pointer;
}
.purchase-top {
  display: flex;
  align-items: center;
  gap: 8px;
}
.purchase-no {
  font-weight: 600;
  font-size: 14px;
}
.purchase-sub {
  color: #909399;
  font-size: 12px;
  margin-top: 3px;
}
.purchase-right {
  text-align: right;
  flex-shrink: 0;
}
.purchase-amount {
  font-weight: 700;
  color: #409eff;
}
.purchase-qty {
  font-size: 12px;
  color: #909399;
  margin-top: 3px;
}

/* 进货单详情 */
.detail-title {
  font-weight: 600;
  font-size: 14px;
}
.detail-summary {
  font-weight: 400;
  color: #606266;
  font-size: 13px;
}

/* 新建进货单明细行 */
.items-header {
  display: flex;
  gap: 6px;
  align-items: center;
  font-size: 12px;
  color: #909399;
  padding: 0 4px 4px;
}
.item-row {
  display: flex;
  gap: 6px;
  align-items: center;
  margin-bottom: 8px;
}
.col-product { flex: 2; min-width: 0; }
.col-size    { width: 68px; flex-shrink: 0; }
.col-qty     { width: 80px; flex-shrink: 0; }
.col-price   { width: 90px; flex-shrink: 0; }
.col-sub     { width: 72px; flex-shrink: 0; text-align: right; }
.col-del     { width: 28px; flex-shrink: 0; }
.item-subtotal {
  font-size: 13px;
  color: #606266;
}
.create-summary {
  text-align: right;
  margin-top: 12px;
  font-size: 14px;
  color: #303133;
  padding-right: 36px;
}
</style>
