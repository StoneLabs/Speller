import { ref } from 'vue'

export const availableModels = ref([])

export function syncModelList(selectedModel = '') {
  if (!selectedModel) return
  if (!availableModels.value.includes(selectedModel)) {
    availableModels.value = [selectedModel, ...availableModels.value]
  }
}

export function setAvailableModels(list, selectedModel = '') {
  const items = Array.isArray(list) ? list : []
  const merged = [...new Set([selectedModel, ...items].filter(Boolean))]
  availableModels.value = merged
  return merged
}
