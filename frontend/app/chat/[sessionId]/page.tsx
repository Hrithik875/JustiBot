'use client'

import { useEffect, useRef, useState } from 'react'
import { Scale } from 'lucide-react'
import { useChat } from '@/lib/hooks/useChat'
import { useSessions } from '@/lib/hooks/useSessions'
import { MessageBubble } from '@/components/chat/MessageBubble'
import { InputBar } from '@/components/chat/InputBar'
import { SessionTitle } from '@/components/chat/SessionTitle'
import { Spinner } from '@/components/ui/Loader'

const SUGGESTIONS = [
  "What should I do if I'm scammed online?",
  "How do I file an RTI application?",
  "What are my rights if I'm arrested?",
]

export default function ChatSessionPage({
  params,
}: {
  params: { sessionId: string }
}) {
  const { sessionId } = params
  const { messages, isLoading, error, sendMessage } = useChat(sessionId)
  const { sessions } = useSessions()
  const scrollRef = useRef<HTMLDivElement>(null)
  const isNew = sessionId === 'new'

  const [categoryFilter, setCategoryFilter] = useState<string>('all')
  const [historyLoading, setHistoryLoading] = useState(!isNew)

  // Find the initial title if it exists
  const currentSession = sessions.find((s) => s.sessionId === sessionId)
  const initialTitle = currentSession?.title || (isNew ? 'New Chat' : 'Untitled')

  // Mark history as loaded once messages are fetched for existing sessions
  useEffect(() => {
    if (!isNew) {
      // Short timeout to let message loading settle
      const t = setTimeout(() => setHistoryLoading(false), 600)
      return () => clearTimeout(t)
    } else {
      setHistoryLoading(false)
    }
  }, [isNew, sessionId])

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, isLoading])

  const handleSend = (query: string) => {
    sendMessage(query, categoryFilter === 'all' ? null : categoryFilter)
  }

  const handleSuggestion = (sug: string) => {
    handleSend(sug)
  }

  const showEmptyState = isNew && messages.length === 0 && !isLoading

  if (historyLoading) {
    return (
      <div className="flex-1 flex items-center justify-center bg-bg h-full">
        <div className="flex flex-col items-center gap-3">
          <Spinner size={28} />
          <p className="text-muted text-sm">Loading conversation…</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full bg-bg">
      {/* ── Top Bar (desktop) ─────────────────────────────────────── */}
      <div className="h-14 border-b border-border bg-surface/50 shrink-0 items-center justify-between px-4 sm:px-6 z-10 hidden md:flex">
        <SessionTitle
          sessionId={sessionId}
          initialTitle={initialTitle}
          isNewSession={isNew}
        />

        <select
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
          className="text-xs bg-bg border border-border rounded-lg px-2 py-1.5 outline-none text-text"
        >
          <option value="all">All Categories</option>
          <option value="criminal">Criminal</option>
          <option value="civil">Civil</option>
          <option value="constitutional">Constitutional</option>
          <option value="cyber">Cyber</option>
          <option value="consumer">Consumer</option>
          <option value="procedural">Procedural</option>
        </select>
      </div>

      {/* ── Top Bar (mobile) ──────────────────────────────────────── */}
      <div className="md:hidden p-2 flex items-center justify-between border-b border-border bg-surface shrink-0">
        <SessionTitle
          sessionId={sessionId}
          initialTitle={initialTitle}
          isNewSession={isNew}
        />
        <select
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
          className="text-xs bg-bg border border-border rounded-lg px-2 py-1 outline-none text-text max-w-[120px]"
        >
          <option value="all">All Categories</option>
          <option value="criminal">Criminal</option>
          <option value="civil">Civil</option>
          <option value="constitutional">Constitutional</option>
          <option value="cyber">Cyber</option>
          <option value="consumer">Consumer</option>
          <option value="procedural">Procedural</option>
        </select>
      </div>

      {/* ── Chat Area ─────────────────────────────────────────────── */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-4 sm:px-6 py-6 scroll-smooth"
      >
        {showEmptyState ? (
          /* Empty state with suggestions */
          <div className="h-full flex flex-col items-center justify-center max-w-2xl mx-auto">
            <div className="w-16 h-16 rounded-2xl bg-surface border border-border flex items-center justify-center mb-6">
              <Scale size={32} className="text-accent" />
            </div>
            <h2 className="text-2xl font-bold mb-2">How can I help you today?</h2>
            <p className="text-muted text-sm mb-8">
              Ask anything about Indian law — rights, procedures, helplines.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 w-full">
              {SUGGESTIONS.map((sug, i) => (
                <button
                  key={i}
                  onClick={() => handleSuggestion(sug)}
                  disabled={isLoading}
                  className="p-4 rounded-xl border border-border bg-surface text-sm text-left hover:border-accent hover:text-accent transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {sug}
                </button>
              ))}
            </div>
          </div>
        ) : (
          /* Message list */
          <div className="max-w-4xl mx-auto flex flex-col pb-4">
            {messages.map((msg, i) => (
              <MessageBubble
                key={msg.id}
                message={msg}
                isLatest={i === messages.length - 1}
              />
            ))}

            {isLoading && (
              <div className="flex justify-start mb-6">
                <div className="flex items-center gap-2 px-2">
                  <Spinner size={16} />
                  <span className="text-muted text-sm">JustiBot is thinking…</span>
                </div>
              </div>
            )}

            {error && (
              <div className="p-3 my-4 bg-danger/10 border border-danger/20 rounded-lg text-danger text-sm text-center">
                {error}
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── Input Area ────────────────────────────────────────────── */}
      <div className="shrink-0 p-4 border-t border-border bg-bg">
        <InputBar
          onSend={handleSend}
          disabled={isLoading}
          isLoading={isLoading}
        />
        <p className="text-center text-[10px] text-muted mt-2">
          JustiBot can make mistakes. Verify important information with a qualified lawyer.
        </p>
      </div>
    </div>
  )
}
