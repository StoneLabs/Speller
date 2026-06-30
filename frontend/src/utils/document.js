let nextId = 1

const INLINE_KEEP = new Set(['B', 'STRONG', 'I', 'EM', 'U', 'S', 'STRIKE', 'SUB', 'SUP'])
const BLOCK_TAGS = new Set([
  'P',
  'DIV',
  'H1',
  'H2',
  'H3',
  'H4',
  'H5',
  'H6',
  'LI',
  'BLOCKQUOTE',
  'SECTION',
  'ARTICLE',
  'PRE',
  'TR',
])

function normalizeWhitespace(text) {
  return text.replace(/\u00a0/g, ' ').replace(/\s+/g, ' ').trim()
}

function escapeHtml(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

/**
 * Clean HTML coming from a paste (Word / LibreOffice / web).
 * Keeps bold/italic/underline, drops everything else, and preserves
 * paragraph structure as simple <p> blocks so editing stays predictable.
 */
export function sanitizePastedHtml(html) {
  const doc = new DOMParser().parseFromString(html, 'text/html')
  doc.querySelectorAll('script, style, meta, link, title, head').forEach((n) => n.remove())

  const out = []

  function inlineHtml(node) {
    let result = ''
    node.childNodes.forEach((child) => {
      if (child.nodeType === Node.TEXT_NODE) {
        result += escapeHtml(child.textContent)
        return
      }
      if (child.nodeType !== Node.ELEMENT_NODE) return

      if (child.tagName === 'BR') {
        result += ' '
        return
      }

      const inner = inlineHtml(child)
      if (!inner.trim() && child.tagName !== 'BR') {
        result += inner
        return
      }

      if (INLINE_KEEP.has(child.tagName)) {
        const tag = child.tagName.toLowerCase()
        result += `<${tag}>${inner}</${tag}>`
        return
      }

      if (child.tagName === 'SPAN' || child.tagName === 'FONT') {
        const style = (child.getAttribute('style') || '').toLowerCase()
        if (/font-weight\s*:\s*(bold|[6-9]00)/.test(style)) {
          result += `<strong>${inner}</strong>`
        } else if (/font-style\s*:\s*italic/.test(style)) {
          result += `<em>${inner}</em>`
        } else if (/text-decoration[^;]*underline/.test(style)) {
          result += `<u>${inner}</u>`
        } else {
          result += inner
        }
        return
      }

      result += inner
    })
    return result
  }

  function collectBlocks(node) {
    let hasBlockChild = false
    node.childNodes.forEach((child) => {
      if (child.nodeType === Node.ELEMENT_NODE && BLOCK_TAGS.has(child.tagName)) {
        hasBlockChild = true
      }
    })

    if (hasBlockChild) {
      // Gather any loose inline content between block children too.
      let buffer = []
      const flush = () => {
        if (!buffer.length) return
        const frag = document.createElement('div')
        buffer.forEach((n) => frag.appendChild(n.cloneNode(true)))
        const h = inlineHtml(frag)
        if (normalizeWhitespace(frag.textContent)) out.push(h.replace(/\s+/g, ' ').trim())
        buffer = []
      }
      node.childNodes.forEach((child) => {
        if (child.nodeType === Node.ELEMENT_NODE && BLOCK_TAGS.has(child.tagName)) {
          flush()
          collectBlocks(child)
        } else {
          buffer.push(child)
        }
      })
      flush()
      return
    }

    const h = inlineHtml(node)
    if (normalizeWhitespace(node.textContent)) out.push(h.replace(/\s+/g, ' ').trim())
  }

  collectBlocks(doc.body)

  if (!out.length) {
    const text = normalizeWhitespace(doc.body.textContent)
    if (text) out.push(escapeHtml(text))
  }

  return out.map((h) => `<p>${h}</p>`).join('')
}

/**
 * Convert plain text into <p> blocks: blank lines separate paragraphs,
 * single line breaks become spaces (soft wraps).
 */
export function plainTextToHtml(text) {
  const normalized = text.replace(/\r\n/g, '\n').replace(/\u00a0/g, ' ')
  const paras = normalized.split(/\n{2,}/)
  const blocks = paras
    .map((p) => normalizeWhitespace(p.replace(/\n/g, ' ')))
    .filter(Boolean)
    .map((p) => `<p>${escapeHtml(p)}</p>`)
  return blocks.join('') || '<p></p>'
}

/**
 * Read an editor's HTML string and split it into logical paragraphs,
 * preserving inline formatting (bold/italic) per paragraph.
 */
export function extractParagraphs(html) {
  const root = document.createElement('div')
  root.innerHTML = html || ''

  const paragraphs = []
  let current = document.createElement('div')

  function flush() {
    collapseBreaks(current)
    const text = normalizeWhitespace(current.textContent || '')
    if (text) {
      const cleanHtml = current.innerHTML.replace(/\s+/g, ' ').trim()
      paragraphs.push({ id: nextId++, html: cleanHtml, text })
    }
    current = document.createElement('div')
  }

  function walk(node) {
    node.childNodes.forEach((child) => {
      if (child.nodeType === Node.ELEMENT_NODE && BLOCK_TAGS.has(child.tagName)) {
        flush()
        walk(child)
        flush()
      } else {
        current.appendChild(child.cloneNode(true))
      }
    })
  }

  walk(root)
  flush()

  paragraphs.forEach((p) => {
    p.markdown = htmlToMarkdown(p.html)
  })

  return paragraphs
}

function collapseBreaks(el) {
  el.querySelectorAll('br').forEach((br) => br.replaceWith(document.createTextNode(' ')))
}

/**
 * Encode inline formatting as Markdown so the model is aware of bold/italic/underline.
 * The backend strips these markers before diffing, so editor offsets stay aligned.
 */
export function htmlToMarkdown(html) {
  const root = document.createElement('div')
  root.innerHTML = html || ''

  function walk(node) {
    let out = ''
    node.childNodes.forEach((child) => {
      if (child.nodeType === Node.TEXT_NODE) {
        out += child.textContent
        return
      }
      if (child.nodeType !== Node.ELEMENT_NODE) return

      const inner = walk(child)
      if (!inner.trim()) {
        out += inner
        return
      }
      const tag = child.tagName
      if (tag === 'STRONG' || tag === 'B') out += `**${inner}**`
      else if (tag === 'EM' || tag === 'I') out += `*${inner}*`
      else if (tag === 'U') out += `__${inner}__`
      else out += inner
    })
    return out
  }

  return walk(root).replace(/\s+/g, ' ').trim()
}

/** Apply diff-based issue underlines to a static (read-only) DOM node. */
export function applyIssueMarks(node, issues) {
  if (!issues?.length) return

  const sorted = [...issues].sort((a, b) => b.start - a.start)

  const textNodes = []
  const walker = document.createTreeWalker(node, NodeFilter.SHOW_TEXT)
  let n
  while ((n = walker.nextNode())) textNodes.push(n)

  const ranges = []
  let pos = 0
  for (const tn of textNodes) {
    const len = tn.textContent.length
    ranges.push({ node: tn, start: pos, end: pos + len })
    pos += len
  }

  function locate(offset) {
    for (const r of ranges) {
      if (offset >= r.start && offset <= r.end) {
        return { node: r.node, offset: offset - r.start }
      }
    }
    return null
  }

  for (const issue of sorted) {
    const tip = [issue.message, issue.suggestion && `→ ${issue.suggestion}`].filter(Boolean).join(' ')

    // Pure insertion: collapsed range — show suggested text at the gap.
    if (issue.end === issue.start) {
      if (!issue.suggestion) continue
      const loc = locate(issue.start)
      if (!loc) continue

      const mark = document.createElement('span')
      mark.className = 'issue-mark issue-insert'
      mark.dataset.type = issue.type || 'grammar'
      if (tip) mark.title = tip
      mark.textContent = `+${issue.suggestion}`

      const range = document.createRange()
      range.setStart(loc.node, loc.offset)
      range.collapse(true)
      range.insertNode(mark)
      continue
    }

    let startNode = null
    let startOffset = 0
    let endNode = null
    let endOffset = 0

    for (const r of ranges) {
      if (!startNode && issue.start >= r.start && issue.start <= r.end) {
        startNode = r.node
        startOffset = issue.start - r.start
      }
      if (!endNode && issue.end >= r.start && issue.end <= r.end) {
        endNode = r.node
        endOffset = issue.end - r.start
      }
    }
    if (!startNode || !endNode) continue

    const range = document.createRange()
    range.setStart(startNode, startOffset)
    range.setEnd(endNode, endOffset)

    const mark = document.createElement('span')
    mark.className = 'issue-mark'
    mark.dataset.type = issue.type || 'grammar'
    if (tip) mark.title = tip

    try {
      range.surroundContents(mark)
    } catch {
      const contents = range.extractContents()
      mark.appendChild(contents)
      range.insertNode(mark)
    }
  }
}
