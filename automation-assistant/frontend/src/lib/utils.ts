import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function escapeHtml(str: string | null | undefined): string {
  if (!str) return ''
  const htmlEscapes: Record<string, string> = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  }
  return str.replace(/[&<>"']/g, (c) => htmlEscapes[c] ?? c)
}

export function formatMarkdown(text: string | null | undefined): string {
  if (!text) return ''
  const escaped = escapeHtml(text)
  const codeBlocks: string[] = []
  const withPlaceholders = escaped.replace(/```([\s\S]*?)```/g, (_match, code) => {
    const index = codeBlocks.length
    const cleaned = String(code).replace(/^\n+|\n+$/g, '')
    codeBlocks.push(`<pre><code>${cleaned}</code></pre>`)
    return `__CODE_BLOCK_${index}__`
  })

  const lines = withPlaceholders.split(/\r?\n/)
  const htmlParts: string[] = []
  let listType: 'ul' | 'ol' | null = null

  const closeList = () => {
    if (listType) {
      htmlParts.push(`</${listType}>`)
      listType = null
    }
  }

  const formatInline = (input: string) => {
    return input
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
  }

  for (const rawLine of lines) {
    const line = rawLine.trim()
    if (!line) {
      closeList()
      continue
    }

    const codeMatch = line.match(/^__CODE_BLOCK_(\d+)__$/)
    if (codeMatch) {
      closeList()
      htmlParts.push(line)
      continue
    }

    const headingMatch = line.match(/^(#{1,6})\s+(.*)$/)
    if (headingMatch) {
      closeList()
      const level = headingMatch[1]?.length ?? 1
      const headingText = headingMatch[2] ?? ''
      htmlParts.push(`<h${level}>${formatInline(headingText)}</h${level}>`)
      continue
    }

    if (/^---+$/.test(line)) {
      closeList()
      htmlParts.push('<hr />')
      continue
    }

    const orderedMatch = line.match(/^\d+\.\s+(.*)$/)
    if (orderedMatch) {
      if (listType !== 'ol') {
        closeList()
        htmlParts.push('<ol>')
        listType = 'ol'
      }
      htmlParts.push(`<li>${formatInline(orderedMatch[1] ?? '')}</li>`)
      continue
    }

    const unorderedMatch = line.match(/^[-*]\s+(.*)$/)
    if (unorderedMatch) {
      if (listType !== 'ul') {
        closeList()
        htmlParts.push('<ul>')
        listType = 'ul'
      }
      htmlParts.push(`<li>${formatInline(unorderedMatch[1] ?? '')}</li>`)
      continue
    }

    closeList()
    htmlParts.push(`<p>${formatInline(rawLine)}</p>`)
  }

  closeList()

  const html = htmlParts.join('\n')
  return html.replace(/__CODE_BLOCK_(\d+)__/g, (_match, index) => {
    const blockIndex = Number(index)
    return codeBlocks[blockIndex] ?? ''
  })
}

export function formatDuration(durationMs: number): string {
  if (durationMs < 1000) {
    return `${Math.round(durationMs)}ms`
  }
  if (durationMs < 60000) {
    return `${(durationMs / 1000).toFixed(1)}s`
  }
  const minutes = Math.floor(durationMs / 60000)
  const seconds = Math.round((durationMs % 60000) / 1000)
  return `${minutes}m ${seconds}s`
}

export function truncateText(text: string | null | undefined, maxLength: number): string {
  if (!text) return ''
  if (text.length <= maxLength) return text
  return `${text.slice(0, maxLength - 3)}...`
}

export async function copyToClipboard(text: string): Promise<void> {
  if (navigator.clipboard && window.isSecureContext) {
    await navigator.clipboard.writeText(text)
    return
  }
  // Fallback for non-secure contexts
  const textarea = document.createElement('textarea')
  textarea.value = text
  textarea.setAttribute('readonly', '')
  textarea.style.position = 'fixed'
  textarea.style.top = '-1000px'
  textarea.style.left = '-1000px'
  document.body.appendChild(textarea)
  textarea.focus()
  textarea.select()
  let copied = false
  try {
    copied = document.execCommand('copy')
  } catch {
    copied = false
  }
  document.body.removeChild(textarea)
  if (!copied) {
    throw new Error('Clipboard copy failed')
  }
}
