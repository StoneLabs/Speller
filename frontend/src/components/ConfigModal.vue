<script setup>
import { ref, watch, onMounted } from 'vue'
import { fetchStrictnessLevels, fetchModels, testConnection } from '../api.js'
import { availableModels, setAvailableModels } from '../constants/models.js'

const props = defineProps({
  config: { type: Object, required: true },
  open: { type: Boolean, default: false },
})

const emit = defineEmits(['close'])

const levels = ref([])

const loadingModels = ref(false)
const modelsMessage = ref(null) // { ok: boolean, text: string }

const testing = ref(false)
const testStatus = ref(null) // { ok: boolean, text: string }

async function loadModels({ silent = false } = {}) {
  loadingModels.value = true
  if (!silent) modelsMessage.value = null
  try {
    const remote = await fetchModels({
      apiBase: props.config.apiBase,
      apiKey: props.config.apiKey,
    })
    const merged = setAvailableModels(remote)
    if (!merged.includes(props.config.model) && merged.length) {
      props.config.model = merged[0]
    }
    if (!silent) {
      modelsMessage.value = {
        ok: true,
        text: `Found ${remote.length} model${remote.length === 1 ? '' : 's'}`,
      }
    }
  } catch (e) {
    if (!silent) modelsMessage.value = { ok: false, text: e.message }
  } finally {
    loadingModels.value = false
  }
}

onMounted(async () => {
  try {
    levels.value = await fetchStrictnessLevels()
  } catch {
    levels.value = [
      { level: 1, name: 'Strict', description: 'Only clear errors and typos.' },
      { level: 2, name: 'Balanced', description: 'Errors plus minor style fixes.' },
      { level: 3, name: 'Editor', description: 'Thorough editing suggestions.' },
    ]
  }
  await loadModels({ silent: true })
})

watch(
  () => props.open,
  (isOpen) => {
    if (isOpen) {
      modelsMessage.value = null
      testStatus.value = null
      loadModels({ silent: true })
    }
  },
)

async function runTest() {
  testing.value = true
  testStatus.value = null
  try {
    const res = await testConnection({
      apiBase: props.config.apiBase,
      model: props.config.model,
      apiKey: props.config.apiKey,
    })
    testStatus.value = { ok: true, text: `Connected — model replied “${res.sample}”` }
  } catch (e) {
    testStatus.value = { ok: false, text: e.message }
  } finally {
    testing.value = false
  }
}
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="overlay" @click.self="emit('close')">
      <div class="modal" role="dialog" aria-label="Settings">
        <header class="modal-header">
          <h2>Settings</h2>
          <button class="close-btn" type="button" @click="emit('close')">×</button>
        </header>

        <div class="modal-body">
          <label class="field">
            <span>API base URL</span>
            <input v-model="config.apiBase" type="url" placeholder="http://lab-gpu2:1234" />
          </label>

          <label class="field">
            <span class="field-head">
              Model
              <button type="button" class="link-btn" :disabled="loadingModels" @click="loadModels()">
                {{ loadingModels ? 'Refreshing…' : 'Refresh' }}
              </button>
            </span>
            <select v-model="config.model">
              <option v-for="m in availableModels" :key="m" :value="m">{{ m }}</option>
            </select>
            <small v-if="modelsMessage" :class="modelsMessage.ok ? 'msg-ok' : 'msg-bad'">
              {{ modelsMessage.text }}
            </small>
          </label>

          <label class="field">
            <span>API key (optional)</span>
            <input v-model="config.apiKey" type="password" autocomplete="off" />
          </label>

          <div class="field">
            <button type="button" class="btn test-btn" :disabled="testing" @click="runTest">
              <span v-if="testing" class="spinner" /> {{ testing ? 'Testing…' : 'Test connection' }}
            </button>
            <div v-if="testStatus" class="test-status" :class="testStatus.ok ? 'msg-ok' : 'msg-bad'">
              <span class="test-icon">{{ testStatus.ok ? '✓' : '✕' }}</span>
              <span>{{ testStatus.text }}</span>
            </div>
          </div>

          <label class="field">
            <span>Context lines</span>
            <input v-model.number="config.contextRange" type="number" min="0" max="10" />
            <small>How many lines before/after each line the model sees.</small>
          </label>

          <fieldset class="field">
            <legend>Strictness</legend>
            <label v-for="lvl in levels" :key="lvl.level" class="radio">
              <input v-model.number="config.strictness" type="radio" :value="lvl.level" />
              <span class="radio-body">
                <strong>{{ lvl.name }}</strong>
                <span>{{ lvl.description }}</span>
              </span>
            </label>
          </fieldset>
        </div>

        <footer class="modal-footer">
          <button type="button" class="btn primary" @click="emit('close')">Done</button>
        </footer>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  background: rgba(24, 20, 16, 0.35);
  backdrop-filter: blur(3px);
  display: flex;
  justify-content: flex-end;
  padding: 72px 24px 24px;
  z-index: 100;
}

.modal {
  width: min(440px, 100%);
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 14px;
  box-shadow: var(--shadow);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 18px;
  border-bottom: 1px solid var(--border);
}

.modal-header h2 {
  margin: 0;
  font-size: 1rem;
}

.close-btn {
  border: none;
  background: none;
  font-size: 1.4rem;
  cursor: pointer;
  color: var(--text-muted);
}

.modal-body {
  padding: 16px 18px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  max-height: 70vh;
  overflow: auto;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  border: none;
  margin: 0;
  padding: 0;
}

.field span,
.field legend {
  font-size: 0.82rem;
  color: var(--text-muted);
}

.field input,
.field select {
  padding: 8px 10px;
  border: 1px solid var(--border);
  border-radius: 8px;
  font-family: var(--font-mono);
  font-size: 0.86rem;
}

.field small {
  font-size: 0.78rem;
  color: var(--text-muted);
}

.field-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.link-btn {
  border: none;
  background: none;
  padding: 0;
  font-size: 0.78rem;
  color: var(--accent);
  cursor: pointer;
  text-decoration: underline;
}

.link-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
  text-decoration: none;
}

.msg-ok {
  color: var(--success) !important;
}

.msg-bad {
  color: var(--error) !important;
}

.test-btn {
  align-self: flex-start;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.test-status {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  font-size: 0.82rem;
  line-height: 1.4;
}

.test-icon {
  font-weight: 700;
}

.spinner {
  width: 11px;
  height: 11px;
  border: 2px solid currentColor;
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  display: inline-block;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.radio {
  display: flex;
  gap: 10px;
  padding: 10px;
  border: 1px solid var(--border);
  border-radius: 8px;
  margin-top: 8px;
  cursor: pointer;
}

.radio:has(input:checked) {
  border-color: var(--accent);
  background: rgba(74, 107, 92, 0.06);
}

.radio-body {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 0.85rem;
}

.radio-body span:last-child {
  color: var(--text-muted);
  font-size: 0.8rem;
}

.modal-footer {
  padding: 12px 18px 16px;
  border-top: 1px solid var(--border);
  display: flex;
  justify-content: flex-end;
}

.btn {
  padding: 8px 14px;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: #fff;
  cursor: pointer;
}

.btn.subtle {
  align-self: flex-start;
  font-size: 0.82rem;
}

.btn.primary {
  background: var(--accent);
  border-color: var(--accent);
  color: #fff;
}
</style>
