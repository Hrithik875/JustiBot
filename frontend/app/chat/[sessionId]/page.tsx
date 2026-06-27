'use client'

import { useEffect, useRef, useState } from 'react'
import { Scale } from 'lucide-react'
import { useChat } from '@/lib/hooks/useChat'
import { useSessions } from '@/lib/hooks/useSessions'
import { MessageBubble, TypingIndicator } from '@/components/chat/MessageBubble'
import { InputBar } from '@/components/chat/InputBar'
import { SessionTitle } from '@/components/chat/SessionTitle'

const SUGGESTIONS = [
  "What should I do if I'm scammed online?",
  "How do I file an RTI application?",
  "What are my rights if I'm arrested?"
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

  // Find the initial title if it exists
  const currentSession = sessions.find((s) => s.sessionId === sessionId)
  const initialTitle = currentSession?.title || (isNew ? 'New Chat' : 'Untitled')

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, isLoading])

  const handleSend = (query: string) => {
    sendMessage(query, categoryFilter === 'all' ? null : categoryFilter)
  }

  const showEmptyState = isNew && messages.length === 0

  return (
    <div className="flex flex-col h-full bg-bg">
      {/* ── Top Bar ─────────────────────────────────────────────── */}
      <div className="h-14 border-b border-border bg-surface/50 backdrop-blur-sm shrink-0 flex items-center justify-between px-4 sm:px-6 z-10 hidden md:flex">
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

      {/* For mobile, we just put the filter and title under the header since header is in layout */}
      <div className="md:hidden p-2 flex items-center justify-between border-b border-border bg-surface">
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

      {/* ── Chat Area ───────────────────────────────────────────── */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 sm:px-6 py-6 scroll-smooth">
        {showEmptyState ? (
          <div className="h-full flex flex-col items-center justify-center max-w-2xl mx-auto">
            <div className="w-16 h-16 rounded-2xl bg-surface border border-border flex items-center justify-center mb-6 shadow-sm">
              <Scale size={32} className="text-accent" />
            </div>
            <h2 className="text-2xl font-bold mb-8">How can I help you today?</h2>
            
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 w-full">
              {SUGGESTIONS.map((sug, i) => (
                <button
                  key={i}
                  onClick={() => handleSend(sug)}
                  className="p-4 rounded-xl border border-border bg-surface text-sm text-left hover:border-accent hover:text-accent transition-colors shadow-sm"
                >
                  {sug}
                </button>
              ))}
            </div>
          </div>
        ) : (
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
                <div className="max-w-[85%] px-2">
                  <TypingIndicator />
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

      {/* ── Input Area ──────────────────────────────────────────── */}
      <div className="shrink-0 p-4 bg-bg border-t border-transparent bg-gradient-to-t from-bg via-bg to-transparent">
        <InputBar onSend={handleSend} disabled={isLoading} isLoading={isLoading} />
        <p className="text-center text-[10px] text-muted mt-2">
          JustiBot can make mistakes. Verify important information.
        </p>
      </div>
    </div>
  )
}
