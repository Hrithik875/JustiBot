'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { v4 as uuidv4 } from 'uuid'
import type { Message } from '@/types'
import * as api from '@/lib/api'

interface UseChatReturn {
  messages: Message[]
  isLoading: boolean
  error: string | null
  sendMessage: (query: string, categoryFilter?: string | null) => Promise<void>
  loadMessages: (sessionId: string) => Promise<void>
  currentSessionId: string
}

export function useChat(sessionId: string): UseChatReturn {
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const sessionIdRef = useRef<string>(
    sessionId === 'new' ? uuidv4() : sessionId
  )

  const hasInMemoryMessages = useRef(false)

  const router = useRouter()

  const loadMessages = useCallback(async (sid: string) => {
    if (sid === 'new') return
    if (hasInMemoryMessages.current) return

    setIsLoading(true)
    try {
      const { messages: loaded } = await api.getSessionMessages(sid)
      if (!hasInMemoryMessages.current) {
        setMessages(loaded)
      }
    } catch {
      // non-fatal
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    if (sessionId !== 'new') {
      sessionIdRef.current = sessionId
      if (!hasInMemoryMessages.current) {
        setMessages([])
        loadMessages(sessionId)
      }
    } else {
      hasInMemoryMessages.current = false
      sessionIdRef.current = uuidv4()
      setMessages([])
    }
  }, [sessionId, loadMessages])

  useEffect(() => {
    if (
      sessionId !== 'new' &&
      sessionId !== sessionIdRef.current
    ) {
      hasInMemoryMessages.current = false
      sessionIdRef.current = sessionId
      setMessages([])
      loadMessages(sessionId)
    }
  }, [sessionId, loadMessages])

  // ─── THIS IS THE FIX ───────────────────────────────────────────
  // sendMessage no longer has 'messages' in its dependency array.
  // History and user message are both captured inside functional
  // state updaters, guaranteeing we always read current state —
  // never a stale closure value.
  // The assistantMsg is built inside the setMessages updater so
  // response.answer is always the value from THIS call, not a
  // previous one.
  // ───────────────────────────────────────────────────────────────
  const sendMessage = useCallback(
    async (query: string, categoryFilter?: string | null) => {
      setError(null)
      const currentSessionId = sessionIdRef.current
      const isNew = sessionId === 'new'

      // Capture history and add user message in a single
      // synchronous state update — no stale closure risk
      let capturedHistory: { role: string; content: string }[] = []
      let isFirstMessage = false

      setMessages((prev) => {
        capturedHistory = prev
          .slice(-6)
          .map((m) => ({ role: m.role, content: m.content }))
        isFirstMessage = prev.length === 0

        const userMsg: Message = {
          id: `user-${Date.now()}`,
          role: 'user',
          content: query,
          sources: [],
          cached: false,
          createdAt: new Date().toISOString(),
        }
        return [...prev, userMsg]
      })

      setIsLoading(true)

      try {
        const response = await api.sendMessage({
          query,
          sessionId: currentSessionId,
          isNewSession: isNew && isFirstMessage,
          conversationHistory: capturedHistory,
          categoryFilter: categoryFilter ?? null,
        })

        // Build and append assistant message inside functional updater
        // response is a local variable — always correct for this call
        setMessages((prev) => {
          const assistantMsg: Message = {
            id: `ai-${Date.now()}`,
            role: 'assistant',
            content: response.answer,
            sources: response.sources,
            cached: response.cached,
            semanticCache: response.semanticCache,
            retrievalBroadened: response.retrievalBroadened,
            model: response.model,
            createdAt: new Date().toISOString(),
          }
          return [...prev, assistantMsg]
        })

        hasInMemoryMessages.current = true

        if (isNew) {
          router.replace(`/chat/${currentSessionId}`)
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Something went wrong')
        // Remove the user message we added on failure
        setMessages((prev) => prev.slice(0, -1))
      } finally {
        setIsLoading(false)
      }
    },
    // 'messages' intentionally removed from deps —
    // state is read via functional updater instead
    [sessionId, router]
  )

  return {
    messages,
    isLoading,
    error,
    sendMessage,
    loadMessages,
    currentSessionId: sessionIdRef.current,
  }
}