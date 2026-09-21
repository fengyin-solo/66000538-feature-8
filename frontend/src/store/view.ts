import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

const STORAGE_KEY = 'factory.viewMode'

export type ViewMode = 'interactive' | 'readonly'

/**
 * 视图模式状态：交互模式 / 大屏只读展示模式。
 *
 * - 模式持久化在 localStorage，刷新后仍停在进入前的模式；
 * - 只读模式是“受控视图”，与具体账号无关，任何账号进入都看到同一套只读大屏；
 * - 进入只读模式时记录原布局滚动位置，退出时还原。
 */
export const useViewStore = defineStore('view', () => {
  const initial: ViewMode =
    localStorage.getItem(STORAGE_KEY) === 'readonly' ? 'readonly' : 'interactive'

  const mode = ref<ViewMode>(initial)
  const readonly = ref(initial === 'readonly')

  // 进入只读模式前交互布局的滚动位置
  let savedScrollY = 0

  function enterReadonly() {
    savedScrollY = window.scrollY
    mode.value = 'readonly'
  }

  function exitReadonly() {
    mode.value = 'interactive'
    // 布局恢复后再还原滚动位置，避免在大屏布局上发生跳动
    requestAnimationFrame(() =>
      requestAnimationFrame(() => window.scrollTo({ top: savedScrollY })),
    )
  }

  function toggle() {
    readonly.value ? exitReadonly() : enterReadonly()
  }

  // 锁定背景滚动：只读大屏为单屏展示，不产生页面级滚动
  watch(mode, (m) => {
    readonly.value = m === 'readonly'
    localStorage.setItem(STORAGE_KEY, m)
    document.body.style.overflow = m === 'readonly' ? 'hidden' : ''
  }, { immediate: true })

  return { mode, readonly, enterReadonly, exitReadonly, toggle }
})
