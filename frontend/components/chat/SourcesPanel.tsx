'use client'

import { useState } from 'react'
import { ChevronDown, ChevronUp, ExternalLink } from 'lucide-react'
import type { Source } from '@/types'

const CATEGORY_STYLES: Record<string, string> = {
  criminal: 'border-red-500/40 text-red-400',
  civil: 'border-blue-500/40 text-blue-400',
  cyber: 'border-purple-500/40 text-purple-400',
  consumer: 'border-green-500/40 text-green-400',
  constitutional: 'border-amber-500/40 text-amber-400',
  procedural: 'border-border text-muted',
}

interface SourcesPanelProps {
  sources: Source[]
}

export function SourcesPanel({ sources }: SourcesPanelProps) {
  const [open, setOpen] = useState(false)

  if (!sources || sources.length === 0) return null

  return (
    <div className="mt-3">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1.5 text-xs text-muted underline underline-offset-2 hover:text-text transition-colors"
      >
        {open ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
        View Sources ({sources.length})
      </button>

      {open && (
        <div className="mt-2 space-y-2">
          {sources.map((src, i) => (
            <div
              key={i}
              className="p-3 rounded-lg border border-border bg-bg text-sm"
            >
              <div className="flex items-start justify-between gap-2">
                <span className="font-medium text-xs">{src.name}</span>
                <span
                  className={`shrink-0 text-xs px-1.5 py-0.5 rounded border ${
                    CATEGORY_STYLES[src.category] ?? CATEGORY_STYLES.procedural
                  }`}
                >
                  {src.category}
                </span>
              </div>
              <p className="text-muted text-xs mt-1">
                Relevance: {src.relevanceScore?.toFixed(3) ?? 'N/A'}
              </p>
              {src.url && (
                <a
                  href={src.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-accent text-xs mt-1 hover:underline"
                >
                  Open source <ExternalLink size={10} />
                </a>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
