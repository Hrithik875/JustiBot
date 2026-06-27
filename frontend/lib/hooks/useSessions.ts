'use client'

import { useState, useEffect, useCallback } from 'react'
import type { Session } from '@/types'
import * as api from '@/lib/api'

interface UseSessionsReturn {
  sessions: Session[]
  isLoading: boolean
  loadSessions: () => Promise<void>
  removeSession: (sessionId: string) => Promise<void>
}

export function useSessions(): UseSessionsReturn {
  const [sessions, setSessions] = useState<Session[]>([])
  const [isLoading, setIsLoading] = useState(false)

  const loadSessions = useCallback(async () => {
    setIsLoading(true)
    try {
      const data = await api.getSessions()
      // Sort by updatedAt descending
      const sorted = [...data].sort(
        (a, b) =>
          new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
      )
      setSessions(sorted)
    } catch {
      // non-fatal
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    loadSessions()
  }, [loadSessions])

  const removeSession = useCallback(async (sessionId: string) => {
    // Optimistic removal
    setSessions((prev) => prev.filter((s) => s.sessionId !== sessionId))
    try {
      await api.deleteSession(sessionId)
    } catch {
      // On failure, reload to restore correct state
      loadSessions()
    }
  }, [loadSessions])

  return { sessions, isLoading, loadSessions, removeSession }
}
