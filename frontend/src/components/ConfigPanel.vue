<template>
  <div class="panel config-panel">
    <h4>⚙️ 告警阈值配置</h4>
    <el-alert
      v-if="!store.canWrite"
      type="warning"
      :closable="false"
      class="perm-alert"
      title="只读视图：当前账号无修改权限"
      description="参数修改与保存仅对可写角色（管理员/操作员）开放；越权提交将被服务端拒绝，数据不会被改动。"
    />
    <div v-for="(r, i) in draft" :key="r.name" class="rule-row">
      <span class="rule-name">{{ r.name }}</span>
      <span class="rule-field">{{ r.field }} {{ r.op === 'gt' ? '>' : '<' }}</span>
      <el-input-number
        v-model="draft[i].threshold"
        :min="0.1"
        :max="200"
        :step="1"
        size="small"
        :disabled="!store.canWrite"
        controls-position="right"
      />
    </div>
    <div class="btn-row">
      <el-button
        type="primary"
        size="small"
        :disabled="!store.canWrite || saving"
        :loading="saving"
        @click="onSave"
      >保存阈值</el-button>
      <span v-if="!store.canWrite" class="btn-hint">只读账号不可保存</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useFactoryStore } from '../store/factory'
import type { RuleConfig } from '../types'

const store = useFactoryStore()
const draft = ref<RuleConfig[]>([])
const saving = ref(false)

// 服务端配置加载/变化后同步到本地草稿，保证展示口径与服务端一致
watch(() => store.rules, (rs) => {
  draft.value = rs.map(r => ({ ...r }))
}, { immediate: true, deep: true })

async function onSave() {
  saving.value = true
  const res = await store.saveRules(draft.value)
  saving.value = false
  if (res.ok) ElMessage.success(res.msg)
  else ElMessage.error(res.msg)
}
</script>

<style scoped>
.panel{background:#0d1b2a;border-radius:8px;padding:12px;border:1px solid #1e3a5f}
.panel h4{color:#64b5f6;margin-bottom:8px;font-size:13px}
.perm-alert{margin-bottom:8px}
.rule-row{display:flex;align-items:center;gap:8px;padding:5px 0}
.rule-name{font-size:12px;color:#e0e6ed;min-width:64px}
.rule-field{font-size:11px;color:#64748b;flex:1}
.btn-row{display:flex;align-items:center;gap:10px;margin-top:8px}
.btn-hint{font-size:11px;color:#fbbf24}
</style>
