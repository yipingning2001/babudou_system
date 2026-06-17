<script setup>
import { ref, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { storesApi, inventoryApi, membersApi, analyticsApi } from '../api'
import { currentStore } from '../store/current'
import { isOwner } from '../store/auth'

const router = useRouter()

const period = ref('month')
const profit = ref(null)
const summary = ref(null)
const lowStockList = ref([])
const birthdays = ref([])
const loading = ref(false)

async function loadAll() {
  if (!currentStore.storeId) return
  loading.value = true
  try {
    const [profitData, summaryData, allLow, bdays] = await Promise.all([
      analyticsApi.profit({ period: period.value, store_id: isOwner() ? undefined : currentStore.storeId }),
      storesApi.summary(currentStore.storeId),
      inventoryApi.lowStock(3),
      membersApi.birthdayReminder(7),
    ])
    profit.value = profitData
    summary.value = summaryData
    lowStockList.value = allLow.filter((r) => r.store === currentStore.storeName)
    birthdays.value = bdays
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

watch(() => currentStore.storeId, loadAll)
watch(period, loadAll)
onMounted(loadAll)

const periodLabel = { today: '今日', week: '本周', month: '本月', all: '全部' }
</script>

<template>
  <div v-loading="loading">

    <!-- 时间段选择 -->
    <div class="period-bar">
      <el-radio-group v-model="period" size="small">
        <el-radio-button value="today">今日</el-radio-button>
        <el-radio-button value="week">本周</el-radio-button>
        <el-radio-button value="month">本月</el-radio-button>
        <el-radio-button value="all">全部</el-radio-button>
      </el-radio-group>
    </div>

    <!-- 利润核心卡片（参考第二张图） -->
    <el-row :gutter="12" style="margin-bottom: 12px">
      <el-col :xs="8" :sm="8">
        <el-card class="profit-card profit-realized">
          <div class="profit-label">实现利润</div>
          <div class="profit-value">¥{{ profit?.realized_profit ?? '-' }}</div>
          <div class="profit-sub">{{ periodLabel[period] }}已卖出赚的</div>
        </el-card>
      </el-col>
      <el-col :xs="8" :sm="8">
        <el-card class="profit-card profit-inventory">
          <div class="profit-label">在库利润</div>
          <div class="profit-value">¥{{ profit?.inventory_profit ?? '-' }}</div>
          <div class="profit-sub">库存潜在利润</div>
        </el-card>
      </el-col>
      <el-col :xs="8" :sm="8">
        <el-card class="profit-card profit-total">
          <div class="profit-label">销售额</div>
          <div class="profit-value">¥{{ profit?.total_sales ?? '-' }}</div>
          <div class="profit-sub">{{ periodLabel[period] }}{{ profit?.total_orders ?? 0 }}单</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 今日快速数据 -->
    <el-row :gutter="12" style="margin-bottom: 12px">
      <el-col :xs="12" :sm="6">
        <el-card class="stat-card">
          <div class="stat-label">今日销售额</div>
          <div class="stat-value">¥{{ summary?.today_sales ?? '-' }}</div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card class="stat-card">
          <div class="stat-label">今日订单数</div>
          <div class="stat-value">{{ summary?.today_orders ?? '-' }}</div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card class="stat-card">
          <div class="stat-label">库存告急SKU</div>
          <div class="stat-value warn">{{ summary?.low_stock_skus ?? '-' }}</div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card class="stat-card">
          <div class="stat-label">已售罄SKU</div>
          <div class="stat-value danger">{{ summary?.out_of_stock_skus ?? '-' }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 快捷入口 + 待办 -->
    <el-row :gutter="12" style="margin-bottom: 12px">
      <el-col :xs="24" :sm="14">
        <el-card>
          <template #header>常用功能</template>
          <div class="quick-actions">
            <div class="quick-btn" @click="router.push('/pos')">
              <el-icon size="28" color="#409eff"><ShoppingCart /></el-icon>
              <span>去收银</span>
            </div>
            <div class="quick-btn" @click="router.push('/purchase')">
              <el-icon size="28" color="#67c23a"><Van /></el-icon>
              <span>进货管理</span>
            </div>
            <div class="quick-btn" @click="router.push('/inventory')">
              <el-icon size="28" color="#e6a23c"><Box /></el-icon>
              <span>库存查询</span>
            </div>
            <div class="quick-btn" @click="router.push('/reports')">
              <el-icon size="28" color="#f56c6c"><TrendCharts /></el-icon>
              <span>销售报表</span>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="10">
        <el-card>
          <template #header>待办事项</template>
          <div v-if="profit?.draft_purchases > 0" class="todo-item" @click="router.push('/purchase')">
            <el-icon color="#e6a23c"><Warning /></el-icon>
            <span>{{ profit.draft_purchases }} 张进货单待确认入库</span>
            <el-icon><ArrowRight /></el-icon>
          </div>
          <div v-if="lowStockList.length > 0" class="todo-item" @click="router.push('/inventory')">
            <el-icon color="#f56c6c"><Bell /></el-icon>
            <span>{{ lowStockList.length }} 个SKU库存告急</span>
            <el-icon><ArrowRight /></el-icon>
          </div>
          <div v-if="birthdays.length > 0" class="todo-item">
            <el-icon color="#409eff"><Present /></el-icon>
            <span>{{ birthdays.length }} 位会员孩子近7天生日</span>
          </div>
          <el-empty
            v-if="!profit?.draft_purchases && !lowStockList.length && !birthdays.length"
            description="暂无待办"
            :image-size="60"
          />
        </el-card>
      </el-col>
    </el-row>

    <!-- 低库存 + 生日提醒 -->
    <el-row :gutter="16">
      <el-col :xs="24" :sm="12">
        <el-card class="list-card">
          <template #header>库存告急（≤3双）</template>
          <el-table :data="lowStockList" size="small" height="220">
            <el-table-column prop="product" label="商品" />
            <el-table-column prop="size" label="鞋码" width="70" />
            <el-table-column prop="quantity" label="剩余" width="70" />
          </el-table>
          <el-empty v-if="lowStockList.length === 0" description="库存充足" :image-size="60" />
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12">
        <el-card class="list-card">
          <template #header>近7天孩子生日提醒</template>
          <el-table :data="birthdays" size="small" height="220">
            <el-table-column prop="name" label="家长" width="90" />
            <el-table-column prop="child_name" label="孩子" width="90" />
            <el-table-column prop="phone" label="手机号" />
            <el-table-column prop="days_until" label="还剩" width="70">
              <template #default="{ row }">{{ row.days_until }}天</template>
            </el-table-column>
          </el-table>
          <el-empty v-if="birthdays.length === 0" description="近7天没有生日" :image-size="60" />
        </el-card>
      </el-col>
    </el-row>

  </div>
</template>

<style scoped>
.period-bar {
  margin-bottom: 14px;
}

/* 利润卡片 */
.profit-card {
  margin-bottom: 0;
  text-align: center;
}
.profit-label {
  font-size: 12px;
  color: #909399;
  margin-bottom: 6px;
}
.profit-value {
  font-size: 22px;
  font-weight: 700;
  margin-bottom: 4px;
}
.profit-sub {
  font-size: 11px;
  color: #c0c4cc;
}
.profit-realized .profit-value { color: #67c23a; }
.profit-inventory .profit-value { color: #e6a23c; }
.profit-total .profit-value { color: #409eff; }

/* 今日数据卡片 */
.stat-card { margin-bottom: 12px; }
.stat-label { color: #909399; font-size: 13px; margin-bottom: 8px; }
.stat-value { font-size: 26px; font-weight: 600; }
.stat-value.warn { color: #e6a23c; }
.stat-value.danger { color: #f56c6c; }

/* 快捷入口 */
.quick-actions {
  display: flex;
  justify-content: space-around;
  padding: 8px 0;
}
.quick-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #606266;
  cursor: pointer;
  padding: 8px 12px;
  border-radius: 8px;
  transition: background 0.2s;
}
.quick-btn:hover { background: #f5f7fa; }

/* 待办 */
.todo-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 4px;
  font-size: 13px;
  cursor: pointer;
  border-bottom: 1px solid #f5f7fa;
}
.todo-item:last-child { border-bottom: none; }
.todo-item span { flex: 1; }

.list-card { margin-bottom: 12px; }
</style>
