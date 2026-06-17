<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { inventoryApi, membersApi, ordersApi, barcodesApi } from '../api'
import { currentStore } from '../store/current'
import { useIsMobile } from '../composables/useIsMobile'
import ReceiptDialog from '../components/ReceiptDialog.vue'
import BarcodeScanner from '../components/BarcodeScanner.vue'

const { isMobile } = useIsMobile()

const receiptVisible = ref(false)
const receiptData = ref(null)

const productList = ref([])
const cart = ref([])
const cartDrawerVisible = ref(false)

const memberPhone = ref('')
const memberInfo = ref(null)
const memberSearchLoading = ref(false)

const discount = ref(0)
const paymentMethod = ref('微信')
const submitting = ref(false)

async function loadInventory() {
  if (!currentStore.storeId) return
  productList.value = await inventoryApi.getStoreInventory(currentStore.storeId)
}

watch(() => currentStore.storeId, () => {
  loadInventory()
  cart.value = []
})
onMounted(loadInventory)

function addToCart(product, sizeRow) {
  if (sizeRow.quantity <= 0) {
    ElMessage.warning('该码已无库存')
    return
  }
  const existing = cart.value.find(
    (c) => c.product_id === product.product_id && c.size === sizeRow.size
  )
  if (existing) {
    if (existing.quantity >= sizeRow.quantity) {
      ElMessage.warning('已达到库存上限')
      return
    }
    existing.quantity++
  } else {
    cart.value.push({
      product_id: product.product_id,
      name: product.name,
      color: product.color,
      size: sizeRow.size,
      unit_price: product.retail_price,
      quantity: 1,
      maxStock: sizeRow.quantity,
    })
  }
  if (isMobile.value) ElMessage.success({ message: '已加入购物车', duration: 600 })
}

function removeFromCart(index) {
  cart.value.splice(index, 1)
}

const total = computed(() =>
  cart.value.reduce((sum, item) => sum + item.unit_price * item.quantity, 0) - discount.value
)
const cartCount = computed(() => cart.value.reduce((sum, item) => sum + item.quantity, 0))

async function searchMember() {
  if (!memberPhone.value) { memberInfo.value = null; return }
  memberSearchLoading.value = true
  try {
    memberInfo.value = await membersApi.search(memberPhone.value)
  } catch {
    memberInfo.value = null
    ElMessage.info('未找到该会员，将按非会员开单')
  } finally {
    memberSearchLoading.value = false
  }
}

// ── 扫码 ──────────────────────────────────────────
const scannerVisible = ref(false)
const scannerError = ref('')

// 扫到条码后的处理
async function onBarcodeDecoded(code) {
  scannerVisible.value = false
  try {
    const info = await barcodesApi.lookup(code, currentStore.storeId)
    // 找到了：直接加入购物车
    const product = productList.value.find((p) => p.product_id === info.product_id)
    if (product) {
      const sizeRow = product.sizes.find((s) => s.size === info.size)
      if (sizeRow) {
        addToCart(product, sizeRow)
      } else {
        ElMessage.warning(`库存中没有 ${info.name} ${info.size}码，请先入库`)
      }
    } else {
      ElMessage.warning(`${info.name} ${info.size}码 不在当前门店库存中`)
    }
  } catch {
    // 没绑定过：弹出绑定框
    bindingBarcode.value = code
    bindForm.value = { product_id: null, size: '' }
    bindVisible.value = true
  }
}

function onScannerError(msg) {
  scannerVisible.value = false
  ElMessage.error(msg)
}

// ── 首次绑定条码 ──────────────────────────────────
const bindVisible = ref(false)
const bindingBarcode = ref('')
const bindForm = ref({ product_id: null, size: '' })
const bindLoading = ref(false)

// 商品扁平列表（供绑定时选择）
const allProductsFlat = computed(() => {
  const result = []
  for (const p of productList.value) {
    result.push({
      id: p.product_id,
      label: `${p.model_no} ${p.name} ${p.color}`,
      retail_price: p.retail_price,
      sizes: p.sizes,
    })
  }
  return result
})

async function submitBind() {
  if (!bindForm.value.product_id || !bindForm.value.size) {
    ElMessage.warning('请选择商品并填写鞋码')
    return
  }
  bindLoading.value = true
  try {
    await barcodesApi.bind({
      barcode: bindingBarcode.value,
      product_id: bindForm.value.product_id,
      size: bindForm.value.size,
    })
    ElMessage.success('绑定成功！下次扫该码直接识别')
    bindVisible.value = false

    // 绑定完顺带加入购物车
    const product = productList.value.find((p) => p.product_id === bindForm.value.product_id)
    if (product) {
      const sizeRow = product.sizes.find((s) => s.size === bindForm.value.size)
      if (sizeRow) addToCart(product, sizeRow)
    }
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    bindLoading.value = false
  }
}

// ── 收款确认 ──────────────────────────────────────
const paymentVisible = ref(false)
const cashPaid = ref(0)
const cashChange = computed(() => Math.max(0, cashPaid.value - total.value))

// 收款码 from localStorage
const wechatQr = ref(localStorage.getItem('bb_wechat_qr') || '')
const alipayQr = ref(localStorage.getItem('bb_alipay_qr') || '')

function uploadQr(type, uploadFile) {
  const file = uploadFile.raw
  const reader = new FileReader()
  reader.onload = (e) => {
    const data = e.target.result
    if (type === 'wechat') {
      wechatQr.value = data
      localStorage.setItem('bb_wechat_qr', data)
    } else {
      alipayQr.value = data
      localStorage.setItem('bb_alipay_qr', data)
    }
    ElMessage.success('收款码已保存')
  }
  reader.readAsDataURL(file)
}

function openPayment() {
  if (cart.value.length === 0) {
    ElMessage.warning('购物车是空的')
    return
  }
  cashPaid.value = Math.ceil(total.value)
  paymentVisible.value = true
  cartDrawerVisible.value = false
}

// 真正提交订单（在确认收款后才调用）
async function submitOrder() {
  submitting.value = true
  try {
    const result = await ordersApi.create({
      store_id: currentStore.storeId,
      member_phone: memberInfo.value ? memberPhone.value : null,
      items: cart.value.map((c) => ({
        product_id: c.product_id,
        size: c.size,
        quantity: c.quantity,
        unit_price: c.unit_price,
      })),
      discount_amount: discount.value,
      payment_method: paymentMethod.value,
    })
    ElMessage.success(
      `收款成功！¥${result.total_amount}${result.earned_points ? ' · 会员+' + result.earned_points + '积分' : ''}`
    )
    paymentVisible.value = false
    cart.value = []
    discount.value = 0
    memberPhone.value = ''
    memberInfo.value = null
    loadInventory()

    try {
      receiptData.value = await ordersApi.receipt(result.order_id)
      receiptVisible.value = true
    } catch {}
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <!-- ── 电脑布局 ────────────────────────────────── -->
  <el-row v-if="!isMobile" :gutter="16">
    <el-col :span="15">
      <el-card>
        <template #header>
          <div style="display:flex;justify-content:space-between;align-items:center">
            <span>选择商品</span>
            <el-button type="primary" plain size="small" @click="scannerVisible = true">
              <el-icon><Camera /></el-icon> 扫码
            </el-button>
          </div>
        </template>
        <div class="product-grid">
          <div v-for="p in productList" :key="p.product_id" class="product-card">
            <div class="product-name">{{ p.model_no }} {{ p.name }}</div>
            <div class="product-sub">{{ p.color }} · ¥{{ p.retail_price }}</div>
            <div class="size-list">
              <el-button
                v-for="s in p.sizes"
                :key="s.size"
                size="small"
                :disabled="s.quantity <= 0"
                :type="s.quantity <= 0 ? 'default' : 'primary'"
                plain
                @click="addToCart(p, s)"
              >{{ s.size }}码（{{ s.quantity }}）</el-button>
            </div>
          </div>
        </div>
      </el-card>
    </el-col>

    <el-col :span="9">
      <el-card>
        <template #header>购物车</template>
        <el-table :data="cart" size="small">
          <el-table-column label="商品">
            <template #default="{ row }">{{ row.name }} {{ row.color }} / {{ row.size }}码</template>
          </el-table-column>
          <el-table-column prop="quantity" label="数量" width="60" />
          <el-table-column label="小计" width="80">
            <template #default="{ row }">¥{{ row.unit_price * row.quantity }}</template>
          </el-table-column>
          <el-table-column width="50">
            <template #default="{ $index }">
              <el-button size="small" text type="danger" @click="removeFromCart($index)">删</el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-divider />

        <el-form label-width="80px">
          <el-form-item label="会员手机号">
            <el-input v-model="memberPhone" placeholder="输入手机号查会员（可不填）" @blur="searchMember" clearable />
          </el-form-item>
          <el-form-item v-if="memberInfo" label="会员信息">
            <el-tag type="success">{{ memberInfo.name }} · 积分{{ memberInfo.points }}</el-tag>
          </el-form-item>
          <el-form-item label="优惠减免">
            <el-input-number v-model="discount" :min="0" />
          </el-form-item>
          <el-form-item label="支付方式">
            <el-radio-group v-model="paymentMethod">
              <el-radio value="微信">微信</el-radio>
              <el-radio value="支付宝">支付宝</el-radio>
              <el-radio value="现金">现金</el-radio>
              <el-radio value="银行卡">银行卡</el-radio>
            </el-radio-group>
          </el-form-item>
        </el-form>

        <div class="total-line">应收金额：<span class="total-amount">¥{{ total }}</span></div>

        <el-button type="primary" size="large" style="width:100%" @click="openPayment">
          去收款
        </el-button>
      </el-card>
    </el-col>
  </el-row>

  <!-- ── 手机布局 ────────────────────────────────── -->
  <template v-else>
    <!-- 扫码悬浮按钮 -->
    <div class="scan-fab" @click="scannerVisible = true">
      <el-icon size="22"><Camera /></el-icon>
      <span>扫码</span>
    </div>

    <div class="mobile-product-grid">
      <div v-for="p in productList" :key="p.product_id" class="product-card">
        <div class="product-name">{{ p.model_no }} {{ p.name }}</div>
        <div class="product-sub">{{ p.color }} · ¥{{ p.retail_price }}</div>
        <div class="size-list">
          <el-button
            v-for="s in p.sizes"
            :key="s.size"
            :disabled="s.quantity <= 0"
            :type="s.quantity <= 0 ? 'default' : 'primary'"
            plain
            @click="addToCart(p, s)"
          >{{ s.size }}码（{{ s.quantity }}）</el-button>
        </div>
      </div>
    </div>

    <div v-if="cart.length > 0" class="floating-cart-bar" @click="cartDrawerVisible = true">
      <span class="cart-count-badge">{{ cartCount }}</span>
      <span class="floating-cart-text">购物车 · ¥{{ total }}</span>
      <span class="floating-cart-action">去结算</span>
    </div>

    <el-drawer v-model="cartDrawerVisible" direction="btt" size="85%" title="确认订单">
      <el-table :data="cart" size="small">
        <el-table-column label="商品">
          <template #default="{ row }">{{ row.name }} {{ row.color }} / {{ row.size }}码</template>
        </el-table-column>
        <el-table-column prop="quantity" label="数量" width="50" />
        <el-table-column label="小计" width="70">
          <template #default="{ row }">¥{{ row.unit_price * row.quantity }}</template>
        </el-table-column>
        <el-table-column width="40">
          <template #default="{ $index }">
            <el-button size="small" text type="danger" @click="removeFromCart($index)">删</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-divider />

      <el-form label-width="80px">
        <el-form-item label="会员手机号">
          <el-input v-model="memberPhone" placeholder="输入手机号查会员（可不填）" @blur="searchMember" clearable />
        </el-form-item>
        <el-form-item v-if="memberInfo" label="会员信息">
          <el-tag type="success">{{ memberInfo.name }} · 积分{{ memberInfo.points }}</el-tag>
        </el-form-item>
        <el-form-item label="优惠减免">
          <el-input-number v-model="discount" :min="0" />
        </el-form-item>
        <el-form-item label="支付方式">
          <el-radio-group v-model="paymentMethod">
            <el-radio value="微信">微信</el-radio>
            <el-radio value="支付宝">支付宝</el-radio>
            <el-radio value="现金">现金</el-radio>
            <el-radio value="银行卡">银行卡</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>

      <div class="total-line">应收金额：<span class="total-amount">¥{{ total }}</span></div>

      <el-button type="primary" size="large" style="width:100%" @click="openPayment">
        去收款
      </el-button>
    </el-drawer>
  </template>

  <!-- ── 扫码摄像头 ──────────────────────────────── -->
  <el-dialog
    v-model="scannerVisible"
    fullscreen
    :show-close="false"
    class="scanner-fullscreen"
  >
    <div class="scanner-wrap">
      <div class="scanner-top">
        <span>对准鞋盒/吊牌条形码</span>
        <el-button text @click="scannerVisible = false" style="color:#fff;font-size:15px">取消</el-button>
      </div>
      <BarcodeScanner
        v-if="scannerVisible"
        @decode="onBarcodeDecoded"
        @error="onScannerError"
        class="scanner-inner"
      />
      <div class="scanner-hint">自动识别 · 对准后保持稳定</div>
    </div>
  </el-dialog>

  <!-- ── 首次绑定条码 ────────────────────────────── -->
  <el-dialog v-model="bindVisible" title="未识别条码，请绑定商品" :width="isMobile ? '92%' : '420px'">
    <p class="bind-code">条码：<code>{{ bindingBarcode }}</code></p>
    <p class="bind-tip">这个条码还没绑定过，请告诉系统它是哪款鞋，以后扫这个码直接识别。</p>
    <el-form label-width="80px">
      <el-form-item label="商品">
        <el-select v-model="bindForm.product_id" placeholder="选择商品" filterable style="width:100%">
          <el-option
            v-for="p in allProductsFlat"
            :key="p.id"
            :label="p.label"
            :value="p.id"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="鞋码">
        <el-input v-model="bindForm.size" placeholder="如 27" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="bindVisible = false">取消</el-button>
      <el-button type="primary" :loading="bindLoading" @click="submitBind">
        绑定并加入购物车
      </el-button>
    </template>
  </el-dialog>

  <!-- ── 收款确认弹窗 ────────────────────────────── -->
  <el-dialog v-model="paymentVisible" title="收款" :width="isMobile ? '92%' : '400px'" align-center>
    <div class="pay-amount">
      <div class="pay-label">应收金额</div>
      <div class="pay-total">¥{{ total.toFixed(2) }}</div>
    </div>

    <el-divider />

    <div class="pay-method-label">支付方式</div>
    <el-radio-group v-model="paymentMethod" class="pay-method-group">
      <el-radio-button value="微信">微信</el-radio-button>
      <el-radio-button value="支付宝">支付宝</el-radio-button>
      <el-radio-button value="现金">现金</el-radio-button>
      <el-radio-button value="银行卡">银行卡</el-radio-button>
    </el-radio-group>

    <!-- 微信收款码 -->
    <div v-if="paymentMethod === '微信'" class="qr-section">
      <img v-if="wechatQr" :src="wechatQr" class="qr-image" alt="微信收款码" />
      <div v-else class="qr-empty">
        <p>还没设置微信收款码</p>
      </div>
      <el-upload
        :auto-upload="false"
        :show-file-list="false"
        accept="image/*"
        :on-change="(f) => uploadQr('wechat', f)"
      >
        <el-button size="small" text type="primary">
          {{ wechatQr ? '更换收款码' : '上传收款码' }}
        </el-button>
      </el-upload>
    </div>

    <!-- 支付宝收款码 -->
    <div v-if="paymentMethod === '支付宝'" class="qr-section">
      <img v-if="alipayQr" :src="alipayQr" class="qr-image" alt="支付宝收款码" />
      <div v-else class="qr-empty">
        <p>还没设置支付宝收款码</p>
      </div>
      <el-upload
        :auto-upload="false"
        :show-file-list="false"
        accept="image/*"
        :on-change="(f) => uploadQr('alipay', f)"
      >
        <el-button size="small" text type="primary">
          {{ alipayQr ? '更换收款码' : '上传收款码' }}
        </el-button>
      </el-upload>
    </div>

    <!-- 现金找零 -->
    <div v-if="paymentMethod === '现金'" class="cash-section">
      <el-form label-width="70px">
        <el-form-item label="收到">
          <el-input-number
            v-model="cashPaid"
            :min="0"
            :precision="0"
            :step="10"
            controls-position="right"
            style="width:100%"
          />
        </el-form-item>
        <el-form-item label="找零">
          <span class="change-amount">¥{{ cashChange.toFixed(2) }}</span>
        </el-form-item>
      </el-form>
    </div>

    <template #footer>
      <el-button @click="paymentVisible = false">取消</el-button>
      <el-button
        type="success"
        size="large"
        :loading="submitting"
        style="width:100%;margin-left:0;margin-top:8px"
        @click="submitOrder"
      >
        确认已收款，保存订单
      </el-button>
    </template>
  </el-dialog>

  <ReceiptDialog v-model="receiptVisible" :receipt="receiptData" />
</template>

<style scoped>
/* ── 电脑 ───────────────────────────────────────── */
.product-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  max-height: 600px;
  overflow-y: auto;
}
.product-card {
  border: 1px solid #ebeef5;
  border-radius: 6px;
  padding: 10px;
}
.product-name { font-weight: 600; }
.product-sub { color: #909399; font-size: 12px; margin: 4px 0 8px; }
.size-list { display: flex; flex-wrap: wrap; gap: 6px; }
.total-line { text-align: right; margin: 12px 0; font-size: 16px; }
.total-amount { color: #f56c6c; font-size: 24px; font-weight: 700; }

/* ── 手机 ───────────────────────────────────────── */
.mobile-product-grid { display: flex; flex-direction: column; gap: 10px; }
.mobile-product-grid .product-card { background: #fff; padding: 12px; }
.mobile-product-grid .size-list .el-button { margin: 2px; min-height: 36px; }

.floating-cart-bar {
  position: fixed;
  left: 10px; right: 10px; bottom: 70px;
  height: 50px;
  background: #409eff;
  color: #fff;
  border-radius: 25px;
  display: flex;
  align-items: center;
  padding: 0 16px;
  gap: 10px;
  box-shadow: 0 4px 12px rgba(64,158,255,0.4);
  z-index: 90;
}
.cart-count-badge {
  background: #fff; color: #409eff;
  border-radius: 50%; width: 24px; height: 24px;
  display: flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 700; flex-shrink: 0;
}
.floating-cart-text { flex: 1; font-size: 15px; font-weight: 600; }
.floating-cart-action {
  font-size: 14px;
  background: rgba(255,255,255,0.2);
  padding: 6px 14px; border-radius: 16px;
}

/* ── 扫码悬浮按钮 ───────────────────────────────── */
.scan-fab {
  position: fixed;
  right: 16px;
  bottom: 130px;
  width: 52px; height: 52px;
  background: #409eff;
  color: #fff;
  border-radius: 50%;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  gap: 2px;
  font-size: 10px;
  box-shadow: 0 4px 12px rgba(64,158,255,0.5);
  z-index: 91;
  cursor: pointer;
}

/* ── 扫码弹窗 ───────────────────────────────────── */
.scanner-wrap {
  background: #000;
  height: 100vh;
  display: flex;
  flex-direction: column;
}
.scanner-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  color: #fff;
  font-size: 15px;
}
.scanner-inner { flex: 1; }
.scanner-hint {
  text-align: center;
  color: #aaa;
  font-size: 13px;
  padding: 12px 16px 28px;
}

/* ── 绑定弹窗 ───────────────────────────────────── */
.bind-code {
  background: #f5f7fa;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 13px;
  margin-bottom: 8px;
}
.bind-code code { color: #409eff; font-weight: 600; }
.bind-tip { color: #909399; font-size: 13px; margin-bottom: 16px; }

/* ── 收款弹窗 ───────────────────────────────────── */
.pay-amount { text-align: center; padding: 16px 0 8px; }
.pay-label { color: #909399; font-size: 14px; margin-bottom: 6px; }
.pay-total { font-size: 42px; font-weight: 700; color: #f56c6c; }
.pay-method-label { font-size: 13px; color: #606266; margin-bottom: 10px; }
.pay-method-group { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 16px; }

.qr-section { display: flex; flex-direction: column; align-items: center; gap: 10px; padding: 8px 0; }
.qr-image { width: 200px; height: 200px; object-fit: contain; border: 1px solid #ebeef5; border-radius: 8px; }
.qr-empty { text-align: center; color: #909399; font-size: 14px; padding: 24px 0; }

.cash-section { padding: 8px 0; }
.change-amount { font-size: 22px; font-weight: 700; color: #67c23a; }
</style>

<style>
/* 扫码弹窗全屏，去掉默认padding */
.scanner-fullscreen .el-dialog__body {
  padding: 0 !important;
  background: #000 !important;
}
.scanner-fullscreen .el-dialog__header { display: none; }
</style>
