<script setup>
import { ref, watch, onMounted, nextTick } from 'vue'
import { applyIssueMarks } from '../utils/document.js'

const props = defineProps({
  paragraphs: { type: Array, default: () => [] },
  results: { type: Array, default: () => [] },
  checkingIndex: { type: Number, default: -1 },
})

const textRefs = ref([])

function setTextRef(el, index) {
  if (el) textRefs.value[index] = el
}

function renderText(index) {
  const el = textRefs.value[index]
  const para = props.paragraphs[index]
  if (!el || !para) return
  el.innerHTML = para.html
  const result = props.results[index]
  if (result?.issues?.length) applyIssueMarks(el, result.issues)
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
  () => nextTick(renderAll),
  { deep: true },
)

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
</script>

<template>
  <div class="review-wrap">
    <div class="review-grid">
      <div class="ghead ghead-num" />
      <div class="ghead">Manuscript</div>
      <div class="ghead ghead-notes">Marginalia</div>

      <template v-for="(para, index) in paragraphs" :key="para.id">
        <div class="gnum" :class="{ active: checkingIndex === index }">
          <span>{{ index + 1 }}</span>
        </div>

        <div class="gtext" :ref="(el) => setTextRef(el, index)" />

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
  grid-template-columns: 3rem minmax(0, 1.18fr) minmax(300px, 0.82fr);
  align-content: start;
}

/* Header row — sticky */
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

.ghead-notes {
  background: var(--margin-bg);
  border-left: 1px solid var(--border);
}

/* Per-paragraph cells */
.gnum,
.gtext,
.gnotes {
  border-bottom: 1px solid var(--border-subtle);
  padding-top: 18px;
  padding-bottom: 18px;
}

.gnum {
  display: flex;
  justify-content: flex-end;
  padding-left: 6px;
  padding-right: 12px;
  font-family: var(--font-mono);
  font-size: 0.74rem;
  line-height: 1.85;
  color: var(--gutter);
  user-select: none;
  background: rgba(0, 0, 0, 0.015);
  border-right: 1px solid var(--border-subtle);
}

.gnum.active {
  color: var(--accent);
  font-weight: 600;
}

.gtext {
  padding-left: 20px;
  padding-right: 28px;
  font-family: var(--font-serif);
  font-size: 1.12rem;
  line-height: 1.85;
  color: var(--ink);
  word-break: break-word;
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
    grid-template-columns: 2.4rem 1fr;
  }
  .ghead-notes {
    display: none;
  }
  .gnotes {
    grid-column: 1 / -1;
    border-left: none;
    border-top: 1px dashed var(--border-subtle);
    padding-left: 2.4rem;
  }
  .gnotes[data-status='clean'],
  .gnotes[data-status='pending'] {
    display: none;
  }
}
</style>
