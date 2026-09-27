/* 配色板注册表：data-theme key ↔ 主题 token 块（theme.css）一一对应。
 * dark = 深色族：需挂 html.dark class（element-plus dark 变量 + color-scheme 跟随）。
 * localStorage.theme 存 key；index.html 内联脚本在首屏绘制前应用同一份深浅映射。 */
export const PALETTES = [
  { key: 'dark',      name: '炭黑 · 默认',       c1: '#f4f5f7', c2: '#131417', dark: true },
  { key: 'light',     name: '纯白',             c1: '#17181a', c2: '#ffffff', dark: false },
  { key: 'bauhaus',   name: '包豪斯红 · 哑光黑', c1: '#D82E2F', c2: '#222222', dark: true },
  { key: 'klein',     name: '克莱因蓝 · 艾绿',   c1: '#012696', c2: '#A4E2C6', dark: false },
  { key: 'sweetpink', name: '甜酷玫粉 · 炭黑',   c1: '#E6397C', c2: '#1A1A1D', dark: true },
  { key: 'cream',     name: '米白 · 星光蓝',     c1: '#41BBC8', c2: '#FCF9E8', dark: false },
  { key: 'apple',     name: '苹果青 · 奶酪色',   c1: '#73AE52', c2: '#FBF1D7', dark: false },
  { key: 'taro',      name: '香芋紫 · 莫黑',     c1: '#C98EFF', c2: '#0B0C10', dark: true },
  { key: 'mars',      name: '马尔斯绿 · 玫瑰粉', c1: '#01847F', c2: '#F9D2E4', dark: false },
]

const DARK_KEYS = new Set(PALETTES.filter(p => p.dark).map(p => p.key))

export function isDark(key) {
  return DARK_KEYS.has(key)
}

export function currentTheme() {
  const t = localStorage.getItem('theme')
  return PALETTES.some(p => p.key === t) ? t : 'dark'
}

/* 设 <html data-theme> + html.dark（EP dark 变量跟随）+ 持久化 */
export function applyTheme(key) {
  const el = document.documentElement
  el.setAttribute('data-theme', key)
  el.classList.toggle('dark', isDark(key))
  localStorage.setItem('theme', key)
}
