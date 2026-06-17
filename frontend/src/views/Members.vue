<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { membersApi } from '../api'
import { currentStore } from '../store/current'
import { isOwner } from '../store/auth'
import { useIsMobile } from '../composables/useIsMobile'

const { isMobile } = useIsMobile()

const members = ref([])
const keyword = ref('')
const loading = ref(false)

async function loadMembers() {
  loading.value = true
  try {
    members.value = await membersApi.list()
  } finally {
    loading.value = false
  }
}
onMounted(loadMembers)

const filteredMembers = ref([])
function applyFilter() {
  if (!keyword.value) {
    filteredMembers.value = members.value
  } else {
    filteredMembers.value = members.value.filter(
      (m) => m.phone.includes(keyword.value) || (m.child_name || '').includes(keyword.value) || (m.name || '').includes(keyword.value)
    )
  }
}
import { watch } from 'vue'
watch(members, applyFilter, { immediate: true })
watch(keyword, applyFilter)

// ── 注册新会员 ──────────────────────────────────────
const registerVisible = ref(false)
const registerForm = ref({ phone: '', name: '', child_name: '', child_birthday: '', current_size: '' })
const registerLoading = ref(false)

function openRegister() {
  registerForm.value = { phone: '', name: '', child_name: '', child_birthday: '', current_size: '' }
  registerVisible.value = true
}

async function submitRegister() {
  if (!registerForm.value.phone) {
    ElMessage.warning('手机号必填')
    return
  }
  registerLoading.value = true
  try {
    await membersApi.create({
      ...registerForm.value,
      register_store_id: currentStore.storeId,
    })
    ElMessage.success('注册成功')
    registerVisible.value = false
    loadMembers()
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    registerLoading.value = false
  }
}

// ── 导出会员 ──────────────────────────────────────
const exportLoading = ref(false)

async function handleExport() {
  exportLoading.value = true
  try {
    await membersApi.exportExcel()
    ElMessage.success('已开始下载')
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    exportLoading.value = false
  }
}

// ── 导入会员 ──────────────────────────────────────
const importVisible = ref(false)
const importLoading = ref(false)
const importResult = ref(null)
const selectedFile = ref(null)

function openImport() {
  importResult.value = null
  selectedFile.value = null
  importVisible.value = true
}

async function downloadTemplate() {
  try {
    await membersApi.downloadImportTemplate()
  } catch (e) {
    ElMessage.error(e.message)
  }
}

function onFileChange(uploadFile) {
  selectedFile.value = uploadFile.raw
}

async function submitImport() {
  if (!selectedFile.value) {
    ElMessage.warning('请先选择要导入的Excel文件')
    return
  }
  importLoading.value = true
  try {
    importResult.value = await membersApi.importExcel(selectedFile.value)
    ElMessage.success(importResult.value.message)
    loadMembers()
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    importLoading.value = false
  }
}

// ── 编辑会员 ──────────────────────────────────────
const editVisible = ref(false)
const editMemberId = ref(null)
const editForm = ref({ phone: '', name: '', child_name: '', child_birthday: '', current_size: '' })
const editLoading = ref(false)

function openEdit(member) {
  editMemberId.value = member.id
  editForm.value = {
    phone: member.phone,
    name: member.name || '',
    child_name: member.child_name || '',
    child_birthday: member.child_birthday ? member.child_birthday.slice(0, 10) : '',
    current_size: member.current_size || '',
  }
  editVisible.value = true
}

async function submitEdit() {
  if (!editForm.value.phone) {
    ElMessage.warning('手机号必填')
    return
  }
  editLoading.value = true
  try {
    await membersApi.update(editMemberId.value, editForm.value)
    ElMessage.success('修改成功')
    editVisible.value = false
    loadMembers()
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    editLoading.value = false
  }
}

// ── 删除会员 ──────────────────────────────────────
async function deleteMember(member) {
  try {
    await ElMessageBox.confirm(
      `确定删除会员「${member.name || member.phone}」吗？有历史订单的会员无法删除。`,
      '删除会员',
      { confirmButtonText: '确定删除', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return
  }
  try {
    await membersApi.remove(member.id)
    ElMessage.success('已删除')
    loadMembers()
  } catch (e) {
    ElMessage.error(e.message)
  }
}

// ── 消费历史 ──────────────────────────────────────
const historyVisible = ref(false)
const historyData = ref(null)
const historyLoading = ref(false)

async function viewHistory(member) {
  historyVisible.value = true
  historyLoading.value = true
  try {
    historyData.value = await membersApi.orders(member.id)
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    historyLoading.value = false
  }
}
</script>

<template>
  <el-card v-loading="loading" :body-style="isMobile ? { padding: '12px' } : {}">
    <template #header>
      <div class="toolbar" :class="{ 'toolbar-mobile': isMobile }">
        <el-input v-model="keyword" placeholder="搜索手机号/家长/孩子姓名" :style="{ width: isMobile ? '100%' : '260px' }" clearable />
        <div class="toolbar-actions">
          <template v-if="isOwner()">
            <el-button :loading="exportLoading" @click="handleExport">导出</el-button>
            <el-button @click="openImport">导入</el-button>
          </template>
          <el-button type="primary" @click="openRegister">注册会员</el-button>
        </div>
      </div>
    </template>

    <!-- 电脑：表格 -->
    <el-table v-if="!isMobile" :data="filteredMembers" size="small" height="600">
      <el-table-column prop="phone" label="手机号" width="130" />
      <el-table-column prop="name" label="家长" width="90" />
      <el-table-column prop="child_name" label="孩子" width="90" />
      <el-table-column prop="current_size" label="当前鞋码" width="90" />
      <el-table-column prop="points" label="积分" width="80" />
      <el-table-column prop="total_spent" label="累计消费" width="100">
        <template #default="{ row }">¥{{ row.total_spent }}</template>
      </el-table-column>
      <el-table-column label="操作" width="200">
        <template #default="{ row }">
          <el-button size="small" text type="primary" @click="viewHistory(row)">消费记录</el-button>
          <el-button size="small" text @click="openEdit(row)">编辑</el-button>
          <el-button size="small" text type="danger" @click="deleteMember(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 手机：卡片列表 -->
    <div v-else class="mobile-list">
      <div v-for="m in filteredMembers" :key="m.id" class="member-row">
        <div class="member-main" @click="viewHistory(m)">
          <div class="member-name">{{ m.name || '未填姓名' }} · {{ m.child_name || '-' }}</div>
          <div class="member-sub">{{ m.phone }} · 鞋码{{ m.current_size || '-' }}</div>
          <div class="member-sub">积分{{ m.points }} · 消费¥{{ m.total_spent }}</div>
        </div>
        <div class="member-actions">
          <el-button size="small" text @click="openEdit(m)">编辑</el-button>
          <el-button size="small" text type="danger" @click="deleteMember(m)">删除</el-button>
        </div>
      </div>
      <el-empty v-if="filteredMembers.length === 0" description="没有会员数据" />
    </div>
  </el-card>

  <el-dialog v-model="registerVisible" title="注册新会员" :width="isMobile ? '92%' : '420px'">
    <el-form label-width="90px">
      <el-form-item label="手机号" required>
        <el-input v-model="registerForm.phone" />
      </el-form-item>
      <el-form-item label="家长姓名">
        <el-input v-model="registerForm.name" placeholder="如 王女士" />
      </el-form-item>
      <el-form-item label="孩子姓名">
        <el-input v-model="registerForm.child_name" />
      </el-form-item>
      <el-form-item label="孩子生日">
        <el-date-picker v-model="registerForm.child_birthday" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
      </el-form-item>
      <el-form-item label="当前鞋码">
        <el-input v-model="registerForm.current_size" placeholder="如 26" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="registerVisible = false">取消</el-button>
      <el-button type="primary" :loading="registerLoading" @click="submitRegister">确认注册</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="importVisible" title="批量导入会员" :width="isMobile ? '92%' : '480px'">
    <p class="import-tip">
      1. 先下载模板，按表头格式填好数据<br />
      2. 手机号已经存在的行会被自动跳过，不会覆盖已有数据
    </p>
    <el-button @click="downloadTemplate" style="margin-bottom: 16px">下载模板</el-button>

    <el-upload
      drag
      :auto-upload="false"
      :limit="1"
      accept=".xlsx,.xls"
      :on-change="onFileChange"
      :on-remove="() => (selectedFile = null)"
    >
      <div class="upload-text">把Excel文件拖到这里，或点击选择文件</div>
    </el-upload>

    <div v-if="importResult" class="import-result">
      <el-alert :title="importResult.message" type="success" :closable="false" />
      <div v-if="importResult.skipped_invalid_count > 0" class="invalid-rows">
        <div v-for="(item, idx) in importResult.skipped_invalid" :key="idx" class="invalid-row">
          第{{ item.row }}行：{{ item.reason }}
        </div>
      </div>
    </div>

    <template #footer>
      <el-button @click="importVisible = false">关闭</el-button>
      <el-button type="primary" :loading="importLoading" @click="submitImport">开始导入</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="editVisible" title="修改会员信息" :width="isMobile ? '92%' : '420px'">
    <el-form label-width="90px">
      <el-form-item label="手机号" required>
        <el-input v-model="editForm.phone" />
      </el-form-item>
      <el-form-item label="家长姓名">
        <el-input v-model="editForm.name" />
      </el-form-item>
      <el-form-item label="孩子姓名">
        <el-input v-model="editForm.child_name" />
      </el-form-item>
      <el-form-item label="孩子生日">
        <el-date-picker v-model="editForm.child_birthday" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
      </el-form-item>
      <el-form-item label="当前鞋码">
        <el-input v-model="editForm.current_size" placeholder="如 28" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="editVisible = false">取消</el-button>
      <el-button type="primary" :loading="editLoading" @click="submitEdit">保存修改</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="historyVisible" title="消费记录" :width="isMobile ? '92%' : '600px'">
    <div v-loading="historyLoading">
      <template v-if="historyData">
        <p>
          {{ historyData.member.name }} · 积分 {{ historyData.member.points }} · 累计消费 ¥{{ historyData.member.total_spent }}
        </p>
        <el-collapse>
          <el-collapse-item v-for="o in historyData.orders" :key="o.order_id" :title="`${o.date}  ¥${o.amount}`">
            <div v-for="(item, idx) in o.items" :key="idx">
              {{ item.product }} {{ item.color }} / {{ item.size }}码 × {{ item.qty }} = ¥{{ item.price * item.qty }}
            </div>
          </el-collapse-item>
        </el-collapse>
        <el-empty v-if="historyData.orders.length === 0" description="暂无购买记录" />
      </template>
    </div>
  </el-dialog>
</template>

<style scoped>
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.toolbar-mobile {
  flex-direction: column;
  align-items: stretch;
  gap: 10px;
}
.toolbar-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}
.mobile-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.member-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
}
.member-name {
  font-weight: 600;
  font-size: 14px;
}
.member-sub {
  color: #909399;
  font-size: 12px;
  margin-top: 4px;
}
.member-stats {
  text-align: right;
  flex-shrink: 0;
}
.member-actions {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
  flex-shrink: 0;
}
.import-tip {
  color: #909399;
  font-size: 13px;
  line-height: 1.6;
  margin-bottom: 12px;
}
.upload-text {
  padding: 20px;
  color: #909399;
}
.import-result {
  margin-top: 16px;
}
.invalid-rows {
  margin-top: 8px;
  max-height: 150px;
  overflow-y: auto;
}
.invalid-row {
  color: #f56c6c;
  font-size: 13px;
  padding: 2px 0;
}
</style>
