<script setup>
import { ref, computed, onMounted } from 'vue'
import ManuscriptEditor from './components/ManuscriptEditor.vue'
import ReviewGrid from './components/ReviewGrid.vue'
import ConfigModal from './components/ConfigModal.vue'
import { useConfig } from './composables/useConfig.js'
import { checkLine } from './api.js'
import { extractParagraphs } from './utils/document.js'
import { availableModels } from './constants/models.js'

const { config } = useConfig()

const mode = ref('edit') // 'edit' | 'review'
const editorHtml = ref('')
const editorRef = ref(null)

const paragraphs = ref([])
const results = ref([])
const checking = ref(false)
const checkingIndex = ref(-1)
const configOpen = ref(false)
const progress = ref({ done: 0, total: 0 })

const phase = ref('idle') // idle | checking | done | error
const issueCount = ref(0)
const errorMessage = ref('')

const statusText = computed(() => {
  if (phase.value === 'checking') {
    return `Reviewing paragraph ${Math.max(progress.value.done + 1, 1)} of ${progress.value.total}…`
  }
  if (phase.value === 'done') {
    if (issueCount.value === 0) return 'Review complete — nothing to flag'
    if (issueCount.value === 1) return 'Review complete — 1 note'
    return `Review complete — ${issueCount.value} notes`
  }
  if (phase.value === 'error') return errorMessage.value
  return mode.value === 'review' ? 'Reviewed' : 'Ready'
})

const statusClass = computed(() => ({ 'status-pill': true, [phase.value]: true }))

function shortModelName(id) {
  return id.split('/').pop() || id
}

function countNotes() {
  return results.value.reduce(
    (sum, r) => sum + (r?.issues?.length || 0) + (r?.hint ? 1 : 0),
    0,
  )
}

async function runReview() {
  const paras = extractParagraphs(editorHtml.value)
  if (!paras.length) {
    phase.value = 'error'
    errorMessage.value = 'Nothing to review — write or paste some text first.'
    return
  }

  paragraphs.value = paras
  results.value = paras.map(() => null)
  mode.value = 'review'
  checking.value = true
  phase.value = 'checking'
  progress.value = { done: 0, total: paras.length }

  const texts = paras.map((p) => p.text)
  const markdowns = paras.map((p) => p.markdown || p.text)
  const range = config.contextRange
  let lastError = ''

  for (let i = 0; i < paras.length; i++) {
    checkingIndex.value = i
    try {
      results.value[i] = await checkLine({
        targetLine: markdowns[i],
        lineNumber: i + 1,
        contextBefore: texts.slice(Math.max(0, i - range), i),
        contextAfter: texts.slice(i + 1, Math.min(texts.length, i + 1 + range)),
        strictness: config.strictness,
        apiBase: config.apiBase,
        model: config.model,
        apiKey: config.apiKey,
      })
    } catch (e) {
      // One bad paragraph shouldn't abort the whole review.
      lastError = e.message
      results.value[i] = {
        line_number: i + 1,
        issues: [],
        notes: [],
        hint: null,
        error: e.message,
      }
    }
    progress.value.done = i + 1
  }

  checking.value = false
  checkingIndex.value = -1
  issueCount.value = countNotes()

  const failures = results.value.filter((r) => r?.error).length
  if (failures === paras.length) {
    phase.value = 'error'
    errorMessage.value = lastError || 'Review failed for every paragraph.'
  } else {
    phase.value = 'done'
  }
}

function backToEdit() {
  mode.value = 'edit'
  phase.value = 'idle'
  errorMessage.value = ''
}

onMounted(() => {
  if (editorRef.value) editorRef.value.focus()
})
</script>

<template>
  <div class="app">
    <header class="topbar">
      <div class="brand">
        <h1>Speller</h1>
        <p>AI grammar for authors · local & private</p>
      </div>

      <div class="status-bar">
        <div :class="statusClass">
          <span class="status-dot" />
          <span class="status-main">{{ statusText }}</span>
          <span v-if="phase !== 'error'" class="status-sub">{{ shortModelName(config.model) }}</span>
        </div>
      </div>

      <div class="actions">
        <label class="model-select">
          <span class="sr-only">Model</span>
          <select v-model="config.model" :disabled="checking">
            <option v-for="m in availableModels" :key="m" :value="m">{{ shortModelName(m) }}</option>
          </select>
        </label>

        <button
          v-if="mode === 'edit'"
          type="button"
          class="btn primary"
          @click="runReview"
        >
          Review Manuscript
        </button>

        <template v-else>
          <button type="button" class="btn" :disabled="checking" @click="backToEdit">
            ← Edit
          </button>
          <button type="button" class="btn primary" :disabled="checking" @click="runReview">
            {{ checking ? 'Reviewing…' : 'Re-review' }}
          </button>
        </template>

        <button type="button" class="btn ghost" @click="configOpen = true">Settings</button>
      </div>
    </header>

    <ManuscriptEditor
      v-show="mode === 'edit'"
      ref="editorRef"
      v-model:html="editorHtml"
    />

    <ReviewGrid
      v-if="mode === 'review'"
      :paragraphs="paragraphs"
      :results="results"
      :checking-index="checkingIndex"
    />

    <ConfigModal :config="config" :open="configOpen" @close="configOpen = false" />
  </div>
</template>

<style scoped>
.app {
  height: 100vh;
  display: flex;
  flex-direction: column;
  padding: 18px 22px 22px;
  gap: 14px;
}

.topbar {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 16px;
}

.brand h1 {
  margin: 0;
  font-family: var(--font-serif);
  font-size: 1.6rem;
  font-weight: 600;
  letter-spacing: -0.02em;
}

.brand p {
  margin: 2px 0 0;
  font-size: 0.88rem;
  color: var(--text-muted);
}

.status-bar {
  min-width: 0;
  display: flex;
  justify-content: center;
}

.status-pill {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  border-radius: 999px;
  border: 1px solid var(--border);
  background: rgba(255, 255, 255, 0.7);
  min-width: 0;
  max-width: 100%;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
  background: var(--gutter);
}

.status-pill.idle .status-dot,
.status-pill.done .status-dot {
  background: var(--success);
}

.status-pill.checking .status-dot {
  background: var(--accent);
  animation: pulse 1.2s ease infinite;
}

.status-pill.error .status-dot {
  background: var(--error);
}

.status-main {
  font-size: 0.86rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.status-sub {
  font-family: var(--font-mono);
  font-size: 0.72rem;
  color: var(--text-muted);
  white-space: nowrap;
  padding-left: 8px;
  border-left: 1px solid var(--border-subtle);
  flex-shrink: 0;
}

.status-pill.error .status-main {
  color: var(--error);
  white-space: normal;
}

@keyframes pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.35;
  }
}

.actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.model-select select {
  padding: 8px 12px;
  border: 1px solid var(--border);
  border-radius: 999px;
  background: #fff;
  font-family: var(--font-mono);
  font-size: 0.8rem;
  color: var(--ink);
  max-width: 180px;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
}

.btn {
  border: 1px solid var(--border);
  background: #fff;
  color: var(--ink);
  border-radius: 999px;
  padding: 9px 16px;
  font-size: 0.9rem;
  cursor: pointer;
  white-space: nowrap;
}

.btn.primary {
  background: var(--accent);
  border-color: var(--accent);
  color: #fff;
}

.btn.ghost {
  background: transparent;
}

.btn:disabled,
.model-select select:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.btn:not(:disabled):hover {
  filter: brightness(1.03);
}

@media (max-width: 900px) {
  .topbar {
    grid-template-columns: 1fr;
  }
  .status-bar {
    justify-content: flex-start;
  }
}
</style>
