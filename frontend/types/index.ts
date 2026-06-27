export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources: Source[]
  cached: boolean
  semanticCache?: boolean
  createdAt: string
}

export interface Source {
  name: string
  url: string
  category: string
  relevanceScore: number
}

export interface Session {
  sessionId: string
  title: string
  createdAt: string
  updatedAt: string
  messageCount: number
}

export interface ChatResponse {
  answer: string
  sources: Source[]
  model: string
  contextChunksUsed: number
  cached: boolean
  semanticCache?: boolean
  sessionId: string
  userUid: string
}

export type Theme = 'dark' | 'light'

export type LegalCategory =
  | 'criminal'
  | 'civil'
  | 'constitutional'
  | 'cyber'
  | 'consumer'
  | 'procedural'
  | null
