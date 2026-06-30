<script setup>
import { ref, watch, onMounted, nextTick } from 'vue'
import { applyIssueMarks } from '../utils/document.js'

const props = defineProps({
  paragraphs: { type: Array, default: () => [] },
  results: { type: Array, default: () => [] },
  checkingIndex: { type: Number, default: -1 },
})

const textRefs = ref([])
/** @type {Record<number, 'original' | 'corrected'>} */
const viewMode = ref({})

function setTextRef(el, index) {
  if (el) textRefs.value[index] = el
}

function result(index) {
  return props.results[index] ?? null
}

function status(index) {
  if (props.checkingIndex === index) return 'checking'
  const r = result(index)
  if (!r) return 'pending'
  if (r.error) return 'error'
  if (r.issues?.length || r.notes?.length || r.hint) return 'notes'
  return 'clean'
}

function isClean(index) {
  return status(index) === 'clean'
}

function hasCorrection(index) {
  const r = result(index)
  if (!r || r.error) return false
  return Boolean(r.corrected && r.corrected !== r.original)
}

function showingCorrected(index) {
  return viewMode.value[index] === 'corrected'
}

function toggleView(index) {
  viewMode.value[index] = showingCorrected(index) ? 'original' : 'corrected'
  nextTick(() => renderText(index))
}

function renderText(index) {
  const el = textRefs.value[index]
  const para = props.paragraphs[index]
  const r = result(index)
  if (!el || !para) return

  el.classList.remove('is-clean', 'is-corrected-view')

  if (isClean(index)) {
    el.classList.add('is-clean')
  }

  if (showingCorrected(index) && r?.corrected) {
    el.classList.add('is-corrected-view')
    el.textContent = r.corrected
    return
  }

  el.innerHTML = para.html
  if (r?.issues?.length) applyIssueMarks(el, r.issues)
}

function renderAll() {
  props.paragraphs.forEach((_, i) => renderText(i))
}

onMounted(() => nextTick(renderAll))

watch(
  () => props.paragraphs,
  () => nextTick(renderAll),
  { deep: false },
)

watch(
  () => props.results,
  () => {
    viewMode.value = {}
    nextTick(renderAll)
  },
  { deep: true },
)
</script>

<template>
  <div class="review-wrap">
    <div class="review-grid">
      <div class="ghead ghead-num" />
      <div class="ghead ghead-manuscript">
        <span>Manuscript</span>
        <span class="format-note">Bold, <em>italic</em>, and underline are preserved and sent to the model.</span>
      </div>
      <div class="ghead ghead-notes">Marginalia</div>

      <template v-for="(para, index) in paragraphs" :key="para.id">
        <div class="gnum" :class="{ active: checkingIndex === index, clean: isClean(index) }">
          <span class="line-num">{{ index + 1 }}</span>
        </div>

        <div
          class="gtext-cell"
          :class="{ 'is-ai-view': showingCorrected(index) && hasCorrection(index) }"
        >
          <button
            v-if="hasCorrection(index)"
            type="button"
            class="view-toggle"
            :class="{ on: showingCorrected(index) }"
            :title="showingCorrected(index) ? 'Show original with marks' : 'Show AI-corrected text'"
            :aria-label="showingCorrected(index) ? 'Show original' : 'Show AI correction'"
            @click="toggleView(index)"
          >
            ↻
          </button>
          <div class="gtext" :ref="(el) => setTextRef(el, index)" />
          <span v-if="showingCorrected(index) && hasCorrection(index)" class="ai-version-badge">
            AI Version
          </span>
        </div>

        <div class="gnotes" :data-status="status(index)">
          <div v-if="status(index) === 'checking'" class="note-checking">
            <span class="spinner" /> Reviewing…
          </div>

          <div v-else-if="status(index) === 'error'" class="note-error">
            {{ result(index).error }}
          </div>

          <div v-else-if="status(index) === 'notes'" class="note-content">
            <div v-if="result(index).issues?.length" class="edits">
              <div class="edits-label">Suggested edits</div>
              <div v-for="(issue, i) in result(index).issues" :key="i" class="edit-row">
                <span v-if="issue.original" class="from">{{ issue.original }}</span>
                <span v-if="issue.original && issue.suggestion" class="arrow">→</span>
                <span v-if="issue.suggestion" class="to">{{ issue.suggestion }}</span>
                <span v-else-if="issue.original" class="to deleted">delete</span>
                <span v-else-if="issue.suggestion" class="to add">+ {{ issue.suggestion }}</span>
              </div>
            </div>

            <ul v-if="result(index).notes?.length" class="notes-list">
              <li v-for="(note, i) in result(index).notes" :key="i">
                <span v-if="note.type && note.type !== 'note'" class="note-tag" :data-type="note.type">{{ note.type }}</span>
                {{ note.message }}
              </li>
            </ul>

            <p v-if="result(index).hint" class="hint">{{ result(index).hint }}</p>
          </div>

          <div v-else-if="status(index) === 'clean'" class="note-clean">Looks good</div>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.review-wrap {
  flex: 1;
  min-height: 0;
  overflow: auto;
  border: 1px solid var(--border);
  border-radius: 14px;
  background: var(--paper);
  box-shadow: var(--shadow);
}

.review-grid {
  display: grid;
  grid-template-columns: 3.75rem minmax(0, 1.18fr) minmax(300px, 0.82fr);
  align-content: start;
}

.ghead {
  position: sticky;
  top: 0;
  z-index: 2;
  padding: 11px 20px;
  font-family: var(--font-mono);
  font-size: 0.68rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--text-muted);
  background: var(--paper);
  border-bottom: 1px solid var(--border);
}

.ghead-num {
  padding: 0;
}

.ghead-manuscript {
  display: flex;
  flex-direction: column;
  gap: 4px;
  text-transform: uppercase;
}

.format-note {
  font-family: var(--font-serif);
  font-size: 0.78rem;
  letter-spacing: 0;
  text-transform: none;
  color: var(--text-muted);
  opacity: 0.85;
  font-style: normal;
}

.format-note em {
  font-style: italic;
}

.ghead-notes {
  background: var(--margin-bg);
  border-left: 1px solid var(--border);
}

.gnum,
.gtext-cell,
.gnotes {
  border-bottom: 1px solid var(--border-subtle);
  padding-top: 18px;
  padding-bottom: 18px;
}

.gnum {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  justify-content: flex-start;
  padding-left: 6px;
  padding-right: 10px;
  font-family: var(--font-mono);
  font-size: 0.74rem;
  line-height: 1.2;
  color: var(--gutter);
  user-select: none;
  background: rgba(0, 0, 0, 0.015);
  border-right: 1px solid var(--border-subtle);
}

.gnum.clean {
  opacity: 0.45;
}

.gnum.active {
  opacity: 1;
  color: var(--accent);
}

.gnum.active .line-num {
  font-weight: 600;
}

.gtext-cell {
  position: relative;
  padding-left: 20px;
  padding-right: 28px;
  min-height: 3.5rem;
}

.gtext-cell.is-ai-view {
  background: rgba(196, 84, 74, 0.14);
  padding-bottom: 30px;
}

.view-toggle {
  position: absolute;
  top: 14px;
  right: 10px;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.75rem;
  height: 1.75rem;
  padding: 0;
  border: 1px solid var(--border);
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.92);
  color: var(--text-muted);
  font-size: 1rem;
  line-height: 1;
  cursor: pointer;
  opacity: 0.75;
  box-shadow: 0 2px 8px rgba(42, 30, 18, 0.08);
  transition: opacity 0.15s, border-color 0.15s, color 0.15s, background 0.15s, transform 0.15s;
}

.view-toggle:hover {
  opacity: 1;
  border-color: var(--accent);
  color: var(--accent);
  transform: scale(1.05);
}

.view-toggle.on {
  background: var(--issue-color);
  border-color: #8f3a32;
  color: #fff;
  opacity: 1;
  transform: rotate(180deg);
}

.view-toggle.on:hover {
  color: #fff;
  border-color: #7a322b;
  transform: rotate(180deg) scale(1.05);
}

.line-num {
  line-height: 1.85;
}

.gtext {
  padding-right: 2rem;
  padding-bottom: 0.25rem;
  font-family: var(--font-serif);
  font-size: 1.12rem;
  line-height: 1.85;
  color: var(--ink);
  word-break: break-word;
  transition: color 0.15s, opacity 0.15s, background 0.15s;
}

.gtext.is-clean {
  color: var(--text-muted);
  opacity: 0.52;
}

.gtext.is-corrected-view {
  color: #a83d34;
  opacity: 1;
  background: rgba(196, 84, 74, 0.1);
  border-radius: 4px;
  padding: 2px 4px;
  margin: -2px -4px;
}

.ai-version-badge {
  position: absolute;
  right: 12px;
  bottom: 10px;
  font-family: var(--font-mono);
  font-size: 1rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: #c4544a;
  -webkit-text-stroke: 0.6px #000;
  paint-order: stroke fill;
  text-shadow:
    -1px -1px 0 #000,
    1px -1px 0 #000,
    -1px 1px 0 #000,
    1px 1px 0 #000;
  pointer-events: none;
  user-select: none;
}

.gtext :deep(b),
.gtext :deep(strong) {
  font-weight: 600;
}

.gtext :deep(i),
.gtext :deep(em) {
  font-style: italic;
}

.gtext :deep(u) {
  text-decoration: underline;
}

.gtext :deep(.issue-mark) {
  text-decoration: underline wavy;
  text-decoration-color: var(--issue-color);
  text-underline-offset: 3px;
  background: rgba(196, 84, 74, 0.09);
  border-radius: 2px;
  padding: 0 1px;
}

.gtext :deep(.issue-mark.issue-insert) {
  text-decoration: none;
  color: var(--success);
  font-weight: 500;
  background: rgba(74, 107, 92, 0.12);
}

.gnotes {
  padding-left: 20px;
  padding-right: 20px;
  background: var(--margin-bg);
  border-left: 1px solid var(--border);
}

.note-checking {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.86rem;
  font-style: italic;
  color: var(--accent);
}

.spinner {
  width: 11px;
  height: 11px;
  border: 2px solid var(--accent);
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.note-error {
  font-size: 0.84rem;
  color: var(--error);
  line-height: 1.5;
}

.note-clean {
  font-size: 0.8rem;
  color: var(--success);
  opacity: 0.6;
}

.note-content {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.edits {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.edits-label {
  font-family: var(--font-mono);
  font-size: 0.62rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-muted);
}

.edit-row {
  font-size: 0.92rem;
  line-height: 1.5;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: baseline;
}

.edit-row .from {
  text-decoration: line-through;
  text-decoration-color: var(--issue-color);
  opacity: 0.75;
}

.edit-row .arrow {
  color: var(--text-muted);
}

.edit-row .to {
  color: var(--success);
  font-weight: 500;
}

.edit-row .to.deleted {
  color: var(--issue-color);
  font-weight: 400;
  font-style: italic;
}

.edit-row .to.add {
  color: var(--success);
}

.notes-list {
  margin: 0;
  padding: 0 0 0 16px;
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.notes-list li {
  font-size: 0.84rem;
  line-height: 1.45;
  color: var(--text-muted);
}

.note-tag {
  display: inline-block;
  font-family: var(--font-mono);
  font-size: 0.6rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 1px 6px;
  margin-right: 6px;
  border-radius: 4px;
  color: var(--accent);
  background: rgba(74, 107, 92, 0.1);
  vertical-align: middle;
}

.note-tag[data-type='style'] {
  color: var(--hint-color);
  background: rgba(138, 106, 61, 0.12);
}

.note-tag[data-type='spelling'],
.note-tag[data-type='grammar'] {
  color: var(--issue-color);
  background: rgba(196, 84, 74, 0.1);
}

.hint {
  margin: 0;
  padding-left: 12px;
  border-left: 2px solid var(--hint-border);
  font-size: 0.87rem;
  line-height: 1.5;
  font-style: italic;
  color: var(--hint-color);
}

@media (max-width: 900px) {
  .review-grid {
    grid-template-columns: 3.25rem 1fr;
  }
  .ghead-notes {
    display: none;
  }
  .gnotes {
    grid-column: 1 / -1;
    border-left: none;
    border-top: 1px dashed var(--border-subtle);
    padding-left: 3.25rem;
  }
  .gnotes[data-status='clean'],
  .gnotes[data-status='pending'] {
    display: none;
  }
  .format-note {
    display: none;
  }
}
</style>
