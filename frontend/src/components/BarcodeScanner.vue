<script setup>
import { onMounted, onUnmounted } from 'vue'
import { Html5Qrcode } from 'html5-qrcode'

const emit = defineEmits(['decode', 'error'])

// 每次实例用不同id，避免多个扫码框同时存在时冲突
const elementId = 'barcode-scanner-' + Math.random().toString(36).slice(2)
let html5QrCode = null
let stopped = false

onMounted(async () => {
  html5QrCode = new Html5Qrcode(elementId)
  try {
    await html5QrCode.start(
      { facingMode: 'environment' }, // 优先用后置摄像头
      {
        fps: 10,
        qrbox: { width: 260, height: 160 },
        formatsToSupport: undefined, // 默认支持常见的一维码(EAN-13/Code128等)和二维码
      },
      (decodedText) => {
        if (stopped) return
        emit('decode', decodedText)
      },
      () => {
        // 单帧没识别到不算错误，忽略
      }
    )
  } catch (e) {
    emit('error', e?.message || '摄像头启动失败，请检查是否已授权摄像头权限，以及网页是否为 https 或 localhost')
  }
})

onUnmounted(() => {
  stopped = true
  if (html5QrCode) {
    html5QrCode.stop().catch(() => {})
  }
})
</script>

<template>
  <div :id="elementId" class="scanner-box"></div>
</template>

<style scoped>
.scanner-box {
  width: 100%;
  min-height: 240px;
}
.scanner-box :deep(video) {
  border-radius: 8px;
}
</style>
