import { defineStore } from 'pinia'
import { ref, nextTick } from 'vue'
import axios from 'axios'
import type { FactoryData, RuleConfig, AccountInfo } from '@/types'

const SCREEN_MODE_KEY = 'dt-screen-mode'
const ACCOUNT_KEY = 'dt-account'

export const useFactoryStore = defineStore('factory', () => {
  const data = ref<FactoryData | null>(null)
  const ws = ref<WebSocket | null>(null)
  const connected = ref(false)

  // ---- 账号与权限（不同账号均为受控视图，写权限由服务端最终裁决）----
  const accounts = ref<AccountInfo[]>([])
  const account = ref(localStorage.getItem(ACCOUNT_KEY) || 'operator')
  const canWrite = ref(false)
  const accountName = ref('')

  // ---- 告警阈值配置 ----
  const rules = ref<RuleConfig[]>([])

  // ---- 大屏只读展示模式（刷新后保持，退出后恢复滚动位置）----
  const screenMode = ref(localStorage.getItem(SCREEN_MODE_KEY) === '1')
  let savedScrollY = 0

  function connect() {
    if (ws.value) return
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
    const s = new WebSocket(`${protocol}//${location.hostname}:8000/ws`)
    s.onopen = () => { connected.value = true; console.log('WS connected') }
    s.onmessage = (e) => {
      try { data.value = JSON.parse(e.data) } catch {}
    }
    s.onclose = () => { connected.value = false; ws.value = null }
    ws.value = s
  }

  function disconnect() {
    ws.value?.close()
    ws.value = null
    connected.value = false
  }

  async function loadAccounts() {
    try {
      const { data: d } = await axios.get('/api/accounts')
      accounts.value = d.accounts
    } catch {}
  }

  async function loadSession() {
    try {
      const { data: d } = await axios.get('/api/session', { params: { account: account.value } })
      canWrite.value = d.can_write
      accountName.value = d.name
    } catch {
      canWrite.value = false // 会话异常时按只读处理
    }
  }

  async function loadRules() {
    try {
      const { data: d } = await axios.get('/api/config')
      rules.value = d.rules
    } catch {}
  }

  function setAccount(id: string) {
    account.value = id
    localStorage.setItem(ACCOUNT_KEY, id)
    loadSession()
  }

  async function saveRules(list: RuleConfig[]): Promise<{ ok: boolean; msg: string }> {
    try {
      const { data: d } = await axios.put('/api/config',
        { rules: list.map(r => ({ name: r.name, threshold: r.threshold })) },
        { headers: { 'X-Account': account.value } })
      rules.value = d.rules
      return { ok: true, msg: '阈值已保存并即时生效' }
    } catch (e: any) {
      const msg = e?.response?.data?.detail || '保存失败：服务不可用'
      await loadRules() // 还原为服务端真实配置，确保本地不残留越权修改
      return { ok: false, msg }
    }
  }

  function setScreenMode(on: boolean) {
    if (on === screenMode.value) return
    if (on) {
      savedScrollY = window.scrollY
      screenMode.value = true
      localStorage.setItem(SCREEN_MODE_KEY, '1')
      nextTick(() => {
        window.scrollTo(0, 0)
        window.dispatchEvent(new Event('resize')) // 触发图表与3D场景重排
      })
    } else {
      screenMode.value = false
      localStorage.setItem(SCREEN_MODE_KEY, '0')
      nextTick(() => {
        window.scrollTo(0, savedScrollY) // 回到进入前的滚动位置
        window.dispatchEvent(new Event('resize'))
      })
    }
  }

  return {
    data, connected, connect, disconnect,
    accounts, account, canWrite, accountName,
    rules, screenMode,
    loadAccounts, loadSession, loadRules, setAccount, saveRules, setScreenMode
  }
})
