<template>
  <div class="app-root" :class="{ 'screen-mode': store.screenMode }">
    <header class="top-bar">
      <div class="title-wrap">
        <h1>🏭 数字孪生工厂产线实时监控系统</h1>
        <span v-if="store.screenMode" class="mode-badge">大屏展示模式 · 只读</span>
      </div>
      <div class="status-row">
        <span class="ws-dot" :class="{on: store.connected}"></span>
        <span>{{ store.connected ? '实时连接中' : '连接断开' }}</span>
        <span class="prod-count">今日产量: {{ store.data?.production || 0 }}</span>
        <el-select
          v-if="!store.screenMode"
          :model-value="store.account"
          size="small"
          class="account-select"
          @change="(v: string) => store.setAccount(v)"
        >
          <el-option
            v-for="a in store.accounts"
            :key="a.id"
            :value="a.id"
            :label="`${a.name}（${a.can_write ? '可写' : '只读'}）`"
          />
        </el-select>
        <el-button
          size="small"
          :type="store.screenMode ? 'warning' : 'primary'"
          @click="store.setScreenMode(!store.screenMode)"
        >{{ store.screenMode ? '退出大屏模式' : '进入大屏模式' }}</el-button>
      </div>
    </header>
    <div v-if="store.screenMode" class="readonly-banner">
      🔒 当前为大屏只读展示模式：参数修改与保存入口已关闭，所有账号均为受控视图，越权操作不会改动数据；页面标题、图例与数值口径与正常模式一致。按 Esc 或点击右上角按钮退出。
    </div>
    <div class="main-grid">
      <div class="scene-col"><FactoryScene /></div>
      <div class="panel-col">
        <DeviceList />
        <AnomalyList />
        <ConfigPanel v-if="!store.screenMode" />
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
import ConfigPanel from './components/ConfigPanel.vue'
import OEEChart from './components/OEEChart.vue'
import TrendPanel from './components/TrendPanel.vue'
import FaultPie from './components/FaultPie.vue'
import { useFactoryStore } from './store/factory'
const store = useFactoryStore()

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape' && store.screenMode) store.setScreenMode(false)
}

onMounted(() => {
  store.connect()
  store.loadAccounts()
  store.loadSession()
  store.loadRules()
  window.addEventListener('keydown', onKeydown)
  if (store.screenMode) window.scrollTo(0, 0) // 刷新后仍停在大屏模式，定位到顶部
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
.title-wrap{display:flex;align-items:center;gap:12px}
.top-bar h1{font-size:1.2rem;color:#64b5f6}
.mode-badge{font-size:12px;color:#fbbf24;border:1px solid #fbbf2455;background:#fbbf2415;padding:2px 10px;border-radius:10px;white-space:nowrap}
.status-row{display:flex;gap:20px;align-items:center;font-size:13px;color:#94a3b8}
.account-select{width:150px}
.ws-dot{width:10px;height:10px;border-radius:50%;background:#ef4444}
.ws-dot.on{background:#22c55e;box-shadow:0 0 8px #22c55e}
.prod-count{color:#fbbf24;font-weight:600}
.readonly-banner{margin:12px 24px 0;padding:8px 16px;font-size:12px;color:#fbbf24;background:#fbbf2412;border:1px solid #fbbf2440;border-radius:8px}
.main-grid{display:grid;grid-template-columns:1fr 360px;gap:12px;padding:12px 24px;min-height:55vh}
.scene-col{background:#0d1b2a;border-radius:12px;border:1px solid #1e3a5f;overflow:hidden}
.panel-col{display:flex;flex-direction:column;gap:12px;overflow-y:auto;max-height:55vh}
.dashboard-row{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;padding:0 24px 16px}

/* ===== 大屏只读展示模式：更大比例铺开设备与图表面板 ===== */
.app-root.screen-mode .top-bar{padding:18px 40px}
.app-root.screen-mode .top-bar h1{font-size:1.7rem}
.app-root.screen-mode .status-row{font-size:15px;gap:28px}
.app-root.screen-mode .mode-badge{font-size:14px}
.app-root.screen-mode .readonly-banner{margin:16px 40px 0;padding:12px 20px;font-size:14px}
.app-root.screen-mode .main-grid{grid-template-columns:1fr 460px;gap:20px;padding:20px 40px;min-height:64vh}
.app-root.screen-mode .panel-col{max-height:64vh;gap:16px}
.app-root.screen-mode .dashboard-row{gap:20px;padding:0 40px 28px}
.app-root.screen-mode .panel h4,.app-root.screen-mode .chart-panel h4{font-size:17px;margin-bottom:10px}
.app-root.screen-mode .chart{height:300px}
.app-root.screen-mode .dev-list{max-height:44vh}
.app-root.screen-mode .dev-row{padding:10px 12px}
.app-root.screen-mode .dev-type{font-size:15px}
.app-root.screen-mode .dev-id{font-size:13px}
.app-root.screen-mode .dev-metrics{font-size:13px;gap:14px}
.app-root.screen-mode .anomaly-row{font-size:13px;padding:6px 0}
.app-root.screen-mode .empty{font-size:14px}
</style>
