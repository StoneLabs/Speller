import { reactive, watch } from 'vue'

const STORAGE_KEY = 'speller-config'

const defaults = {
  apiBase: 'http://lab-gpu2:1234',
  model: 'qwen/qwen3.6-27b',
  apiKey: '',
  contextRange: 2,
  strictness: 2,
}

function load() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) return { ...defaults, ...JSON.parse(raw) }
  } catch {
    /* ignore */
  }
  return { ...defaults }
}

export function useConfig() {
  const config = reactive(load())

  watch(
    config,
    (value) => {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(value))
    },
    { deep: true },
  )

  return { config, defaults }
}
