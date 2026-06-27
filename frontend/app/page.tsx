import Link from 'next/link'
import { Scale, FileText, Shield, Mic, BookOpen, MessageSquare, Lock } from 'lucide-react'
import { ThemeToggle } from '@/components/ui/ThemeToggle'

const features = [
  {
    icon: FileText,
    title: 'Sourced from Official Docs',
    description:
      'Every answer cites BNS, BNSS, RTI Act, Consumer Protection Act, and more — directly from official sources.',
  },
  {
    icon: Shield,
    title: 'Zero Hallucination Design',
    description:
      'RAG architecture retrieves relevant legal text before generating responses. No fabricated sections or invented rulings.',
  },
  {
    icon: Mic,
    title: 'Voice Input Support',
    description:
      'Speak your legal question naturally. JustiBot transcribes and answers in real time.',
  },
  {
    icon: BookOpen,
    title: 'Cited Sources',
    description:
      'Every response includes a "View Sources" panel showing the exact documents referenced.',
  },
  {
    icon: MessageSquare,
    title: 'Multiple Chat Sessions',
    description:
      'Save and revisit conversations. Organize by topic and continue where you left off.',
  },
  {
    icon: Lock,
    title: 'Private and Secure',
    description:
      'Your conversations are private to your account. Firebase Auth ensures only you can access your history.',
  },
]

export default function LandingPage() {
  return (
    <div className="min-h-screen flex flex-col bg-bg text-text">
      {/* ── Nav ───────────────────────────────────────────────────── */}
      <header className="sticky top-0 z-10 bg-bg border-b border-border">
        <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Scale size={20} className="text-accent" />
            <span className="font-bold text-lg">JustiBot</span>
          </div>

          <div className="flex items-center gap-3">
            <ThemeToggle />
            <Link
              href="/login"
              className="px-4 py-1.5 text-sm border border-border rounded-lg hover:border-text/40 transition-colors"
            >
              Sign In
            </Link>
            <Link
              href="/login"
              className="px-4 py-1.5 text-sm bg-accent text-white rounded-lg hover:bg-accent-hover transition-colors"
            >
              Get Started
            </Link>
          </div>
        </div>
      </header>

      {/* ── Hero ──────────────────────────────────────────────────── */}
      <section className="flex-1 flex flex-col items-center justify-center text-center px-6 py-20 min-h-[60vh]">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-border text-muted text-xs mb-6">
          <span className="w-1.5 h-1.5 rounded-full bg-accent"></span>
          Powered by official Indian legal documents
        </div>

        <h1 className="text-5xl md:text-6xl font-bold mb-5 leading-tight">
          Know Your Rights.
        </h1>

        <p className="text-muted text-lg max-w-lg mx-auto mb-8 leading-relaxed">
          India&apos;s AI legal assistant — powered by official legal documents.
          Get accurate answers to your legal questions, instantly.
        </p>

        <Link
          href="/login"
          className="px-8 py-3 bg-accent text-white rounded-lg text-base font-medium hover:bg-accent-hover transition-colors"
        >
          Start for Free →
        </Link>
      </section>

      {/* ── Features ──────────────────────────────────────────────── */}
      <section className="border-t border-border py-16 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {features.map((f) => (
              <div
                key={f.title}
                className="p-5 rounded-lg border border-border bg-surface"
              >
                <div className="w-8 h-8 flex items-center justify-center rounded-lg border border-border mb-3">
                  <f.icon size={16} className="text-accent" />
                </div>
                <h3 className="font-semibold text-sm mb-1.5">{f.title}</h3>
                <p className="text-muted text-sm leading-relaxed">{f.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Footer ────────────────────────────────────────────────── */}
      <footer className="border-t border-border py-6 px-6 text-center">
        <p className="text-muted text-sm">© 2025 JustiBot. Built for Indian citizens.</p>
      </footer>
    </div>
  )
}
