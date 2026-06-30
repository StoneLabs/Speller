import { reactive, watch } from 'vue'
import { syncModelList } from '../constants/models.js'

const STORAGE_KEY = 'speller-config'

let serverDefaults = null

const baseDefaults = {
  apiBase: '',
  model: '',
  apiKey: '',
  contextRange: 4,
  strictness: 2,
}

async function fetchServerDefaults() {
  try {
    const res = await fetch('/api/defaults')
    if (!res.ok) return null
    const data = await res.json()
    if (!data.api_base) return null
    return data
  } catch {
    return null
  }
}

export async function initConfig() {
  serverDefaults = await fetchServerDefaults()
}

function load() {
  const defaults = {
    ...baseDefaults,
    apiBase: serverDefaults?.api_base || baseDefaults.apiBase,
  }

  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const saved = JSON.parse(raw)
      const config = { ...defaults, ...saved }
      if (!saved.apiBase && defaults.apiBase) config.apiBase = defaults.apiBase
      syncModelList(config.model)
      return config
    }
  } catch {
    /* ignore */
  }

  syncModelList(defaults.model)
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

  return { config, defaults: baseDefaults }
}
