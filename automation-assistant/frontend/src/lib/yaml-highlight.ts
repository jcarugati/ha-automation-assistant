/**
 * Lightweight YAML syntax highlighting using regex
 * Returns HTML string with span elements for different token types
 */

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

export function highlightYaml(yaml: string): string {
  const lines = yaml.split('\n')

  return lines.map(line => {
    // Preserve empty lines
    if (line.trim() === '') {
      return ''
    }

    // Comment lines
    if (line.trim().startsWith('#')) {
      return `<span class="yaml-comment">${escapeHtml(line)}</span>`
    }

    // Check for key-value pairs
    const keyValueMatch = line.match(/^(\s*)(- )?([a-zA-Z_][a-zA-Z0-9_]*):(.*)$/)
    if (keyValueMatch) {
      const [, indent, listMarker, key, rest] = keyValueMatch
      let result = escapeHtml(indent ?? '')

      // List marker
      if (listMarker) {
        result += `<span class="yaml-punctuation">${escapeHtml(listMarker)}</span>`
      }

      // Key
      result += `<span class="yaml-key">${escapeHtml(key ?? "")}</span><span class="yaml-punctuation">:</span>`

      // Value
      if (rest && rest.trim()) {
        result += highlightValue(rest ?? "")
      }

      return result
    }

    // List items without keys (e.g., "  - value")
    const listItemMatch = line.match(/^(\s*)(- )(.+)$/)
    if (listItemMatch) {
      const [, indent, marker, value] = listItemMatch
      return `${escapeHtml(indent ?? '')}<span class="yaml-punctuation">${escapeHtml(marker ?? '')}</span>${highlightValue(value ?? '')}`
    }

    // Just a list marker (e.g., "  -")
    const emptyListMatch = line.match(/^(\s*)(-)(\s*)$/)
    if (emptyListMatch) {
      const [, indent, marker, trailing] = emptyListMatch
      return `${escapeHtml(indent ?? '')}<span class="yaml-punctuation">${escapeHtml(marker ?? '')}</span>${escapeHtml(trailing ?? '')}`
    }

    // Default: return escaped line
    return escapeHtml(line)
  }).join('\n')
}

function highlightValue(value: string): string {
  const trimmed = value.trim()
  const leadingSpace = value.substring(0, value.length - value.trimStart().length)

  // Empty value
  if (!trimmed) {
    return escapeHtml(value)
  }

  // Inline comment
  if (trimmed.startsWith('#')) {
    return `${escapeHtml(leadingSpace)}<span class="yaml-comment">${escapeHtml(trimmed)}</span>`
  }

  // Quoted strings (single or double)
  if ((trimmed.startsWith("'") && trimmed.endsWith("'")) ||
      (trimmed.startsWith('"') && trimmed.endsWith('"'))) {
    return `${escapeHtml(leadingSpace)}<span class="yaml-string">${escapeHtml(trimmed)}</span>`
  }

  // Empty array []
  if (trimmed === '[]') {
    return `${escapeHtml(leadingSpace)}<span class="yaml-punctuation">[]</span>`
  }

  // Empty object {}
  if (trimmed === '{}') {
    return `${escapeHtml(leadingSpace)}<span class="yaml-punctuation">{}</span>`
  }

  // Booleans
  if (['true', 'false', 'yes', 'no', 'on', 'off'].includes(trimmed.toLowerCase())) {
    return `${escapeHtml(leadingSpace)}<span class="yaml-boolean">${escapeHtml(trimmed)}</span>`
  }

  // Null
  if (['null', '~'].includes(trimmed.toLowerCase())) {
    return `${escapeHtml(leadingSpace)}<span class="yaml-null">${escapeHtml(trimmed)}</span>`
  }

  // Numbers (including negative and decimals)
  if (/^-?\d+\.?\d*$/.test(trimmed)) {
    return `${escapeHtml(leadingSpace)}<span class="yaml-number">${escapeHtml(trimmed)}</span>`
  }

  // Entity IDs and service calls (contains dots, common in Home Assistant)
  if (/^[a-z_]+\.[a-z0-9_]+$/i.test(trimmed)) {
    return `${escapeHtml(leadingSpace)}<span class="yaml-entity">${escapeHtml(trimmed)}</span>`
  }

  // Default: plain value
  return `${escapeHtml(leadingSpace)}<span class="yaml-value">${escapeHtml(trimmed)}</span>`
}
