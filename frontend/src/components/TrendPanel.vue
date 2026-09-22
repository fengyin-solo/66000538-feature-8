<template>
  <div class="chart-panel"><h4>📈 温度/振动趋势</h4><div ref="chart" class="chart"></div></div>
</template>
<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import { useFactoryStore } from '../store/factory'
const store = useFactoryStore(); const chart = ref<HTMLDivElement>(); let inst: echarts.ECharts|null=null
function update() {
  if (!inst||!store.data) return
  const ds = store.data.devices.slice(0,4)
  inst.setOption({
    backgroundColor:'transparent', grid:{left:40,right:15,top:10,bottom:25},
    xAxis:{type:'category',data:ds.map(d=>d.type+'-'+d.id),axisLabel:{color:'#94a3b8',fontSize:9,rotate:20}},
    yAxis:{type:'value',axisLabel:{color:'#94a3b8'}},
    series:[
      {type:'bar',data:ds.map(d=>d.temperature),name:'温度°C',itemStyle:{color:'#f97316'}},
      {type:'line',data:ds.map(d=>d.vibration*20),name:'振动',itemStyle:{color:'#a78bfa'},smooth:true}
    ],animation:false
  })
}
function resize(){ inst?.resize() }
onMounted(()=>{if(chart.value){inst=echarts.init(chart.value);update()};window.addEventListener('resize',resize)})
watch(()=>store.data,update)
onUnmounted(()=>{window.removeEventListener('resize',resize);inst?.dispose()})
</script>
<style scoped>.chart-panel{background:#0d1b2a;border-radius:8px;padding:12px;border:1px solid #1e3a5f}.chart-panel h4{color:#64b5f6;font-size:13px;margin-bottom:4px}.chart{width:100%;height:200px}</style>