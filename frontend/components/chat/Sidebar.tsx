'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useParams, useRouter } from 'next/navigation'
import { Scale, Plus, Search, Trash2, LogOut, MessageSquare } from 'lucide-react'
import { ThemeToggle } from '@/components/ui/ThemeToggle'
import { useAuth } from '@/lib/hooks/useAuth'
import { useSessions } from '@/lib/hooks/useSessions'

export function Sidebar() {
  const { user, signOut } = useAuth()
  const { sessions, removeSession } = useSessions()
  const params = useParams()
  const router = useRouter()
  const currentSessionId = params.sessionId as string

  const [search, setSearch] = useState('')

  const filteredSessions = sessions.filter((s) =>
    s.title.toLowerCase().includes(search.toLowerCase())
  )

  const handleDelete = async (e: React.MouseEvent, sessionId: string) => {
    e.preventDefault()
    e.stopPropagation()
    await removeSession(sessionId)
    if (currentSessionId === sessionId) {
      router.push('/chat/new')
    }
  }

  return (
    <div className="w-[260px] flex-shrink-0 flex flex-col h-full bg-surface border-r border-border">
      {/* ── Top Section ───────────────────────────────────────── */}
      <div className="p-4 flex items-center justify-between">
        <Link href="/chat/new" className="flex items-center gap-2">
          <Scale size={20} className="text-accent" />
          <span className="font-bold">JustiBot</span>
        </Link>
        <ThemeToggle />
      </div>

      {/* ── Middle Section: New Chat ──────────────────────────── */}
      <div className="px-4 pb-4">
        <Link
          href="/chat/new"
          className="flex items-center gap-2 w-full px-4 py-2.5 bg-accent text-white rounded-lg text-sm font-medium hover:bg-accent-hover transition-colors"
        >
          <Plus size={16} />
          New Chat
        </Link>
      </div>

      {/* ── Sessions List ─────────────────────────────────────── */}
      <div className="px-4 pb-2">
        <div className="relative">
          <Search
            size={14}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-muted"
          />
          <input
            type="text"
            placeholder="Search conversations..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 text-xs bg-bg border border-border rounded-lg outline-none focus:border-accent text-text placeholder:text-muted transition-colors"
          />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-2 pb-2">
        {filteredSessions.length === 0 ? (
          <div className="text-center py-8 text-xs text-muted">
            {search ? 'No sessions found.' : 'No previous sessions.'}
          </div>
        ) : (
          <div className="space-y-1 mt-2">
            {filteredSessions.map((session) => {
              const isActive = session.sessionId === currentSessionId
              return (
                <Link
                  key={session.sessionId}
                  href={`/chat/${session.sessionId}`}
                  className={`group flex items-center justify-between p-2 rounded-lg text-sm transition-colors ${
                    isActive
                      ? 'bg-bg border-l-2 border-accent text-text'
                      : 'text-muted hover:bg-bg hover:text-text border-l-2 border-transparent'
                  }`}
                >
                  <div className="flex items-center gap-2 overflow-hidden">
                    <MessageSquare size={14} className="shrink-0" />
                    <div className="flex flex-col truncate">
                      <span className="truncate leading-tight">
                        {session.title || 'Untitled'}
                      </span>
                      <span className="text-[10px] opacity-70">
                        {session.messageCount} messages
                      </span>
                    </div>
                  </div>
                  <button
                    onClick={(e) => handleDelete(e, session.sessionId)}
                    className="opacity-0 group-hover:opacity-100 p-1.5 rounded-md hover:bg-surface text-muted hover:text-danger transition-all"
                    title="Delete session"
                  >
                    <Trash2 size={12} />
                  </button>
                </Link>
              )
            })}
          </div>
        )}
      </div>

      {/* ── Bottom Section ────────────────────────────────────── */}
      <div className="p-4 border-t border-border mt-auto">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 overflow-hidden">
            <div className="w-8 h-8 shrink-0 rounded-full bg-accent flex items-center justify-center text-white font-semibold text-xs">
              {user?.email?.charAt(0).toUpperCase() || 'U'}
            </div>
            <span className="text-xs font-medium truncate">
              {user?.email || 'User'}
            </span>
          </div>
          <button
            onClick={signOut}
            className="p-2 text-muted hover:text-danger hover:bg-bg rounded-lg transition-colors"
            title="Sign out"
          >
            <LogOut size={16} />
          </button>
        </div>
      </div>
    </div>
  )
}
