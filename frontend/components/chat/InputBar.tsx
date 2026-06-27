'use client'

import { useState, useRef, useEffect, KeyboardEvent } from 'react'
import { Send, Mic, Square } from 'lucide-react'

// Define SpeechRecognition types for TS
interface SpeechRecognitionEvent {
  results: {
    [index: number]: {
      [index: number]: {
        transcript: string
      }
    }
  }
}

interface SpeechRecognition extends EventTarget {
  continuous: boolean
  interimResults: boolean
  lang: string
  start: () => void
  stop: () => void
  onresult: (event: SpeechRecognitionEvent) => void
  onend: () => void
  onerror: (event: { error: string }) => void
}

declare global {
  interface Window {
    SpeechRecognition?: { new (): SpeechRecognition }
    webkitSpeechRecognition?: { new (): SpeechRecognition }
  }
}

interface InputBarProps {
  onSend: (query: string) => void
  disabled: boolean
  isLoading: boolean
}

export function InputBar({ onSend, disabled, isLoading }: InputBarProps) {
  const [query, setQuery] = useState('')
  const [isListening, setIsListening] = useState(false)
  const [supportSpeech, setSupportSpeech] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const recognitionRef = useRef<SpeechRecognition | null>(null)

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const SpeechRecognition =
        window.SpeechRecognition || window.webkitSpeechRecognition
      if (SpeechRecognition) {
        setSupportSpeech(true)
        const recognition = new SpeechRecognition()
        recognition.continuous = false
        recognition.interimResults = false
        recognition.lang = 'en-IN' // Indian English for legal context

        recognition.onresult = (event) => {
          const transcript = event.results[0][0].transcript
          setQuery((prev) => (prev ? `${prev} ${transcript}` : transcript))
        }

        recognition.onend = () => {
          setIsListening(false)
        }

        recognition.onerror = () => {
          setIsListening(false)
        }

        recognitionRef.current = recognition
      }
    }
  }, [])

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${Math.min(
        textareaRef.current.scrollHeight,
        150 // approx 6 rows
      )}px`
    }
  }, [query])

  const handleSubmit = () => {
    const trimmed = query.trim()
    if (!trimmed || disabled || isLoading) return
    onSend(trimmed)
    setQuery('')
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const toggleListen = () => {
    if (isListening) {
      recognitionRef.current?.stop()
    } else {
      setQuery('') // optional: clear previous before listening
      try {
        recognitionRef.current?.start()
        setIsListening(true)
      } catch (e) {
        console.error('Speech recognition error', e)
        setIsListening(false)
      }
    }
  }

  return (
    <div className="border border-border bg-surface rounded-xl flex items-end p-2 gap-2 max-w-4xl mx-auto w-full shadow-sm">
      <textarea
        ref={textareaRef}
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask a legal question..."
        className="flex-1 max-h-[150px] bg-transparent resize-none outline-none text-sm p-2 text-text placeholder:text-muted"
        rows={1}
        disabled={disabled}
      />

      <div className="flex items-center gap-1 pb-1 shrink-0">
        {supportSpeech && (
          <button
            onClick={toggleListen}
            disabled={disabled}
            className={`p-2 rounded-lg transition-colors ${
              isListening
                ? 'bg-danger/10 text-danger animate-pulse'
                : 'text-muted hover:bg-bg hover:text-text'
            }`}
            title="Voice Input"
          >
            {isListening ? <Square size={18} fill="currentColor" /> : <Mic size={18} />}
          </button>
        )}

        <button
          onClick={handleSubmit}
          disabled={!query.trim() || disabled || isLoading}
          className={`p-2 rounded-lg transition-colors ${
            !query.trim() || disabled || isLoading
              ? 'text-muted opacity-50 cursor-not-allowed'
              : 'bg-accent text-white hover:bg-accent-hover'
          }`}
        >
          <Send size={18} />
        </button>
      </div>
    </div>
  )
}
