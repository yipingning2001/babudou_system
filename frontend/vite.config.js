import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0', // 监听局域网，手机/其他门店设备同一WiFi下才能打开
    port: 5173,
  },
})
