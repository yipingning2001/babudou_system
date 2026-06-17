<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { authApi } from '../api'
import { setAuth } from '../store/auth'

const router = useRouter()
const username = ref('')
const password = ref('')
const loading = ref(false)

async function handleLogin() {
  if (!username.value || !password.value) {
    ElMessage.warning('请输入账号和密码')
    return
  }
  loading.value = true
  try {
    const result = await authApi.login(username.value, password.value)
    setAuth(result.access_token, result.user)
    ElMessage.success(`欢迎，${result.user.display_name || result.user.username}`)
    router.push('/dashboard')
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <el-card class="login-card">
      <div class="title">👟 巴布豆门店管理系统</div>
      <el-form label-width="60px" @submit.prevent="handleLogin">
        <el-form-item label="账号">
          <el-input v-model="username" placeholder="如 boss1 / staff01" @keyup.enter="handleLogin" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="password" type="password" show-password @keyup.enter="handleLogin" />
        </el-form-item>
      </el-form>
      <el-button type="primary" style="width: 100%" :loading="loading" @click="handleLogin">登录</el-button>
    </el-card>
  </div>
</template>

<style scoped>
.login-page {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f7fa;
}
.login-card {
  width: 360px;
}
.title {
  text-align: center;
  font-size: 20px;
  font-weight: 600;
  margin-bottom: 24px;
}
</style>
