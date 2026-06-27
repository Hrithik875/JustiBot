import type { ChatResponse, Message, Session } from '@/types'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'

async function getAuthToken(): Promise<string> {
  const { auth } = await import('./firebase')
  const user = auth.currentUser
  if (!user) throw new Error('Not authenticated')
  return user.getIdToken()
}

async function fetchWithAuth(
  endpoint: string,
  options: RequestInit = {}
): Promise<Response> {
  const token = await getAuthToken()
  return fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
      ...options.headers,
    },
  })
}

// ── Chat ──────────────────────────────────────────────────────────────────────

export async function sendMessage(params: {
  query: string
  sessionId: string
  isNewSession: boolean
  conversationHistory: { role: string; content: string }[]
  categoryFilter?: string | null
}): Promise<ChatResponse> {
  const res = await fetchWithAuth('/chat', {
    method: 'POST',
    body: JSON.stringify({
      query: params.query,
      session_id: params.sessionId,
      is_new_session: params.isNewSession,
      conversation_history: params.conversationHistory,
      category_filter: params.categoryFilter ?? null,
    }),
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }

  const data = await res.json()
  // Map snake_case response keys to camelCase
  return {
    answer: data.answer,
    sources: (data.sources || []).map((s: Record<string, unknown>) => ({
      name: s.name,
      url: s.url,
      category: s.category,
      relevanceScore: s.relevance_score,
    })),
    model: data.model,
    contextChunksUsed: data.context_chunks_used,
    cached: data.cached,
    semanticCache: data.semantic_cache,
    sessionId: data.session_id,
    userUid: data.user_uid,
  }
}

// ── Sessions ──────────────────────────────────────────────────────────────────

export async function getSessions(): Promise<Session[]> {
  const res = await fetchWithAuth('/chat/sessions')
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  const data = await res.json()
  return (data.sessions || []).map((s: Record<string, unknown>) => ({
    sessionId: s.session_id,
    title: s.title,
    createdAt: s.created_at,
    updatedAt: s.updated_at,
    messageCount: s.message_count,
  }))
}

export async function getSessionMessages(
  sessionId: string,
  limit = 50
): Promise<{ session: Session; messages: Message[] }> {
  const res = await fetchWithAuth(
    `/chat/sessions/${sessionId}/messages?limit=${limit}`
  )
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  const data = await res.json()

  const session: Session = {
    sessionId: data.session?.session_id ?? sessionId,
    title: data.session?.title ?? 'Untitled',
    createdAt: data.session?.created_at ?? '',
    updatedAt: data.session?.updated_at ?? '',
    messageCount: data.session?.message_count ?? 0,
  }

  const messages: Message[] = (data.messages || []).map(
    (m: Record<string, unknown>) => ({
      id: m.message_id as string,
      role: m.role as 'user' | 'assistant',
      content: m.content as string,
      sources: ((m.sources as Record<string, unknown>[]) || []).map((s) => ({
        name: s.name,
        url: s.url,
        category: s.category,
        relevanceScore: s.relevance_score ?? s.relevanceScore ?? 0,
      })),
      cached: (m.cached as boolean) ?? false,
      createdAt: (m.created_at as string) ?? '',
    })
  )

  return { session, messages }
}

export async function deleteSession(sessionId: string): Promise<void> {
  const res = await fetchWithAuth(`/chat/sessions/${sessionId}`, {
    method: 'DELETE',
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
}

export async function updateSessionTitle(
  sessionId: string,
  title: string
): Promise<void> {
  const res = await fetchWithAuth(`/chat/sessions/${sessionId}/title`, {
    method: 'PATCH',
    body: JSON.stringify({ title }),
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
}
