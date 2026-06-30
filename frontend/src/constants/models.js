import { ref } from 'vue'

export const DEFAULT_MODELS = [
  'qwen/qwen3.6-27b',
  'mistralai/mistral-7b-instruct-v0.3',
]

// Shared across the top bar selector and the Settings modal.
export const availableModels = ref([...DEFAULT_MODELS])

export function setAvailableModels(list) {
  const merged = [...new Set([...DEFAULT_MODELS, ...list])]
  availableModels.value = merged
  return merged
}
