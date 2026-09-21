<template>
  <div v-if="!view.readonly" class="panel rule-panel">
    <h4>🛠️ 告警阈值参数</h4>
    <p class="hint">编辑检测阈值后点击“保存”，参数即时生效。</p>
    <div class="rule-list">
      <div v-for="(r, i) in rulesStore.draft" :key="r.field" class="rule-row">
        <span class="rule-name">{{ r.name }}</span>
        <el-input-number
          v-model="rulesStore.draft[i].threshold"
          :step="0.1"
          :precision="2"
          :controls="false"
          size="small"
          class="rule-input"
        />
        <span class="rule-unit">{{ r.unit }}</span>
      </div>
    </div>
    <div class="rule-actions">
      <el-button type="primary" size="small" :loading="rulesStore.saving" @click="onSave">
        保存
      </el-button>
      <el-button size="small" :disabled="rulesStore.saving" @click="rulesStore.resetDraft()">
        重置
      </el-button>
      <span v-if="rulesStore.lastError" class="save-err">{{ rulesStore.lastError }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { useRulesStore } from '../store/rules'
import { useViewStore } from '../store/view'

const rulesStore = useRulesStore()
const view = useViewStore()

async function onSave() {
  const { ok, message } = await rulesStore.saveRules()
  ok ? ElMessage.success(message) : ElMessage.warning(message)
}
</script>

<style scoped>
.rule-panel { padding: 12px; }
.rule-panel h4 { color: #64b5f6; margin-bottom: 6px; font-size: 13px; }
.hint { color: #64748b; font-size: 11px; margin-bottom: 8px; }
.rule-list { display: flex; flex-direction: column; gap: 6px; }
.rule-row { display: flex; align-items: center; gap: 8px; }
.rule-name { font-size: 12px; color: #e0e6ed; flex: 1; }
.rule-input { width: 90px; }
.rule-unit { font-size: 11px; color: #94a3b8; width: 42px; }
.rule-actions { display: flex; align-items: center; gap: 8px; margin-top: 10px; }
.save-err { color: #f87171; font-size: 11px; }
</style>
