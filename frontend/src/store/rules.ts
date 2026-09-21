import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { AnomalyRule } from '@/types'
import { useViewStore } from './view'

export const useRulesStore = defineStore('rules', () => {
  const rules = ref<AnomalyRule[]>([])
  const loaded = ref(false)
  const saving = ref(false)
  const lastError = ref('')

  // 草稿与已保存值分离：只有点击“保存”且服务端接受后才真正生效
  const draft = ref<AnomalyRule[]>([])

  async function fetchRules() {
    const res = await fetch('/api/rules')
    if (!res.ok) throw new Error('阈值参数加载失败')
    const body = await res.json()
    rules.value = body.rules
    draft.value = body.rules.map((r: AnomalyRule) => ({ ...r }))
    loaded.value = true
  }

  function resetDraft() {
    draft.value = rules.value.map((r) => ({ ...r }))
    lastError.value = ''
  }

  /**
   * 保存阈值参数。
   * 只读大屏模式下前端直接拒绝；即便绕过前端，后端也会依据
   * X-View-Mode 头再次拒绝（403），双重保证越权操作不改动数据。
   */
  async function saveRules(): Promise<{ ok: boolean; message: string }> {
    const view = useViewStore()
    if (view.readonly) {
      lastError.value = '大屏只读模式下不可修改或保存参数'
      return {
        ok: false,
        message: '当前为大屏只读展示模式：改参数与保存入口不可用，请退出只读模式后再操作。',
      }
    }

    saving.value = true
    lastError.value = ''
    try {
      const res = await fetch('/api/rules', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          // 向服务端声明当前视图模式，只读模式不允许写
          'X-View-Mode': view.mode,
        },
        body: JSON.stringify(
          draft.value.map((r) => ({ field: r.field, threshold: Number(r.threshold) })),
        ),
      })
      const body = await res.json().catch(() => ({}))
      if (res.status === 403) {
        lastError.value = body.detail || '只读模式禁止保存'
        return { ok: false, message: body.detail || '只读模式禁止保存' }
      }
      if (!res.ok) {
        lastError.value = body.detail || '保存失败'
        return { ok: false, message: body.detail || '保存失败' }
      }
      rules.value = body.rules
      draft.value = body.rules.map((r: AnomalyRule) => ({ ...r }))
      return { ok: true, message: '阈值参数已保存并即时生效' }
    } finally {
      saving.value = false
    }
  }

  return { rules, draft, loaded, saving, lastError, fetchRules, resetDraft, saveRules }
})
