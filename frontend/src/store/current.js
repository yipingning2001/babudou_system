import { reactive } from 'vue'

// 全局共享状态：当前选中的门店。简单场景用不上 Pinia，直接用 reactive 共享就够了。
export const currentStore = reactive({
  storeId: null,
  storeName: '',
})

export function setCurrentStore(id, name) {
  currentStore.storeId = id
  currentStore.storeName = name
  localStorage.setItem('babadou_store_id', id)
  localStorage.setItem('babadou_store_name', name)
}

export function restoreCurrentStore() {
  const id = localStorage.getItem('babadou_store_id')
  const name = localStorage.getItem('babadou_store_name')
  if (id) {
    currentStore.storeId = Number(id)
    currentStore.storeName = name || ''
  }
}
