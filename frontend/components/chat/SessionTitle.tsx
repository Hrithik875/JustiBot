'use client'

import { useState, useEffect, useRef } from 'react'
import { Edit2, X, Check } from 'lucide-react'
import { updateSessionTitle } from '@/lib/api'

const MAX_LEN = 60

interface SessionTitleProps {
  sessionId: string
  initialTitle: string
  isNewSession: boolean
}

export function SessionTitle({ sessionId, initialTitle, isNewSession }: SessionTitleProps) {
  const [savedTitle, setSavedTitle] = useState(initialTitle)
  const [modalOpen, setModalOpen] = useState(false)
  const [draft, setDraft] = useState(initialTitle)
  const [saving, setSaving] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    setSavedTitle(initialTitle)
    setDraft(initialTitle)
  }, [initialTitle, sessionId])

  useEffect(() => {
    if (modalOpen && inputRef.current) {
      inputRef.current.focus()
      inputRef.current.select()
    }
  }, [modalOpen])

  const open = () => {
    setDraft(savedTitle)
    setModalOpen(true)
  }

  const cancel = () => {
    setDraft(savedTitle)
    setModalOpen(false)
  }

  const save = async () => {
    const trimmed = draft.trim().slice(0, MAX_LEN)
    if (!trimmed || trimmed === savedTitle) {
      cancel()
      return
    }
    setSaving(true)
    try {
      await updateSessionTitle(sessionId, trimmed)
      setSavedTitle(trimmed)
    } catch (e) {
      console.error('Failed to rename session', e)
    } finally {
      setSaving(false)
      setModalOpen(false)
    }
  }

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') save()
    if (e.key === 'Escape') cancel()
  }

  if (isNewSession) {
    return <span className="font-semibold text-sm">New Chat</span>
  }

  return (
    <>
      {/* Title display with edit button */}
      <div className="group flex items-center gap-1.5 max-w-[220px] md:max-w-[380px]">
        <span
          className="font-semibold text-sm truncate cursor-default"
          title={savedTitle}
        >
          {savedTitle || 'Untitled'}
        </span>
        <button
          onClick={open}
          className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-surface text-muted hover:text-text transition-all shrink-0"
          title="Rename"
        >
          <Edit2 size={12} />
        </button>
      </div>

      {/* Modal popup */}
      {modalOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center"
          onClick={(e) => { if (e.target === e.currentTarget) cancel() }}
        >
          {/* Backdrop */}
          <div className="absolute inset-0 bg-black/50" />

          {/* Dialog */}
          <div className="relative bg-surface border border-border rounded-xl p-6 w-full max-w-sm mx-4 shadow-2xl">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold text-sm">Rename conversation</h2>
              <button
                onClick={cancel}
                className="p-1 rounded hover:bg-bg text-muted hover:text-text transition-colors"
              >
                <X size={16} />
              </button>
            </div>

            <input
              ref={inputRef}
              type="text"
              value={draft}
              onChange={(e) => setDraft(e.target.value.slice(0, MAX_LEN))}
              onKeyDown={handleKey}
              placeholder="Enter a name…"
              className="w-full px-3 py-2.5 rounded-lg border border-border bg-bg text-text text-sm placeholder:text-muted focus:outline-none focus:border-accent transition-colors"
            />

            {/* Character count */}
            <div className="flex items-center justify-between mt-1.5">
              <span className={`text-xs ${draft.length >= MAX_LEN ? 'text-danger' : 'text-muted'}`}>
                {draft.length}/{MAX_LEN} characters
              </span>
              <span className="text-xs text-muted">Enter to save · Esc to cancel</span>
            </div>

            <div className="flex gap-2 mt-4">
              <button
                onClick={cancel}
                className="flex-1 py-2 rounded-lg border border-border text-sm text-muted hover:bg-bg hover:text-text transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={save}
                disabled={saving || !draft.trim() || draft.trim() === savedTitle}
                className="flex-1 py-2 rounded-lg bg-accent text-white text-sm font-medium hover:bg-accent-hover transition-colors disabled:opacity-50 flex items-center justify-center gap-1.5"
              >
                {saving ? (
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  <Check size={14} />
                )}
                {saving ? 'Saving…' : 'Save'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
