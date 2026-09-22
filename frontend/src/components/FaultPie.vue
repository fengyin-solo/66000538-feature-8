<template>
  <div class="chart-panel"><h4>🥧 故障分布</h4><div ref="chart" class="chart"></div></div>
</template>
<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import { useFactoryStore } from '../store/factory'
import { DEVICE_COLORS } from '../types'
const store = useFactoryStore(); const chart = ref<HTMLDivElement>(); let inst: echarts.ECharts|null=null
function update() {
  if (!inst||!store.data) return
  const faults: Record<string,number> = {}
  store.data.devices.forEach(d=>{ faults[d.type] = (faults[d.type]||0) + d.fault_count })
  const data = Object.entries(faults).map(([k,v])=>({name:k,value:v}))
  inst.setOption({
    backgroundColor:'transparent',
    series:[{type:'pie',data,radius:['45%','75%'],center:['50%','55%'],label:{color:'#94a3b8',fontSize:10},
      itemStyle:{borderColor:'#0d1b2a',borderWidth:2}}],animation:false
  })
}
function resize(){ inst?.resize() }
onMounted(()=>{if(chart.value){inst=echarts.init(chart.value);update()};window.addEventListener('resize',resize)})
watch(()=>store.data,update)
onUnmounted(()=>{window.removeEventListener('resize',resize);inst?.dispose()})
</script>
<style scoped>.chart-panel{background:#0d1b2a;border-radius:8px;padding:12px;border:1px solid #1e3a5f}.chart-panel h4{color:#64b5f6;font-size:13px;margin-bottom:4px}.chart{width:100%;height:200px}</style>