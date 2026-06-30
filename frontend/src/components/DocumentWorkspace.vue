<script setup>
import { ref, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import {
  newParagraph,
  plainText,
  paragraphsToLines,
  extractParagraphsFromPaste,
  stripIssueMarks,
  applyIssueMarks,
} from '../utils/document.js'

const props = defineProps({
  lines: { type: Array, default: () => [''] },
  results: { type: Array, default: () => [] },
  checkingLine: { type: Number, default: null },
  checking: { type: Boolean, default: false },
})

const emit = defineEmits(['update:lines'])

const paragraphs = ref([newParagraph('')])
const paraRefs = ref([])
const noteRefs = ref([])
const rowHeights = ref([])
const scrollLeft = ref(null)
const scrollRight = ref(null)
const syncingScroll = ref(false)
const editing = ref(false)

function setParaRef(el, index) {
  if (el) paraRefs.value[index] = el
}

function setNoteRef(el, index) {
  if (el) noteRefs.value[index] = el
}

function syncLines() {
  emit('update:lines', paragraphsToLines(paragraphs.value))
}

function measureRows() {
  rowHeights.value = paragraphs.value.map((_, i) => {
    const para = paraRefs.value[i]
    const note = noteRefs.value[i]
    const content = Math.max(para?.scrollHeight || 0, note?.scrollHeight || 0, 32)
    return content + 20
  })
}

function refreshMarks() {
  if (editing.value) return
  paragraphs.value.forEach((para, i) => {
    const el = paraRefs.value[i]
    if (!el) return
    stripIssueMarks(el)
    const result = props.results[i]
    if (result?.issues?.length) applyIssueMarks(el, result.issues)
  })
  nextTick(measureRows)
}

function onParaInput(index) {
  editing.value = true
  const el = paraRefs.value[index]
  if (el) {
    stripIssueMarks(el)
    paragraphs.value[index].html = el.innerHTML
  }
  syncLines()
  measureRows()
}

function onParaBlur() {
  editing.value = false
  syncLines()
  refreshMarks()
}

function onDocumentPaste(e) {
  const html = e.clipboardData.getData('text/html')
  const text = e.clipboardData.getData('text/plain')
  if (!html && !text) return

  e.preventDefault()
  paragraphs.value = extractParagraphsFromPaste(html, text)
  editing.value = false
  syncLines()
  nextTick(() => {
    paragraphs.value.forEach((para, i) => {
      const el = paraRefs.value[i]
      if (el) el.innerHTML = para.html
    })
    refreshMarks()
    measureRows()
  })
}

function onParaKeydown(e, index) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    paragraphs.value.splice(index + 1, 0, newParagraph(''))
    syncLines()
    nextTick(() => paraRefs.value[index + 1]?.focus())
  }
}

function onManuscriptScroll() {
  if (syncingScroll.value || !scrollLeft.value || !scrollRight.value) return
  syncingScroll.value = true
  scrollRight.value.scrollTop = scrollLeft.value.scrollTop
  requestAnimationFrame(() => {
    syncingScroll.value = false
  })
}

function onNotesScroll() {
  if (syncingScroll.value || !scrollLeft.value || !scrollRight.value) return
  syncingScroll.value = true
  scrollLeft.value.scrollTop = scrollRight.value.scrollTop
  requestAnimationFrame(() => {
    syncingScroll.value = false
  })
}

function lineResult(index) {
  return props.results[index] ?? null
}

function hasNote(result) {
  return Boolean(result?.error || result?.hint || result?.issues?.length)
}

function showNote(index) {
  if (props.checkingLine === index + 1) return true
  const result = lineResult(index)
  return Boolean(result?.error || hasNote(result))
}

let resizeObserver
onMounted(() => {
  nextTick(() => {
    paragraphs.value.forEach((para, i) => {
      if (paraRefs.value[i]) paraRefs.value[i].innerHTML = para.html
    })
    measureRows()
  })
  resizeObserver = new ResizeObserver(() => measureRows())
})

onBeforeUnmount(() => resizeObserver?.disconnect())

watch(
  () => props.results,
  async () => {
    await nextTick()
    refreshMarks()
  },
  { deep: true },
)

watch(
  () => [props.checkingLine, props.checking],
  () => nextTick(measureRows),
)

watch(
  paragraphs,
  () => {
    nextTick(() => {
      paragraphs.value.forEach((_, i) => {
        const el = paraRefs.value[i]
        if (el && resizeObserver) resizeObserver.observe(el)
        const note = noteRefs.value[i]
        if (note && resizeObserver) resizeObserver.observe(note)
      })
      measureRows()
    })
  },
  { deep: true },
)
</script>

<template>
  <div class="workspace" @paste.capture="onDocumentPaste">
    <section class="manuscript">
      <div class="pane-label">Manuscript</div>
      <div ref="scrollLeft" class="pane-scroll" @scroll="onManuscriptScroll">
        <div class="rows">
          <div
            v-for="(para, index) in paragraphs"
            :key="para.id"
            class="row"
            :style="{ minHeight: (rowHeights[index] || 52) + 'px' }"
          >
            <span class="gutter" :class="{ active: checkingLine === index + 1 }">{{ index + 1 }}</span>
            <div
              :ref="(el) => setParaRef(el, index)"
              class="para"
              contenteditable="true"
              spellcheck="false"
              @input="onParaInput(index)"
              @blur="onParaBlur"
              @keydown="onParaKeydown($event, index)"
            />
          </div>
          <div v-if="paragraphs.length === 1 && !plainText(paragraphs[0].html)" class="placeholder">
            Paste from Word or LibreOffice, or start writing…
          </div>
        </div>
      </div>
    </section>

    <section class="marginalia">
      <div class="pane-label">Marginalia</div>
      <div ref="scrollRight" class="pane-scroll" @scroll="onNotesScroll">
        <div class="rows">
          <div
            v-for="(para, index) in paragraphs"
            :key="'note-' + para.id"
            class="row"
            :style="{ minHeight: (rowHeights[index] || 52) + 'px' }"
          >
            <div :ref="(el) => setNoteRef(el, index)" class="note">
              <template v-if="showNote(index)">
                <div v-if="checkingLine === index + 1" class="note-checking">
                  Reviewing paragraph {{ index + 1 }}…
                </div>
                <div v-else-if="lineResult(index)?.error" class="note-error">
                  {{ lineResult(index).error }}
                </div>
                <div v-else class="note-content">
                  <div
                    v-for="(issue, i) in lineResult(index)?.issues || []"
                    :key="i"
                    class="issue-card"
                  >
                    <div class="issue-label">{{ issue.type }}</div>
                    <div v-if="issue.original || issue.suggestion" class="issue-change">
                      <span v-if="issue.original" class="from">{{ issue.original }}</span>
                      <span v-if="issue.suggestion" class="to">→ {{ issue.suggestion }}</span>
                    </div>
                    <p v-if="issue.message" class="issue-detail">{{ issue.message }}</p>
                  </div>
                  <p v-if="lineResult(index)?.hint" class="hint">{{ lineResult(index).hint }}</p>
                </div>
              </template>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.workspace {
  flex: 1;
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(300px, 0.85fr);
  min-height: 0;
  border: 1px solid var(--border);
  border-radius: 14px;
  overflow: hidden;
  background: var(--paper);
  box-shadow: var(--shadow);
}

.manuscript,
.marginalia {
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.marginalia {
  border-left: 1px solid var(--border);
  background: var(--margin-bg);
}

.pane-label {
  padding: 10px 18px;
  font-family: var(--font-mono);
  font-size: 0.68rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--text-muted);
  border-bottom: 1px solid var(--border);
  background: rgba(255, 255, 255, 0.35);
  flex-shrink: 0;
}

.pane-scroll {
  flex: 1;
  overflow: auto;
  min-height: 0;
}

.rows {
  padding: 24px 0 48px;
}

.row {
  display: grid;
  grid-template-columns: 3.25rem minmax(0, 1fr);
  gap: 0;
  box-sizing: border-box;
  padding: 0 20px 0 0;
}

.marginalia .row {
  grid-template-columns: minmax(0, 1fr);
  padding: 0 20px 0 18px;
}

.gutter {
  padding: 2px 10px 0 8px;
  text-align: right;
  font-family: var(--font-mono);
  font-size: 0.76rem;
  line-height: 1.75;
  color: var(--gutter);
  border-right: 1px solid var(--border-subtle);
  user-select: none;
}

.gutter.active {
  color: var(--accent);
  font-weight: 600;
}

.para {
  padding: 2px 16px 2px 16px;
  outline: none;
  font-family: var(--font-serif);
  font-size: 1.125rem;
  line-height: 1.75;
  color: var(--ink);
  word-break: break-word;
}

.para :deep(b),
.para :deep(strong) {
  font-weight: 600;
}

.para :deep(i),
.para :deep(em) {
  font-style: italic;
}

.para :deep(.issue-mark) {
  text-decoration: underline wavy;
  text-decoration-color: var(--issue-color);
  text-underline-offset: 3px;
  background: rgba(196, 84, 74, 0.08);
  border-radius: 2px;
}

.note {
  padding: 2px 0 10px;
}

.note-checking {
  font-size: 0.88rem;
  font-style: italic;
  color: var(--accent);
  line-height: 1.75;
}

.note-error {
  font-size: 0.88rem;
  color: var(--error);
}

.note-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.issue-card {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.issue-label {
  font-family: var(--font-mono);
  font-size: 0.65rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--issue-color);
}

.issue-change {
  font-size: 0.9rem;
  line-height: 1.5;
}

.issue-change .from {
  text-decoration: line-through;
  opacity: 0.7;
}

.issue-change .to {
  color: var(--success);
  font-weight: 500;
}

.issue-detail {
  margin: 0;
  font-size: 0.84rem;
  line-height: 1.45;
  color: var(--text-muted);
}

.hint {
  margin: 0;
  padding-left: 12px;
  border-left: 2px solid var(--hint-border);
  font-size: 0.88rem;
  line-height: 1.5;
  font-style: italic;
  color: var(--hint-color);
}

.placeholder {
  padding: 0 3.25rem 0 0;
  margin-left: 3.25rem;
  color: var(--text-muted);
  font-family: var(--font-serif);
  font-size: 1.125rem;
  pointer-events: none;
}

@media (max-width: 900px) {
  .workspace {
    grid-template-columns: 1fr;
    grid-template-rows: 1fr 1fr;
  }

  .marginalia {
    border-left: none;
    border-top: 1px solid var(--border);
  }
}
</style>
