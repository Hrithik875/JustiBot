'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useParams, useRouter, usePathname } from 'next/navigation'
import { Scale, Plus, Search, Trash2, LogOut, MessageSquare } from 'lucide-react'
import { ThemeToggle } from '@/components/ui/ThemeToggle'
import { useAuth } from '@/lib/hooks/useAuth'
import { useSessions } from '@/lib/hooks/useSessions'
import { Spinner } from '@/components/ui/Loader'

export function Sidebar() {
  const { user, signOut } = useAuth()
  const { sessions, isLoading, removeSession, loadSessions } = useSessions()
  const params = useParams()
  const router = useRouter()
  const pathname = usePathname()
  const currentSessionId = params.sessionId as string

  const [search, setSearch] = useState('')

  // Reload session list whenever the route changes (e.g. after creating a new session)
  useEffect(() => {
    loadSessions()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname])

  const filteredSessions = sessions.filter((s) =>
    (s.title ?? '').toLowerCase().includes(search.toLowerCase())
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
      {/* ── Brand ─────────────────────────────────────────────────── */}
      <div className="p-4 flex items-center justify-between border-b border-border">
        <Link href="/chat/new" className="flex items-center gap-2">
          <Scale size={20} className="text-accent" />
          <span className="font-bold text-sm">JustiBot</span>
        </Link>
        <ThemeToggle />
      </div>

      {/* ── New Chat ──────────────────────────────────────────────── */}
      <div className="px-3 py-3">
        <Link
          href="/chat/new"
          className="flex items-center justify-center gap-2 w-full px-4 py-2 bg-accent text-white rounded-lg text-sm font-medium hover:bg-accent-hover transition-colors"
        >
          <Plus size={16} />
          New Chat
        </Link>
      </div>

      {/* ── Search ───────────────────────────────────────────────── */}
      <div className="px-3 pb-2">
        <div className="relative">
          <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted pointer-events-none" />
          <input
            type="text"
            placeholder="Search…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 text-xs bg-bg border border-border rounded-lg outline-none focus:border-accent text-text placeholder:text-muted transition-colors"
          />
        </div>
      </div>

      {/* ── Sessions List ─────────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto px-2 pb-2">
        {isLoading && sessions.length === 0 ? (
          <div className="flex justify-center py-6">
            <Spinner size={18} />
          </div>
        ) : filteredSessions.length === 0 ? (
          <div className="text-center py-8 text-xs text-muted px-4">
            {search ? 'No sessions match your search.' : 'No conversations yet. Start a new chat!'}
          </div>
        ) : (
          <div className="space-y-0.5 mt-1">
            {filteredSessions.map((session) => {
              const isActive = session.sessionId === currentSessionId
              return (
                <Link
                  key={session.sessionId}
                  href={`/chat/${session.sessionId}`}
                  className={`group flex items-center justify-between px-3 py-2 rounded-lg text-sm transition-colors ${
                    isActive
                      ? 'bg-accent/10 text-accent border border-accent/20'
                      : 'text-muted hover:bg-bg hover:text-text'
                  }`}
                >
                  <div className="flex items-center gap-2.5 overflow-hidden min-w-0">
                    <MessageSquare size={13} className="shrink-0" />
                    <div className="flex flex-col min-w-0">
                      <span className="truncate text-xs leading-tight font-medium">
                        {session.title || 'Untitled'}
                      </span>
                      <span className="text-[10px] opacity-60 mt-0.5">
                        {session.messageCount ?? 0} messages
                      </span>
                    </div>
                  </div>
                  <button
                    onClick={(e) => handleDelete(e, session.sessionId)}
                    className="opacity-0 group-hover:opacity-100 p-1.5 rounded hover:bg-surface text-muted hover:text-danger transition-all shrink-0 ml-1"
                    title="Delete"
                  >
                    <Trash2 size={11} />
                  </button>
                </Link>
              )
            })}
          </div>
        )}
      </div>

      {/* ── User Footer ───────────────────────────────────────────── */}
      <div className="p-3 border-t border-border">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 overflow-hidden min-w-0">
            <div className="w-7 h-7 shrink-0 rounded-full bg-accent flex items-center justify-center text-white font-semibold text-xs">
              {user?.email?.charAt(0).toUpperCase() || 'U'}
            </div>
            <span className="text-xs font-medium truncate text-muted">
              {user?.email || 'User'}
            </span>
          </div>
          <button
            onClick={signOut}
            className="p-1.5 text-muted hover:text-danger hover:bg-bg rounded-lg transition-colors shrink-0"
            title="Sign out"
          >
            <LogOut size={14} />
          </button>
        </div>
      </div>
    </div>
  )
}
