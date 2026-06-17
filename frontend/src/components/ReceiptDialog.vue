<script setup>
defineProps({
  modelValue: Boolean,
  receipt: Object,
})
defineEmits(['update:modelValue'])

function doPrint() {
  window.print()
}
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    @update:model-value="(v) => $emit('update:modelValue', v)"
    title="小票"
    width="92%"
    style="max-width: 380px"
  >
    <div v-if="receipt" id="receipt-print-area" class="receipt">
      <div class="store-name">{{ receipt.store_name }}</div>
      <div class="line"></div>
      <div class="row"><span>订单号</span><span>#{{ receipt.order_id }}</span></div>
      <div class="row"><span>时间</span><span>{{ receipt.created_at }}</span></div>
      <div class="row"><span>店员</span><span>{{ receipt.staff_name || '-' }}</span></div>
      <div class="row" v-if="receipt.member_phone"><span>会员</span><span>{{ receipt.member_phone }}</span></div>
      <div class="line"></div>
      <div v-for="(item, idx) in receipt.items" :key="idx" class="item">
        <div>{{ item.name }} {{ item.size }}码 × {{ item.quantity }}</div>
        <div class="item-price">¥{{ item.subtotal }}</div>
      </div>
      <div class="line"></div>
      <div class="row" v-if="receipt.discount_amount"><span>优惠</span><span>-¥{{ receipt.discount_amount }}</span></div>
      <div class="row total"><span>合计</span><span>¥{{ receipt.total_amount }}</span></div>
      <div class="row"><span>支付方式</span><span>{{ receipt.payment_method }}</span></div>
      <div class="row" v-if="receipt.member_points !== null && receipt.member_points !== undefined">
        <span>会员积分</span><span>{{ receipt.member_points }}</span>
      </div>
      <div v-if="receipt.status === 'voided'" class="voided-mark">已撤销</div>
      <div class="footer">谢谢光临，欢迎再次惠顾</div>
    </div>

    <template #footer>
      <el-button @click="$emit('update:modelValue', false)">关闭</el-button>
      <el-button type="primary" @click="doPrint">打印</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.receipt {
  font-family: ui-monospace, Consolas, monospace;
  font-size: 13px;
}
.store-name {
  text-align: center;
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 8px;
}
.line {
  border-top: 1px dashed #ccc;
  margin: 8px 0;
}
.row {
  display: flex;
  justify-content: space-between;
  margin: 4px 0;
}
.row.total {
  font-weight: 700;
  font-size: 15px;
}
.item {
  display: flex;
  justify-content: space-between;
  margin: 4px 0;
}
.item-price {
  white-space: nowrap;
  margin-left: 8px;
}
.voided-mark {
  text-align: center;
  color: #f56c6c;
  font-weight: 700;
  margin-top: 8px;
}
.footer {
  text-align: center;
  color: #909399;
  margin-top: 12px;
}
</style>

<style>
/* 打印时只显示小票内容，隐藏页面其余部分 */
@media print {
  body * {
    visibility: hidden;
  }
  #receipt-print-area,
  #receipt-print-area * {
    visibility: visible;
  }
  #receipt-print-area {
    position: absolute;
    left: 0;
    top: 0;
    width: 100%;
  }
}
</style>
