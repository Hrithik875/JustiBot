'use client'

/* ─────────────────────────────────────────────────────────────
   Full-screen loader shown while Firebase checks auth state
   ──────────────────────────────────────────────────────────── */
export function FullPageLoader({ message = 'Loading…' }: { message?: string }) {
  return (
    <div className="fixed inset-0 bg-bg flex flex-col items-center justify-center z-50 gap-4">
      <Spinner size={32} />
      <p className="text-muted text-sm">{message}</p>
    </div>
  )
}

/* ─────────────────────────────────────────────────────────────
   Generic spinner
   ──────────────────────────────────────────────────────────── */
export function Spinner({ size = 20, className = '' }: { size?: number; className?: string }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      className={`animate-spin text-accent ${className}`}
      aria-label="Loading"
    >
      <circle
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="3"
        strokeOpacity="0.25"
      />
      <path
        d="M12 2a10 10 0 0 1 10 10"
        stroke="currentColor"
        strokeWidth="3"
        strokeLinecap="round"
      />
    </svg>
  )
}
