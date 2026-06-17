import { ref, onMounted, onUnmounted } from 'vue'

const MOBILE_BREAKPOINT = 768

/**
 * 响应式判断当前是不是"手机屏幕"宽度。
 * 电脑窗口拉宽/缩小、手机横竖屏切换都会自动更新。
 */
export function useIsMobile() {
  const isMobile = ref(window.innerWidth < MOBILE_BREAKPOINT)

  function onResize() {
    isMobile.value = window.innerWidth < MOBILE_BREAKPOINT
  }

  onMounted(() => window.addEventListener('resize', onResize))
  onUnmounted(() => window.removeEventListener('resize', onResize))

  return { isMobile }
}
