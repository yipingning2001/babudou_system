<script setup>
import { ref, watch, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ordersApi, analyticsApi } from '../api'
import { currentStore } from '../store/current'
import { isOwner } from '../store/auth'
import { useIsMobile } from '../composables/useIsMobile'
import ReceiptDialog from '../components/ReceiptDialog.vue'

// ── 畅销/滞销 ──────────────────────────────────────
const activeTab = ref('sales')
const productPeriod = ref('month')
const productData = ref(null)
const productLoading = ref(false)

async function loadProductStats() {
  productLoading.value = true
  try {
    productData.value = await analyticsApi.topProducts({
      period: productPeriod.value,
      store_id: isOwner() ? undefined : currentStore.storeId,
    })
  } finally {
    productLoading.value = false
  }
}

const { isMobile } = useIsMobile()

const selectedDate = ref(new Date().toISOString().slice(0, 10))
const report = ref(null)
const orderList = ref([])
const loading = ref(false)

const allStoresReport = ref(null)
const allStoresLoading = ref(false)

const receiptVisible = ref(false)
const receiptData = ref(null)

async function viewReceipt(row) {
  try {
    receiptData.value = await ordersApi.receipt(row.order_id)
    receiptVisible.value = true
  } catch (e) {
    ElMessage.error(e.message)
  }
}

async function loadReport() {
  if (!currentStore.storeId) return
  loading.value = true
  try {
    report.value = await ordersApi.report({ store_id: currentStore.storeId, date_str: selectedDate.value })
    orderList.value = await ordersApi.list({ store_id: currentStore.storeId, date_str: selectedDate.value })
  } finally {
    loading.value = false
  }
}

async function loadAllStoresReport() {
  if (!isOwner()) return
  allStoresLoading.value = true
  try {
    allStoresReport.value = await ordersApi.reportAllStores(selectedDate.value)
  } catch (e) {
    console.error('全门店汇总加载失败', e)
  } finally {
    allStoresLoading.value = false
  }
}

watch([() => currentStore.storeId, selectedDate], () => {
  loadReport()
  loadAllStoresReport()
})
onMounted(() => {
  loadReport()
  loadAllStoresReport()
  loadProductStats()
})

watch(productPeriod, loadProductStats)
watch(() => currentStore.storeId, loadProductStats)

async function voidOrder(row) {
  let reason = ''
  try {
    const result = await ElMessageBox.prompt(`确定撤销订单 #${row.order_id}（¥${row.total_amount}）吗？库存会自动恢复。`, '撤销/退货', {
      confirmButtonText: '确定撤销',
      cancelButtonText: '取消',
      inputPlaceholder: '退货原因（可不填）',
      type: 'warning',
    })
    reason = result.value
  } catch {
    return
  }
  try {
    await ordersApi.void(row.order_id, reason)
    ElMessage.success('已撤销，库存已恢复')
    loadReport()
  } catch (e) {
    ElMessage.error(e.message)
  }
}
</script>

<template>
  <el-tabs v-model="activeTab">

  <!-- ── 销售报表 Tab ─────────────────────────────── -->
  <el-tab-pane label="销售报表" name="sales">
  <div v-loading="loading">
    <el-card v-if="isOwner()" v-loading="allStoresLoading" class="all-stores-card">
      <template #header>
        <span>全门店当日汇总（{{ selectedDate }}）</span>
      </template>
      <el-table :data="allStoresReport?.stores ?? []" size="small">
        <el-table-column prop="store_name" label="门店" />
        <el-table-column prop="total_orders" label="订单数" width="100" />
        <el-table-column label="销售额" width="120">
          <template #default="{ row }">¥{{ row.total_sales }}</template>
        </el-table-column>
      </el-table>
      <div class="grand-total">
        <span>全部门店合计：</span>
        <span class="grand-total-orders">{{ allStoresReport?.grand_total_orders ?? '-' }} 单</span>
        <span class="grand-total-amount">¥{{ allStoresReport?.grand_total_sales ?? '-' }}</span>
      </div>
    </el-card>

    <el-card>
      <template #header>
        <div class="toolbar">
          <span>选择日期：</span>
          <el-date-picker v-model="selectedDate" type="date" value-format="YYYY-MM-DD" />
        </div>
      </template>

      <el-row :gutter="12">
        <el-col :xs="12" :sm="6"><el-card class="stat"><div class="label">订单总数</div><div class="value">{{ report?.total_orders ?? '-' }}</div></el-card></el-col>
        <el-col :xs="12" :sm="6"><el-card class="stat"><div class="label">销售总额</div><div class="value">¥{{ report?.total_sales ?? '-' }}</div></el-card></el-col>
        <el-col :xs="12" :sm="6"><el-card class="stat"><div class="label">优惠总额</div><div class="value">¥{{ report?.total_discount ?? '-' }}</div></el-card></el-col>
        <el-col :xs="12" :sm="6"><el-card class="stat"><div class="label">会员订单占比</div><div class="value">{{ report?.member_orders ?? 0 }} / {{ (report?.member_orders ?? 0) + (report?.non_member_orders ?? 0) }}</div></el-card></el-col>
      </el-row>

      <el-divider />

      <h4>支付方式分布</h4>
      <el-table :data="Object.entries(report?.payment_breakdown ?? {}).map(([k, v]) => ({ method: k, amount: v }))" size="small">
        <el-table-column prop="method" label="支付方式" />
        <el-table-column prop="amount" label="金额">
          <template #default="{ row }">¥{{ row.amount }}</template>
        </el-table-column>
      </el-table>

      <el-divider />

      <h4>当日订单明细（销售汇总不含已撤销订单）</h4>

      <!-- 电脑：表格 -->
      <el-table v-if="!isMobile" :data="orderList" size="small" height="300">
        <el-table-column prop="order_id" label="订单号" width="80" />
        <el-table-column prop="created_at" label="时间" width="160" />
        <el-table-column prop="total_amount" label="金额" width="90">
          <template #default="{ row }">¥{{ row.total_amount }}</template>
        </el-table-column>
        <el-table-column prop="payment_method" label="支付方式" width="90" />
        <el-table-column prop="items_count" label="商品件数" width="90" />
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag v-if="row.status === 'voided'" type="danger">已撤销</el-tag>
            <el-tag v-else type="success">正常</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button size="small" text @click="viewReceipt(row)">小票</el-button>
            <el-button v-if="row.status !== 'voided'" size="small" text type="danger" @click="voidOrder(row)">
              撤销/退货
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 手机：卡片列表 -->
      <div v-else class="mobile-list">
        <div v-for="row in orderList" :key="row.order_id" class="order-row">
          <div class="order-main">
            <div class="order-top">
              <span class="order-id">#{{ row.order_id }}</span>
              <el-tag v-if="row.status === 'voided'" type="danger" size="small">已撤销</el-tag>
              <el-tag v-else type="success" size="small">正常</el-tag>
            </div>
            <div class="order-sub">{{ row.created_at }} · {{ row.payment_method }} · {{ row.items_count }}件</div>
          </div>
          <div class="order-right">
            <div class="order-amount">¥{{ row.total_amount }}</div>
            <div class="order-actions">
              <el-button size="small" text @click="viewReceipt(row)">小票</el-button>
              <el-button v-if="row.status !== 'voided'" size="small" text type="danger" @click="voidOrder(row)">撤销</el-button>
            </div>
          </div>
        </div>
        <el-empty v-if="orderList.length === 0" description="当天没有订单" />
      </div>
    </el-card>

    <ReceiptDialog v-model="receiptVisible" :receipt="receiptData" />
  </div>
  </el-tab-pane>

  <!-- ── 畅销/滞销 Tab ───────────────────────────── -->
  <el-tab-pane label="畅销/滞销分析" name="products">
    <div class="product-toolbar">
      <el-radio-group v-model="productPeriod" size="small">
        <el-radio-button value="today">今日</el-radio-button>
        <el-radio-button value="week">本周</el-radio-button>
        <el-radio-button value="month">本月</el-radio-button>
        <el-radio-button value="all">全部</el-radio-button>
      </el-radio-group>
    </div>

    <div v-loading="productLoading">
      <el-row :gutter="16">
        <el-col :xs="24" :sm="12">
          <el-card style="margin-bottom: 16px">
            <template #header>
              <span style="color:#67c23a; font-weight:600">畅销排行 TOP10</span>
            </template>
            <el-table :data="productData?.top_sellers ?? []" size="small">
              <el-table-column type="index" label="排名" width="55" />
              <el-table-column prop="name" label="商品" />
              <el-table-column prop="qty_sold" label="售出" width="65" align="center" />
              <el-table-column label="销售额" width="90">
                <template #default="{ row }">¥{{ row.revenue }}</template>
              </el-table-column>
            </el-table>
            <el-empty v-if="!productData?.top_sellers?.length" description="暂无销售数据" :image-size="60" />
          </el-card>
        </el-col>

        <el-col :xs="24" :sm="12">
          <el-card>
            <template #header>
              <span style="color:#e6a23c; font-weight:600">滞销预警（库存多、卖得少）</span>
            </template>
            <el-table :data="productData?.slow_movers ?? []" size="small">
              <el-table-column prop="name" label="商品" />
              <el-table-column prop="qty_in_stock" label="在库" width="65" align="center">
                <template #default="{ row }">
                  <el-tag type="warning" size="small">{{ row.qty_in_stock }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="qty_sold" label="本期售出" width="80" align="center" />
            </el-table>
            <el-empty v-if="!productData?.slow_movers?.length" description="没有滞销商品" :image-size="60" />
          </el-card>
        </el-col>
      </el-row>
    </div>
  </el-tab-pane>

  </el-tabs>
</template>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
}
.stat .label {
  color: #909399;
  font-size: 13px;
}
.stat .value {
  font-size: 22px;
  font-weight: 600;
  margin-top: 6px;
}
.stat {
  margin-bottom: 12px;
}
.mobile-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.order-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
}
.order-top {
  display: flex;
  align-items: center;
  gap: 8px;
}
.order-id {
  font-weight: 600;
}
.order-sub {
  color: #909399;
  font-size: 12px;
  margin-top: 4px;
}
.order-right {
  text-align: right;
  flex-shrink: 0;
}
.order-amount {
  font-weight: 700;
  color: #f56c6c;
}
.order-actions {
  margin-top: 2px;
}
.all-stores-card {
  margin-bottom: 16px;
}
.product-toolbar {
  margin-bottom: 16px;
}
.grand-total {
  text-align: right;
  margin-top: 12px;
  font-size: 15px;
  display: flex;
  justify-content: flex-end;
  align-items: baseline;
  gap: 8px;
}
.grand-total-orders {
  color: #909399;
}
.grand-total-amount {
  font-size: 22px;
  font-weight: 700;
  color: #f56c6c;
}
</style>
