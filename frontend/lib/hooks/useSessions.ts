'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import type { Session } from '@/types'
import * as api from '@/lib/api'

interface UseSessionsReturn {
  sessions: Session[]
  isLoading: boolean
  loadSessions: () => Promise<void>
  removeSession: (sessionId: string) => Promise<void>
  refreshSessions: () => void
}

export function useSessions(): UseSessionsReturn {
  const [sessions, setSessions] = useState<Session[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const hasFetched = useRef(false)

  const loadSessions = useCallback(async () => {
    setIsLoading(true)
    try {
      const data = await api.getSessions()
      const sorted = [...data].sort(
        (a, b) =>
          new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
      )
      setSessions(sorted)
    } catch (e) {
      console.error('[useSessions] loadSessions failed:', e)
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    if (!hasFetched.current) {
      hasFetched.current = true
      loadSessions()
    }
  }, [loadSessions])

  // Expose a lightweight refresh trigger
  const refreshSessions = useCallback(() => {
    loadSessions()
  }, [loadSessions])

  const removeSession = useCallback(
    async (sessionId: string) => {
      // Optimistic removal
      setSessions((prev) => prev.filter((s) => s.sessionId !== sessionId))
      try {
        await api.deleteSession(sessionId)
        // Reload to get consistent order
        loadSessions()
      } catch (e) {
        console.error('[useSessions] removeSession failed:', e)
        loadSessions()
      }
    },
    [loadSessions]
  )

  return { sessions, isLoading, loadSessions, removeSession, refreshSessions }
}
