<template>
  <div class="chart-panel">
    <h4>📐 OEE设备综合效率</h4>
    <div ref="chart" class="chart"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import { useFactoryStore } from '../store/factory'
const store = useFactoryStore(); const chart = ref<HTMLDivElement>(); let inst: echarts.ECharts|null=null

function update() {
  if (!inst || !store.data) return
  const oee = store.data.oee
  inst.setOption({
    backgroundColor:'transparent', grid:{left:30,right:15,top:10,bottom:25},
    xAxis:{type:'category',data:oee.map(d=>d.type+'-'+d.id),axisLabel:{color:'#94a3b8',fontSize:9,rotate:30}},
    yAxis:{type:'value',max:100,axisLabel:{color:'#94a3b8'}},
    series:[
      {type:'bar',data:oee.map(d=>d.availability),name:'可用性',itemStyle:{color:'#22c55e'},barGap:0},
      {type:'bar',data:oee.map(d=>d.performance),name:'性能',itemStyle:{color:'#fbbf24'},barGap:0},
      {type:'bar',data:oee.map(d=>d.quality),name:'质量',itemStyle:{color:'#3b82f6'},barGap:0},
      {type:'line',data:oee.map(d=>d.oee),name:'OEE',symbol:'diamond',lineStyle:{color:'#f87171',width:2}}
    ],
    animation:false,legend:{bottom:0,textStyle:{color:'#94a3b8',fontSize:10}}
  })
}
const ro = new ResizeObserver(() => inst?.resize())
onMounted(()=>{if(chart.value){inst=echarts.init(chart.value);update();ro.observe(chart.value)}})
watch(()=>store.data,update)
onUnmounted(()=>{ro.disconnect();inst?.dispose()})
</script>
<style scoped>.chart-panel{background:#0d1b2a;border-radius:8px;padding:12px;border:1px solid #1e3a5f}.chart-panel h4{color:#64b5f6;font-size:13px;margin-bottom:4px}.chart{width:100%;height:200px}</style>