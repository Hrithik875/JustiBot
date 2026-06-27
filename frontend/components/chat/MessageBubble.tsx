'use client'

import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { Message } from '@/types'
import { SourcesPanel } from './SourcesPanel'

interface MessageBubbleProps {
  message: Message
  isLatest: boolean
}

function TypingIndicator() {
  return (
    <div className="flex gap-1 items-center px-1 py-2">
      <span className="w-2 h-2 rounded-full bg-muted opacity-60 animate-bounce [animation-delay:0ms]" />
      <span className="w-2 h-2 rounded-full bg-muted opacity-60 animate-bounce [animation-delay:150ms]" />
      <span className="w-2 h-2 rounded-full bg-muted opacity-60 animate-bounce [animation-delay:300ms]" />
    </div>
  )
}

export { TypingIndicator }

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

  // Assistant message
  return (
    <div className="flex justify-start mb-6">
      <div className="max-w-[85%] w-full">
        <div className="markdown-content text-sm leading-relaxed">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              a: ({ href, children }: any) => (
                <a
                  href={href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-accent underline underline-offset-2"
                >
                  {children}
                </a>
              ),
              code: ({ children, className }: any) => {
                const isInline = !className
                if (isInline) {
                  return (
                    <code className="bg-surface border border-border px-1.5 py-0.5 rounded text-accent font-semibold text-xs">
                      {children}
                    </code>
                  )
                }
                return (
                  <code className="block">{children}</code>
                )
              },
            }}
          >
            {message.content}
          </ReactMarkdown>
        </div>

        <SourcesPanel sources={message.sources} />

        {/* Metadata row */}
        <div className="flex items-center gap-2 mt-2 flex-wrap">
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
