import { reactive, watch } from 'vue'
import { syncModelList } from '../constants/models.js'

const STORAGE_KEY = 'speller-config'

const defaults = {
  apiBase: '',
  model: '',
  apiKey: '',
  contextRange: 2,
  strictness: 2,
}

function load() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const config = { ...defaults, ...JSON.parse(raw) }
      syncModelList(config.model)
      return config
    }
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
      syncModelList(value.model)
    },
    { deep: true },
  )

  return { config, defaults }
}
