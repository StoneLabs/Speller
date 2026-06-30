<script setup>
import { ref, onMounted, watch } from 'vue'
import { sanitizePastedHtml, plainTextToHtml } from '../utils/document.js'

const props = defineProps({
  html: { type: String, default: '' },
})

const emit = defineEmits(['update:html'])

const editorRef = ref(null)

function emitChange() {
  if (editorRef.value) emit('update:html', editorRef.value.innerHTML)
}

function onPaste(e) {
  e.preventDefault()
  const html = e.clipboardData.getData('text/html')
  const text = e.clipboardData.getData('text/plain')

  const toInsert = html ? sanitizePastedHtml(html) : plainTextToHtml(text)
  insertHtmlAtCursor(toInsert)
  emitChange()
}

function insertHtmlAtCursor(htmlString) {
  const sel = window.getSelection()
  if (!sel || !sel.rangeCount) {
    editorRef.value.innerHTML += htmlString
    return
  }
  const range = sel.getRangeAt(0)
  range.deleteContents()

  const temp = document.createElement('div')
  temp.innerHTML = htmlString
  const frag = document.createDocumentFragment()
  let lastNode = null
  while (temp.firstChild) {
    lastNode = frag.appendChild(temp.firstChild)
  }
  range.insertNode(frag)

  if (lastNode) {
    const after = range.cloneRange()
    after.setStartAfter(lastNode)
    after.collapse(true)
    sel.removeAllRanges()
    sel.addRange(after)
  }
}

onMounted(() => {
  if (editorRef.value && props.html) {
    editorRef.value.innerHTML = props.html
  }
})

// Reseed only when the external value diverges from the live DOM
// (e.g. a programmatic reset), never on every keystroke.
watch(
  () => props.html,
  (value) => {
    if (editorRef.value && value !== editorRef.value.innerHTML) {
      editorRef.value.innerHTML = value || ''
    }
  },
)

function focus() {
  editorRef.value?.focus()
}

defineExpose({ focus })
</script>

<template>
  <div class="editor-wrap">
    <div class="editor-inner">
      <div
        ref="editorRef"
        class="editor"
        contenteditable="true"
        spellcheck="false"
        role="textbox"
        aria-multiline="true"
        data-placeholder="Paste your manuscript from Word or LibreOffice — or just start writing. Bold and italics are kept. When you're ready, hit Review Manuscript."
        @input="emitChange"
        @paste="onPaste"
      />
    </div>
  </div>
</template>

<style scoped>
.editor-wrap {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  border: 1px solid var(--border);
  border-radius: 14px;
  overflow: hidden;
  background: var(--paper);
  box-shadow: var(--shadow);
}

.editor-inner {
  flex: 1;
  overflow: auto;
  min-height: 0;
  display: flex;
  justify-content: center;
}

.editor {
  width: 100%;
  max-width: 760px;
  padding: 48px 40px 96px;
  outline: none;
  font-family: var(--font-serif);
  font-size: 1.18rem;
  line-height: 1.85;
  color: var(--ink);
  word-break: break-word;
}

.editor:empty::before {
  content: attr(data-placeholder);
  color: var(--text-muted);
  pointer-events: none;
  white-space: pre-wrap;
}

.editor :deep(p) {
  margin: 0 0 1.1em;
}

.editor :deep(p:last-child) {
  margin-bottom: 0;
}

.editor :deep(b),
.editor :deep(strong) {
  font-weight: 600;
}

.editor :deep(i),
.editor :deep(em) {
  font-style: italic;
}

.editor :deep(u) {
  text-decoration: underline;
}
</style>
