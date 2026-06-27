'use client'

import { useState, useEffect, useCallback } from 'react'
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
  const [currentSessionId] = useState(() =>
    sessionId === 'new' ? uuidv4() : sessionId
  )
  const router = useRouter()
  const isNew = sessionId === 'new'

  const loadMessages = useCallback(async (sid: string) => {
    if (sid === 'new') return
    try {
      const { messages: loaded } = await api.getSessionMessages(sid)
      setMessages(loaded)
    } catch {
      // non-fatal — user may have no messages yet
    }
  }, [])

  useEffect(() => {
    if (!isNew) {
      loadMessages(sessionId)
    }
  }, [sessionId, isNew, loadMessages])

  const sendMessage = useCallback(
    async (query: string, categoryFilter?: string | null) => {
      setError(null)

      // Optimistic user message
      const optimisticMsg: Message = {
        id: `tmp-${Date.now()}`,
        role: 'user',
        content: query,
        sources: [],
        cached: false,
        createdAt: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, optimisticMsg])
      setIsLoading(true)

      // Build conversation history from current messages (last 6)
      const history = messages
        .slice(-6)
        .map((m) => ({ role: m.role, content: m.content }))

      try {
        const response = await api.sendMessage({
          query,
          sessionId: currentSessionId,
          isNewSession: isNew && messages.length === 0,
          conversationHistory: history,
          categoryFilter: categoryFilter ?? null,
        })

        const assistantMsg: Message = {
          id: `ai-${Date.now()}`,
          role: 'assistant',
          content: response.answer,
          sources: response.sources,
          cached: response.cached,
          semanticCache: response.semanticCache,
          createdAt: new Date().toISOString(),
        }

        setMessages((prev) => [...prev, assistantMsg])

        // Navigate from /new to real session route after first message
        if (isNew) {
          router.replace(`/chat/${currentSessionId}`)
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Something went wrong')
        // Remove optimistic message on failure
        setMessages((prev) => prev.filter((m) => m.id !== optimisticMsg.id))
      } finally {
        setIsLoading(false)
      }
    },
    [messages, currentSessionId, isNew, router]
  )

  return { messages, isLoading, error, sendMessage, loadMessages, currentSessionId }
}
