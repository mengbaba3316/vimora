import { reactive } from 'vue'

/* 跨视图共享的轻量全局状态（无 pinia，模块单例） */
export const store = reactive({
  /**
   * 提示词库点「用起来」时挂载：{ id, name, content }
   * 工作台读取后置回 null，可自由修改、不回写库。
   */
  pendingPrompt: null,
})
