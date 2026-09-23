import { createRouter, createWebHistory } from 'vue-router'
import Workbench from './views/Workbench.vue'
import Prompts from './views/Prompts.vue'
import Libraries from './views/Libraries.vue'
import Providers from './views/Providers.vue'
import History from './views/History.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'workbench', component: Workbench },
    { path: '/prompts', name: 'prompts', component: Prompts },
    { path: '/libraries', name: 'libraries', component: Libraries },
    { path: '/providers', name: 'providers', component: Providers },
    { path: '/history', name: 'history', component: History },
  ],
})

export default router
