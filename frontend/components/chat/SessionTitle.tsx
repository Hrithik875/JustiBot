'use client'

import { useState, useRef, useEffect, KeyboardEvent } from 'react'
import { Edit2 } from 'lucide-react'
import { updateSessionTitle } from '@/lib/api'

interface SessionTitleProps {
  sessionId: string
  initialTitle: string
  isNewSession: boolean
}

export function SessionTitle({
  sessionId,
  initialTitle,
  isNewSession,
}: SessionTitleProps) {
  const [isEditing, setIsEditing] = useState(false)
  const [title, setTitle] = useState(initialTitle)
  const [currentSavedTitle, setCurrentSavedTitle] = useState(initialTitle)
  const inputRef = useRef<HTMLInputElement>(null)

  // Sync prop changes (e.g. switching sessions)
  useEffect(() => {
    setTitle(initialTitle)
    setCurrentSavedTitle(initialTitle)
  }, [initialTitle, sessionId])

  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus()
      inputRef.current.select()
    }
  }, [isEditing])

  if (isNewSession) {
    return <span className="font-semibold text-sm">New Chat</span>
  }

  const handleSave = async () => {
    const trimmed = title.trim()
    if (!trimmed || trimmed === currentSavedTitle) {
      setTitle(currentSavedTitle)
      setIsEditing(false)
      return
    }
    
    const finalTitle = trimmed.slice(0, 100)
    setTitle(finalTitle)
    setCurrentSavedTitle(finalTitle)
    setIsEditing(false)

    try {
      await updateSessionTitle(sessionId, finalTitle)
    } catch {
      // If API fails, revert local state
      setTitle(currentSavedTitle)
      setCurrentSavedTitle(currentSavedTitle)
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleSave()
    } else if (e.key === 'Escape') {
      setTitle(currentSavedTitle)
      setIsEditing(false)
    }
  }

  if (isEditing) {
    return (
      <input
        ref={inputRef}
        type="text"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        onBlur={handleSave}
        onKeyDown={handleKeyDown}
        maxLength={100}
        className="font-semibold text-sm bg-surface border border-accent rounded px-2 py-0.5 outline-none max-w-[200px] md:max-w-[400px] text-center"
      />
    )
  }

  return (
    <div className="group flex items-center gap-2 cursor-pointer max-w-[200px] md:max-w-[400px]">
      <span
        onDoubleClick={() => setIsEditing(true)}
        className="font-semibold text-sm truncate"
        title={title}
      >
        {title}
      </span>
      <button
        onClick={() => setIsEditing(true)}
        className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-surface text-muted hover:text-text transition-all"
        title="Rename session"
      >
        <Edit2 size={12} />
      </button>
    </div>
  )
}
