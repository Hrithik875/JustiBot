'use client'

import type { Message } from '@/types'
import { SourcesPanel } from './SourcesPanel'

interface MessageBubbleProps {
  message: Message
  isLatest: boolean
}

/**
 * Parses basic markdown syntax into React elements without external deps:
 * - **bold** → <strong>
 * - `code` → <code>
 * - ## headings
 * - - bullet lists
 * - numbered lists
 * - [text](url) links
 * - bare URLs
 */
function renderMarkdown(text: string): React.ReactNode[] {
  const lines = text.split('\n')
  const result: React.ReactNode[] = []
  let i = 0

  while (i < lines.length) {
    const line = lines[i]

    // Heading
    const h2 = line.match(/^## (.+)/)
    const h3 = line.match(/^### (.+)/)
    const h1 = line.match(/^# (.+)/)
    if (h1) {
      result.push(<h1 key={i} className="text-base font-bold mt-3 mb-1 border-b border-border pb-1">{h1[1]}</h1>)
      i++; continue
    }
    if (h2) {
      result.push(<h2 key={i} className="text-sm font-semibold mt-3 mb-1 border-b border-border pb-1">{h2[1]}</h2>)
      i++; continue
    }
    if (h3) {
      result.push(<h3 key={i} className="text-sm font-semibold mt-2 mb-0.5">{h3[1]}</h3>)
      i++; continue
    }

    // Bullet list
    if (line.match(/^[-*] /)) {
      const items: string[] = []
      while (i < lines.length && lines[i].match(/^[-*] /)) {
        items.push(lines[i].replace(/^[-*] /, ''))
        i++
      }
      result.push(
        <ul key={`ul-${i}`} className="list-disc pl-5 my-1 space-y-0.5">
          {items.map((item, j) => (
            <li key={j} className="leading-relaxed">{inlineMarkdown(item)}</li>
          ))}
        </ul>
      )
      continue
    }

    // Numbered list
    if (line.match(/^\d+\. /)) {
      const items: string[] = []
      while (i < lines.length && lines[i].match(/^\d+\. /)) {
        items.push(lines[i].replace(/^\d+\. /, ''))
        i++
      }
      result.push(
        <ol key={`ol-${i}`} className="list-decimal pl-5 my-1 space-y-0.5">
          {items.map((item, j) => (
            <li key={j} className="leading-relaxed">{inlineMarkdown(item)}</li>
          ))}
        </ol>
      )
      continue
    }

    // Horizontal rule
    if (line.match(/^---+$/)) {
      result.push(<hr key={i} className="border-border my-2" />)
      i++; continue
    }

    // Blank line
    if (line.trim() === '') {
      result.push(<div key={i} className="h-1" />)
      i++; continue
    }

    // Regular paragraph
    result.push(
      <p key={i} className="leading-relaxed my-0.5">
        {inlineMarkdown(line)}
      </p>
    )
    i++
  }

  return result
}

/**
 * Processes inline markdown: **bold**, `code`, [link](url), bare URLs
 */
function inlineMarkdown(text: string): React.ReactNode[] {
  const parts: React.ReactNode[] = []
  // Pattern: **bold**, `code`, [text](url), https://...
  const pattern = /(\*\*(.+?)\*\*|`([^`]+)`|\[([^\]]+)\]\(([^)]+)\)|(https?:\/\/[^\s]+))/g
  let last = 0
  let match: RegExpExecArray | null

  while ((match = pattern.exec(text)) !== null) {
    if (match.index > last) {
      parts.push(text.slice(last, match.index))
    }

    if (match[2] !== undefined) {
      // **bold**
      parts.push(<strong key={match.index} className="font-semibold">{match[2]}</strong>)
    } else if (match[3] !== undefined) {
      // `code`
      parts.push(
        <code key={match.index} className="bg-surface border border-border px-1.5 py-0.5 rounded text-accent font-mono text-xs font-semibold">
          {match[3]}
        </code>
      )
    } else if (match[4] !== undefined) {
      // [text](url)
      parts.push(
        <a key={match.index} href={match[5]} target="_blank" rel="noopener noreferrer" className="text-accent underline underline-offset-2">
          {match[4]}
        </a>
      )
    } else if (match[6] !== undefined) {
      // bare URL
      parts.push(
        <a key={match.index} href={match[6]} target="_blank" rel="noopener noreferrer" className="text-accent underline underline-offset-2 break-all">
          {match[6]}
        </a>
      )
    }

    last = match.index + match[0].length
  }

  if (last < text.length) {
    parts.push(text.slice(last))
  }

  return parts
}

export function MessageBubble({ message }: MessageBubbleProps) {
  if (message.role === 'user') {
    return (
      <div className="flex justify-end mb-4">
        <div className="max-w-[78%] px-4 py-3 rounded-xl bg-surface border border-border text-sm leading-relaxed">
          {message.content}
        </div>
      </div>
    )
  }

  // Assistant
  return (
    <div className="flex justify-start mb-6">
      <div className="max-w-[85%] w-full">
        {/* Bot avatar dot */}
        <div className="flex items-center gap-2 mb-2">
          <div className="w-6 h-6 rounded-full bg-accent flex items-center justify-center text-white text-xs font-bold shrink-0">J</div>
          <span className="text-xs text-muted font-medium">JustiBot</span>
        </div>

        <div className="text-sm text-text pl-8">
          {renderMarkdown(message.content)}
        </div>

        <div className="pl-8 mt-1">
          <SourcesPanel sources={message.sources ?? []} />
        </div>

        {/* Metadata row */}
        <div className="flex items-center gap-2 mt-2 pl-8 flex-wrap">
          <span className="text-xs text-muted">llama-3.3-70b-versatile</span>
          {message.semanticCache && (
            <span className="text-xs px-1.5 py-0.5 rounded border border-border text-muted">
              ⚡ Semantic cache
            </span>
          )}
          {message.cached && !message.semanticCache && (
            <span className="text-xs px-1.5 py-0.5 rounded border border-border text-muted">
              ⚡ Cached
            </span>
          )}
        </div>
      </div>
    </div>
  )
}
