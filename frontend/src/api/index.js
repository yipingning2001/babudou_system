import axios from 'axios'
import router from '../router'
import { authState, clearAuth } from '../store/auth'

// 用访问网页时的主机名拼后端地址：电脑上打开是 localhost，手机上打开是电脑的局域网IP，
// 这样就不用为了手机访问专门改代码或配置。
const api = axios.create({
  baseURL: `http://${window.location.hostname}:8000`,
  timeout: 10000,
})

// 每个请求自动带上登录token
api.interceptors.request.use((config) => {
  if (authState.token) {
    config.headers.Authorization = `Bearer ${authState.token}`
  }
  return config
})

// 统一错误提示交给调用方处理，这里只是把后端的 detail message 抽出来，方便显示
// 401（token过期/失效）统一清空登录态并跳回登录页
api.interceptors.response.use(
  (res) => res.data,
  (err) => {
    if (err.response?.status === 401) {
      clearAuth()
      router.push('/login')
    }
    const detail = err.response?.data?.detail || err.message || '请求失败'
    return Promise.reject(new Error(detail))
  }
)

export const authApi = {
  login: (username, password) => {
    const form = new URLSearchParams()
    form.append('username', username)
    form.append('password', password)
    return api.post('/auth/login', form, { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } })
  },
}

export const storesApi = {
  list: () => api.get('/stores/'),
  create: (data) => api.post('/stores/', data),
  update: (id, data) => api.put(`/stores/${id}`, data),
  remove: (id) => api.delete(`/stores/${id}`),
  summary: (storeId) => api.get(`/stores/${storeId}/summary`),
}

export const productsApi = {
  list: () => api.get('/products/'),
  create: (data) => api.post('/products/', data),
  update: (id, data) => api.put(`/products/${id}`, data),
  remove: (id) => api.delete(`/products/${id}`),
}

export const inventoryApi = {
  getStoreInventory: (storeId) => api.get(`/inventory/store/${storeId}`),
  upsert: (data) => api.post('/inventory/upsert', data),
  transfer: (data) => api.post('/inventory/transfer', data),
  lowStock: (threshold = 3) => api.get('/inventory/low-stock', { params: { threshold } }),
}

// 触发浏览器下载一个 blob（导出Excel等场景用）
function downloadBlob(blob, filename) {
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}

export const membersApi = {
  list: (storeId) => api.get('/members/', { params: storeId ? { store_id: storeId } : {} }),
  search: (phone) => api.get('/members/search', { params: { phone } }),
  create: (data) => api.post('/members/', data),
  update: (id, data) => api.put(`/members/${id}`, data),
  birthdayReminder: (daysAhead = 7) => api.get('/members/birthday-reminder', { params: { days_ahead: daysAhead } }),
  orders: (id) => api.get(`/members/${id}/orders`),
  async downloadImportTemplate() {
    const blob = await api.get('/members/import-template', { responseType: 'blob' })
    downloadBlob(blob, 'member_import_template.xlsx')
  },
  async exportExcel() {
    const blob = await api.get('/members/export-excel', { responseType: 'blob' })
    const today = new Date().toISOString().slice(0, 10)
    downloadBlob(blob, `members_export_${today}.xlsx`)
  },
  remove: (id) => api.delete(`/members/${id}`),
  importExcel: (file) => {
    const form = new FormData()
    form.append('file', file)
    return api.post('/members/import-excel', form, { headers: { 'Content-Type': 'multipart/form-data' } })
  },
}

export const analyticsApi = {
  profit: (params) => api.get('/analytics/profit', { params }),
  topProducts: (params) => api.get('/analytics/top-products', { params }),
}

export const suppliersApi = {
  list: () => api.get('/suppliers/'),
  create: (data) => api.post('/suppliers/', data),
  update: (id, data) => api.put(`/suppliers/${id}`, data),
  remove: (id) => api.delete(`/suppliers/${id}`),
}

export const purchasesApi = {
  list: (params) => api.get('/purchases/', { params }),
  get: (id) => api.get(`/purchases/${id}`),
  create: (data) => api.post('/purchases/', data),
  confirm: (id) => api.post(`/purchases/${id}/confirm`),
  remove: (id) => api.delete(`/purchases/${id}`),
}

export const barcodesApi = {
  bind: (data) => api.post('/barcodes/bind', data),
  lookup: (barcode, storeId) => api.get('/barcodes/lookup', { params: { barcode, store_id: storeId } }),
}

export const ordersApi = {
  create: (data) => api.post('/orders/', data),
  list: (params) => api.get('/orders/', { params }),
  report: (params) => api.get('/orders/report', { params }),
  reportAllStores: (dateStr) => api.get('/orders/report/all-stores', { params: dateStr ? { date_str: dateStr } : {} }),
  receipt: (orderId) => api.get(`/orders/${orderId}/receipt`),
  void: (orderId, reason) => api.post(`/orders/${orderId}/void`, { reason }),
}

export default api
