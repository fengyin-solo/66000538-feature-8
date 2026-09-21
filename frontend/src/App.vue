<template>
  <div class="app-root" :class="{ 'is-readonly': view.readonly }">
    <header class="top-bar">
      <h1>🏭 数字孪生工厂产线实时监控系统</h1>
      <div class="status-row">
        <span class="ws-dot" :class="{on: store.connected}"></span>
        <span>{{ store.connected ? '实时连接中' : '连接断开' }}</span>
        <span class="prod-count">今日产量: {{ store.data?.production || 0 }}</span>
        <span v-if="view.readonly" class="ro-badge">👁 只读展示</span>
        <el-button
          v-if="!view.readonly"
          size="small"
          type="primary"
          plain
          @click="view.enterReadonly()"
        >
          🖥️ 进入大屏
        </el-button>
        <el-button v-else size="small" plain @click="view.exitReadonly()">
          退出大屏 (Esc)
        </el-button>
      </div>
    </header>

    <div v-if="view.readonly" class="lock-banner" role="status">
      🔒 大屏只读展示模式：已隐去参数修改与保存等操作入口，当前视图仅供展示，任何账号均无法改动数据。
    </div>

    <div class="main-grid">
      <div class="scene-col"><FactoryScene /></div>
      <div class="panel-col">
        <DeviceList class="device-panel" />
        <AnomalyList class="anomaly-panel" />
        <RuleSettings />
      </div>
    </div>
    <div class="dashboard-row">
      <OEEChart />
      <TrendPanel />
      <FaultPie />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import FactoryScene from './components/FactoryScene.vue'
import DeviceList from './components/DeviceList.vue'
import AnomalyList from './components/AnomalyList.vue'
import OEEChart from './components/OEEChart.vue'
import TrendPanel from './components/TrendPanel.vue'
import FaultPie from './components/FaultPie.vue'
import RuleSettings from './components/RuleSettings.vue'
import { useFactoryStore } from './store/factory'
import { useViewStore } from './store/view'
import { useRulesStore } from './store/rules'

const store = useFactoryStore()
const view = useViewStore()
const rulesStore = useRulesStore()

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape' && view.readonly) view.exitReadonly()
}

onMounted(() => {
  store.connect()
  rulesStore.fetchRules().catch(() => {})
  window.addEventListener('keydown', onKeydown)
})
onUnmounted(() => {
  store.disconnect()
  window.removeEventListener('keydown', onKeydown)
})
</script>

<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:system-ui,sans-serif;background:#0a1628;color:#e0e6ed;overflow-x:hidden}
.app-root{min-height:100vh}
.top-bar{display:flex;justify-content:space-between;align-items:center;padding:12px 24px;background:linear-gradient(90deg,#0d2137,#1a3a5c);border-bottom:1px solid #1e3a5f}
.top-bar h1{font-size:1.2rem;color:#64b5f6}
.status-row{display:flex;gap:20px;align-items:center;font-size:13px;color:#94a3b8}
.ws-dot{width:10px;height:10px;border-radius:50%;background:#ef4444}
.ws-dot.on{background:#22c55e;box-shadow:0 0 8px #22c55e}
.prod-count{color:#fbbf24;font-weight:600}
.main-grid{display:grid;grid-template-columns:1fr 360px;gap:12px;padding:12px 24px;min-height:55vh}
.scene-col{background:#0d1b2a;border-radius:12px;border:1px solid #1e3a5f;overflow:hidden}
.panel-col{display:flex;flex-direction:column;gap:12px;overflow-y:auto;max-height:55vh}
.dashboard-row{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;padding:0 24px 16px}

/* ============ 大屏只读展示模式 ============ */
/* 标题/图例/数值口径保持不变，仅放大面板与字号、铺满整屏；操作入口隐去 */
.lock-banner{
  margin:10px 24px 0;padding:8px 16px;border-radius:8px;font-size:14px;
  background:#1e293b;border:1px solid #475569;color:#cbd5e1;
}
.ro-badge{
  padding:2px 10px;border-radius:999px;font-size:12px;font-weight:600;
  background:#1e293b;border:1px solid #475569;color:#cbd5e1;
}
.app-root.is-readonly{height:100vh;display:flex;flex-direction:column;overflow:hidden}
.app-root.is-readonly .top-bar{padding:18px 32px;flex:none}
.app-root.is-readonly .top-bar h1{font-size:1.7rem}
.app-root.is-readonly .status-row{font-size:16px;gap:28px}
.app-root.is-readonly .main-grid{
  flex:1;min-height:0;grid-template-columns:1fr 460px;
  gap:18px;padding:18px 32px 10px;
}
.app-root.is-readonly .panel-col{max-height:none;overflow:hidden;gap:16px}
.app-root.is-readonly .scene-col{border-radius:14px}
.app-root.is-readonly .dashboard-row{flex:none;height:34vh;padding:0 32px 20px;gap:18px}
.app-root.is-readonly .dashboard-row .chart-panel,
.app-root.is-readonly .panel-col .panel{padding:16px 18px}
.app-root.is-readonly .dashboard-row .chart-panel h4,
.app-root.is-readonly .panel-col .panel h4{font-size:16px}
.app-root.is-readonly .dashboard-row .chart-panel{display:flex;flex-direction:column;min-height:0}
.app-root.is-readonly .dashboard-row .chart{height:calc(100% - 34px)}
.app-root.is-readonly .panel-col .panel{display:flex;flex-direction:column;min-height:0}
.app-root.is-readonly .device-panel{flex:1.2}
.app-root.is-readonly .anomaly-panel{flex:1}
.app-root.is-readonly .dev-list{max-height:none;flex:1;min-height:0;overflow-y:auto;gap:8px}
.app-root.is-readonly .dev-row{padding:10px 12px}
.app-root.is-readonly .dev-type{font-size:15px}
.app-root.is-readonly .dev-id{font-size:13px}
.app-root.is-readonly .dev-metrics{font-size:14px;gap:16px}
.app-root.is-readonly .anomaly-panel{display:flex;flex-direction:column;min-height:0}
.app-root.is-readonly .anomaly-row{font-size:14px;padding:6px 0}
.app-root.is-readonly .empty{font-size:14px}
</style>
