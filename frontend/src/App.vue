<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storesApi } from './api'
import { currentStore, setCurrentStore, restoreCurrentStore } from './store/current'
import { authState, restoreAuth, clearAuth, isAuthenticated, isOwner } from './store/auth'
import { useIsMobile } from './composables/useIsMobile'

const route = useRoute()
const router = useRouter()
const stores = ref([])
const { isMobile } = useIsMobile()

const activeMenu = computed(() => route.path)
const isStaff = computed(() => authState.user?.role === 'staff')
const moreVisible = ref(false)

async function loadStores() {
  if (!isAuthenticated()) return
  try {
    stores.value = await storesApi.list()
    if (isStaff.value) {
      // 店员锁定在自己门店，不允许切换
      const own = stores.value.find((s) => s.id === authState.user.store_id)
      if (own) setCurrentStore(own.id, own.name)
    } else if (!currentStore.storeId && stores.value.length) {
      setCurrentStore(stores.value[0].id, stores.value[0].name)
    }
  } catch (e) {
    console.error('加载门店列表失败', e)
  }
}

onMounted(() => {
  restoreAuth()
  restoreCurrentStore()
  loadStores()
})

// 登录成功后 token 从空变为有值，这时再拉一次门店列表
watch(() => authState.token, (val) => {
  if (val) loadStores()
})

function onStoreChange(id) {
  const store = stores.value.find((s) => s.id === id)
  if (store) setCurrentStore(store.id, store.name)
}

function go(path) {
  router.push(path)
  moreVisible.value = false
}

function handleLogout() {
  clearAuth()
  router.push('/login')
}
</script>

<template>
  <router-view v-if="route.meta.public" />

  <!-- 手机布局：顶部简化栏 + 底部Tab，"更多"收纳次要功能 -->
  <div v-else-if="isMobile" class="mobile-layout">
    <div class="mobile-header">
      <span class="page-title">{{ route.meta.title }}</span>
      <el-select
        v-if="!isStaff"
        :model-value="currentStore.storeId"
        @change="onStoreChange"
        placeholder="选择门店"
        size="small"
        style="width: 130px"
      >
        <el-option v-for="s in stores" :key="s.id" :label="s.name" :value="s.id" />
      </el-select>
      <el-tag v-else size="small">{{ currentStore.storeName }}</el-tag>
    </div>

    <div class="mobile-main">
      <router-view />
    </div>

    <div class="bottom-nav">
      <div class="nav-item" :class="{ active: activeMenu === '/dashboard' }" @click="go('/dashboard')">
        <el-icon><HomeFilled /></el-icon>
        <span>概览</span>
      </div>
      <div class="nav-item" :class="{ active: activeMenu === '/pos' }" @click="go('/pos')">
        <el-icon><ShoppingCart /></el-icon>
        <span>收银</span>
      </div>
      <div class="nav-item" :class="{ active: activeMenu === '/inventory' }" @click="go('/inventory')">
        <el-icon><Box /></el-icon>
        <span>库存</span>
      </div>
      <div class="nav-item" :class="{ active: activeMenu === '/members' }" @click="go('/members')">
        <el-icon><User /></el-icon>
        <span>会员</span>
      </div>
      <div class="nav-item" @click="moreVisible = true">
        <el-icon><MoreFilled /></el-icon>
        <span>更多</span>
      </div>
    </div>

    <el-drawer v-model="moreVisible" direction="btt" size="auto" :with-header="false">
      <div class="more-sheet">
        <div class="more-item" @click="go('/reports')">
          <el-icon><TrendCharts /></el-icon><span>销售报表</span>
        </div>
        <div class="more-item" @click="go('/purchase')">
          <el-icon><Van /></el-icon><span>进货管理</span>
        </div>
        <template v-if="isOwner()">
          <div class="more-item" @click="go('/products')">
            <el-icon><Goods /></el-icon><span>商品管理</span>
          </div>
          <div class="more-item" @click="go('/stores')">
            <el-icon><Shop /></el-icon><span>门店管理</span>
          </div>
        </template>
        <el-divider />
        <div class="more-item">
          <span class="user-name">当前账号：{{ authState.user?.display_name }}</span>
        </div>
        <div class="more-item danger" @click="handleLogout">
          <span>退出登录</span>
        </div>
      </div>
    </el-drawer>
  </div>

  <!-- 电脑布局：侧边栏 -->
  <el-container v-else class="layout">
    <el-aside width="200px" class="sidebar">
      <div class="logo">👟 巴布豆管理系统</div>
      <el-menu :default-active="activeMenu" router background-color="#1f2d3d" text-color="#bfcbd9" active-text-color="#fff">
        <el-menu-item index="/dashboard" @click="go('/dashboard')">
          <el-icon><HomeFilled /></el-icon>
          <span>今日概览</span>
        </el-menu-item>
        <el-menu-item index="/pos" @click="go('/pos')">
          <el-icon><ShoppingCart /></el-icon>
          <span>收银台</span>
        </el-menu-item>
        <el-menu-item index="/inventory" @click="go('/inventory')">
          <el-icon><Box /></el-icon>
          <span>库存管理</span>
        </el-menu-item>
        <el-menu-item v-if="isOwner()" index="/products" @click="go('/products')">
          <el-icon><Goods /></el-icon>
          <span>商品管理</span>
        </el-menu-item>
        <el-menu-item v-if="isOwner()" index="/stores" @click="go('/stores')">
          <el-icon><Shop /></el-icon>
          <span>门店管理</span>
        </el-menu-item>
        <el-menu-item index="/members" @click="go('/members')">
          <el-icon><User /></el-icon>
          <span>会员管理</span>
        </el-menu-item>
        <el-menu-item index="/purchase" @click="go('/purchase')">
          <el-icon><Van /></el-icon>
          <span>进货管理</span>
        </el-menu-item>
        <el-menu-item index="/reports" @click="go('/reports')">
          <el-icon><TrendCharts /></el-icon>
          <span>销售报表</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <span class="page-title">{{ route.meta.title }}</span>
        <div class="header-right">
          <el-select
            v-if="!isStaff"
            :model-value="currentStore.storeId"
            @change="onStoreChange"
            placeholder="选择门店"
            style="width: 200px"
          >
            <el-option v-for="s in stores" :key="s.id" :label="s.name" :value="s.id" />
          </el-select>
          <el-tag v-else size="large">{{ currentStore.storeName }}</el-tag>
          <span class="user-name">{{ authState.user?.display_name }}</span>
          <el-button text @click="handleLogout">退出</el-button>
        </div>
      </el-header>
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.layout {
  height: 100vh;
}
.sidebar {
  background-color: #1f2d3d;
}
.logo {
  color: #fff;
  font-size: 16px;
  font-weight: bold;
  padding: 16px;
  border-bottom: 1px solid #2d3d4f;
}
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}
.user-name {
  color: #606266;
  font-size: 14px;
}
.page-title {
  font-size: 18px;
  font-weight: 600;
}
.main {
  background: #f5f7fa;
}

/* ── 手机布局 ───────────────────────────────────── */
.mobile-layout {
  height: 100vh;
  display: flex;
  flex-direction: column;
}
.mobile-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  flex-shrink: 0;
}
.mobile-main {
  flex: 1;
  overflow-y: auto;
  background: #f5f7fa;
  padding: 10px;
  padding-bottom: 70px; /* 给底部Tab留空间 */
}
.bottom-nav {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: 58px;
  background: #fff;
  border-top: 1px solid #e4e7ed;
  display: flex;
  z-index: 100;
}
.nav-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  font-size: 11px;
  color: #909399;
}
.nav-item .el-icon {
  font-size: 20px;
}
.nav-item.active {
  color: #409eff;
}
.more-sheet {
  padding: 8px 0 24px;
}
.more-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 20px;
  font-size: 15px;
}
.more-item.danger {
  color: #f56c6c;
}
</style>
