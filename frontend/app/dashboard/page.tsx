'use client'

import { useEffect, useState, useCallback } from 'react'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  ArcElement,
  Tooltip,
  Legend,
} from 'chart.js'
import { Bar, Doughnut } from 'react-chartjs-2'
import {
  Activity,
  Zap,
  Clock,
  DollarSign,
  RefreshCw,
  AlertTriangle,
} from 'lucide-react'
import { getObservabilityStats, getRecentEvents } from '@/lib/api'

// ── Register Chart.js components ─────────────────────────────────────────────

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  ArcElement,
  Tooltip,
  Legend
)

// ── Types ────────────────────────────────────────────────────────────────────

interface Stats {
  total_requests: number
  cache_hit_ratio: number
  cache_breakdown: { exact: number; semantic: number; miss: number }
  avg_latency_ms: Record<string, number>
  category_breakdown: Record<string, number>
  model_breakdown: Record<string, number>
  hallucination_breakdown: { high: number; medium: number; low: number }
  total_estimated_cost_usd: number
  avg_cost_per_request_usd: number
}

interface PipelineEvent {
  timestamp: string
  query_category: string
  model_used: string
  cache_hit: boolean
  cache_type: string | null
  timings_ms: Record<string, number>
  hallucination_confidence: string
  estimated_cost_usd: number
}

// ── Color palette ────────────────────────────────────────────────────────────

const ACCENT = '#2563EB'
const ACCENT_LIGHT = '#3B82F6'
const SURFACE = '#141414'
const BORDER = '#262626'
const TEXT = '#FAFAFA'
const MUTED = '#737373'

const STAGE_COLORS = [
  '#6366F1', // classification — indigo
  '#8B5CF6', // embedding — violet
  '#EC4899', // hybrid_search — pink
  '#F97316', // reranking — orange
  '#2563EB', // generation — blue (accent)
  '#10B981', // hallucination_check — emerald
]

const CATEGORY_COLORS = [
  '#6366F1', // GREETING
  '#3B82F6', // LEGAL_SIMPLE
  '#8B5CF6', // LEGAL_COMPLEX
  '#EF4444', // UNSAFE
  '#F97316', // OUT_OF_DOMAIN
  '#737373', // other
]

const MODEL_COLORS = ['#3B82F6', '#8B5CF6', '#F97316', '#10B981']

const CONFIDENCE_COLORS = {
  high: '#10B981',
  medium: '#F59E0B',
  low: '#EF4444',
}

// ── Chart defaults ───────────────────────────────────────────────────────────

const chartFont = { family: "'Inter', sans-serif", size: 11 }

// ── Component ────────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const [stats, setStats] = useState<Stats | null>(null)
  const [events, setEvents] = useState<PipelineEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchData = useCallback(async (isRefresh = false) => {
    try {
      if (isRefresh) setRefreshing(true)
      else setLoading(true)

      const [statsData, eventsData] = await Promise.all([
        getObservabilityStats(),
        getRecentEvents(20),
      ])

      setStats(statsData as unknown as Stats)
      setEvents((eventsData.events || []) as unknown as PipelineEvent[])
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  // ── Loading state ────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-32 gap-4">
        <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin" />
        <p className="text-muted text-sm">Loading dashboard data…</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-32 gap-4">
        <AlertTriangle size={32} className="text-danger" />
        <p className="text-muted text-sm">{error}</p>
        <button
          onClick={() => fetchData()}
          className="px-4 py-2 bg-accent text-white rounded-lg text-sm hover:bg-accent-hover transition-colors"
        >
          Retry
        </button>
      </div>
    )
  }

  if (!stats) return null

  // ── Derived data ─────────────────────────────────────────────────────────

  const latencyStages = [
    'classification',
    'embedding',
    'hybrid_search',
    'reranking',
    'generation',
    'hallucination_check',
  ]
  const latencyLabels = [
    'Classification',
    'Embedding',
    'Hybrid Search',
    'Reranking',
    'Generation',
    'Hallucination Check',
  ]
  const latencyValues = latencyStages.map(
    (s) => stats.avg_latency_ms[s] ?? 0
  )

  const categoryLabels = Object.keys(stats.category_breakdown)
  const categoryValues = Object.values(stats.category_breakdown)

  const modelLabels = Object.keys(stats.model_breakdown)
  const modelValues = Object.values(stats.model_breakdown)

  const hallLabels = ['High', 'Medium', 'Low']
  const hallValues = [
    stats.hallucination_breakdown.high,
    stats.hallucination_breakdown.medium,
    stats.hallucination_breakdown.low,
  ]

  // ── Render ───────────────────────────────────────────────────────────────

  return (
    <div className="space-y-6 pb-8">
      {/* Header row */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-text">
            Pipeline Observability
          </h2>
          <p className="text-xs text-muted mt-0.5">
            Real-time performance metrics from the last {stats.total_requests}{' '}
            requests
          </p>
        </div>
        <button
          onClick={() => fetchData(true)}
          disabled={refreshing}
          className="flex items-center gap-2 px-3 py-1.5 bg-surface border border-border rounded-lg text-xs text-muted hover:text-text hover:border-accent/40 transition-all disabled:opacity-50"
        >
          <RefreshCw
            size={13}
            className={refreshing ? 'animate-spin' : ''}
          />
          Refresh
        </button>
      </div>

      {/* ── SECTION 1: Summary Cards ────────────────────────────────────── */}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <SummaryCard
          icon={<Activity size={18} />}
          label="Total Requests"
          value={stats.total_requests.toLocaleString()}
          sub={`${stats.cache_breakdown.miss} cache misses`}
          accent="#6366F1"
        />
        <SummaryCard
          icon={<Zap size={18} />}
          label="Cache Hit Ratio"
          value={`${(stats.cache_hit_ratio * 100).toFixed(1)}%`}
          sub={`${stats.cache_breakdown.exact} exact · ${stats.cache_breakdown.semantic} semantic`}
          accent="#10B981"
        />
        <SummaryCard
          icon={<Clock size={18} />}
          label="Avg Total Latency"
          value={`${(stats.avg_latency_ms.total ?? 0).toFixed(0)} ms`}
          sub={`Generation: ${(stats.avg_latency_ms.generation ?? 0).toFixed(0)} ms`}
          accent={ACCENT}
        />
        <SummaryCard
          icon={<DollarSign size={18} />}
          label="Total Est. Cost"
          value={`$${stats.total_estimated_cost_usd.toFixed(4)}`}
          sub={`Avg $${stats.avg_cost_per_request_usd.toFixed(6)} / req`}
          accent="#F97316"
        />
      </div>

      {/* ── SECTION 2: Latency Breakdown ────────────────────────────────── */}

      <div className="bg-surface border border-border rounded-xl p-5">
        <h3 className="text-sm font-semibold text-text mb-4">
          Pipeline Stage Latency (avg ms)
        </h3>
        <div className="h-64">
          <Bar
            data={{
              labels: latencyLabels,
              datasets: [
                {
                  label: 'Avg Latency (ms)',
                  data: latencyValues,
                  backgroundColor: STAGE_COLORS,
                  borderRadius: 6,
                  borderSkipped: false,
                  maxBarThickness: 48,
                },
              ],
            }}
            options={{
              responsive: true,
              maintainAspectRatio: false,
              plugins: {
                legend: { display: false },
                tooltip: {
                  backgroundColor: SURFACE,
                  borderColor: BORDER,
                  borderWidth: 1,
                  titleFont: chartFont,
                  bodyFont: chartFont,
                  titleColor: TEXT,
                  bodyColor: MUTED,
                  callbacks: {
                    label: (ctx) => `${ctx.parsed.y.toFixed(1)} ms`,
                  },
                },
              },
              scales: {
                x: {
                  grid: { display: false },
                  ticks: { color: MUTED, font: chartFont },
                  border: { display: false },
                },
                y: {
                  grid: { color: BORDER },
                  ticks: {
                    color: MUTED,
                    font: chartFont,
                    callback: (v) => `${v} ms`,
                  },
                  border: { display: false },
                },
              },
            }}
          />
        </div>
      </div>

      {/* ── SECTION 3: Category & Model Breakdown ───────────────────────── */}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Category Donut */}
        <div className="bg-surface border border-border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-text mb-4">
            Query Categories
          </h3>
          <div className="h-56 flex items-center justify-center">
            {categoryLabels.length > 0 ? (
              <Doughnut
                data={{
                  labels: categoryLabels,
                  datasets: [
                    {
                      data: categoryValues,
                      backgroundColor: CATEGORY_COLORS.slice(
                        0,
                        categoryLabels.length
                      ),
                      borderColor: SURFACE,
                      borderWidth: 2,
                    },
                  ],
                }}
                options={{
                  responsive: true,
                  maintainAspectRatio: false,
                  cutout: '60%',
                  plugins: {
                    legend: {
                      position: 'right',
                      labels: {
                        color: MUTED,
                        font: chartFont,
                        padding: 12,
                        usePointStyle: true,
                        pointStyleWidth: 8,
                      },
                    },
                    tooltip: {
                      backgroundColor: SURFACE,
                      borderColor: BORDER,
                      borderWidth: 1,
                      titleFont: chartFont,
                      bodyFont: chartFont,
                      titleColor: TEXT,
                      bodyColor: MUTED,
                    },
                  },
                }}
              />
            ) : (
              <p className="text-xs text-muted">No data yet</p>
            )}
          </div>
        </div>

        {/* Model Donut */}
        <div className="bg-surface border border-border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-text mb-4">
            Model Usage
          </h3>
          <div className="h-56 flex items-center justify-center">
            {modelLabels.length > 0 ? (
              <Doughnut
                data={{
                  labels: modelLabels,
                  datasets: [
                    {
                      data: modelValues,
                      backgroundColor: MODEL_COLORS.slice(
                        0,
                        modelLabels.length
                      ),
                      borderColor: SURFACE,
                      borderWidth: 2,
                    },
                  ],
                }}
                options={{
                  responsive: true,
                  maintainAspectRatio: false,
                  cutout: '60%',
                  plugins: {
                    legend: {
                      position: 'right',
                      labels: {
                        color: MUTED,
                        font: chartFont,
                        padding: 12,
                        usePointStyle: true,
                        pointStyleWidth: 8,
                      },
                    },
                    tooltip: {
                      backgroundColor: SURFACE,
                      borderColor: BORDER,
                      borderWidth: 1,
                      titleFont: chartFont,
                      bodyFont: chartFont,
                      titleColor: TEXT,
                      bodyColor: MUTED,
                    },
                  },
                }}
              />
            ) : (
              <p className="text-xs text-muted">No data yet</p>
            )}
          </div>
        </div>
      </div>

      {/* ── SECTION 4: Hallucination Confidence ─────────────────────────── */}

      <div className="bg-surface border border-border rounded-xl p-5">
        <h3 className="text-sm font-semibold text-text mb-4">
          Hallucination Confidence Breakdown
        </h3>
        <div className="space-y-3">
          {hallLabels.map((label, i) => {
            const total =
              hallValues[0] + hallValues[1] + hallValues[2] || 1
            const pct = ((hallValues[i] / total) * 100).toFixed(1)
            const color =
              CONFIDENCE_COLORS[
                label.toLowerCase() as keyof typeof CONFIDENCE_COLORS
              ]
            return (
              <div key={label} className="flex items-center gap-3">
                <span className="text-xs text-muted w-16 shrink-0">
                  {label}
                </span>
                <div className="flex-1 h-6 bg-bg rounded-lg overflow-hidden relative">
                  <div
                    className="h-full rounded-lg transition-all duration-500"
                    style={{
                      width: `${pct}%`,
                      backgroundColor: color,
                      minWidth: hallValues[i] > 0 ? '2px' : '0px',
                    }}
                  />
                </div>
                <span className="text-xs text-muted w-16 text-right tabular-nums">
                  {hallValues[i]} ({pct}%)
                </span>
              </div>
            )
          })}
        </div>
      </div>

      {/* ── SECTION 5: Recent Requests Table ────────────────────────────── */}

      <div className="bg-surface border border-border rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-border">
          <h3 className="text-sm font-semibold text-text">
            Recent Requests
          </h3>
          <p className="text-xs text-muted mt-0.5">
            Last {events.length} pipeline events
          </p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-border">
                {[
                  'Time',
                  'Category',
                  'Model',
                  'Cache',
                  'Latency',
                  'Cost',
                  'Confidence',
                ].map((h) => (
                  <th
                    key={h}
                    className="px-4 py-3 text-left text-muted font-medium whitespace-nowrap"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {events.length === 0 ? (
                <tr>
                  <td
                    colSpan={7}
                    className="px-4 py-12 text-center text-muted"
                  >
                    No events recorded yet. Send some queries through the chat
                    to see data here.
                  </td>
                </tr>
              ) : (
                events.map((ev, i) => (
                  <tr
                    key={i}
                    className="border-b border-border/50 hover:bg-bg/50 transition-colors"
                  >
                    <td className="px-4 py-2.5 text-muted whitespace-nowrap tabular-nums">
                      {formatTime(ev.timestamp)}
                    </td>
                    <td className="px-4 py-2.5">
                      <CategoryBadge category={ev.query_category} />
                    </td>
                    <td className="px-4 py-2.5 text-muted whitespace-nowrap">
                      {formatModel(ev.model_used)}
                    </td>
                    <td className="px-4 py-2.5">
                      {ev.cache_hit ? (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 text-[10px] font-medium">
                          {ev.cache_type ?? 'hit'}
                        </span>
                      ) : (
                        <span className="text-muted">miss</span>
                      )}
                    </td>
                    <td className="px-4 py-2.5 text-muted tabular-nums">
                      {(ev.timings_ms?.total ?? 0).toFixed(0)} ms
                    </td>
                    <td className="px-4 py-2.5 text-muted tabular-nums">
                      ${ev.estimated_cost_usd?.toFixed(6) ?? '0.000000'}
                    </td>
                    <td className="px-4 py-2.5">
                      <ConfidenceBadge
                        confidence={ev.hallucination_confidence}
                      />
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

// ── Sub-components ───────────────────────────────────────────────────────────

function SummaryCard({
  icon,
  label,
  value,
  sub,
  accent,
}: {
  icon: React.ReactNode
  label: string
  value: string
  sub: string
  accent: string
}) {
  return (
    <div className="bg-surface border border-border rounded-xl p-4 flex flex-col gap-3 hover:border-border/80 transition-colors">
      <div className="flex items-center gap-2.5">
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center"
          style={{ backgroundColor: `${accent}15`, color: accent }}
        >
          {icon}
        </div>
        <span className="text-xs text-muted font-medium">{label}</span>
      </div>
      <div>
        <p className="text-xl font-bold text-text tabular-nums">{value}</p>
        <p className="text-[11px] text-muted mt-0.5">{sub}</p>
      </div>
    </div>
  )
}

function CategoryBadge({ category }: { category: string }) {
  const colorMap: Record<string, string> = {
    GREETING: 'bg-indigo-500/10 text-indigo-400',
    LEGAL_SIMPLE: 'bg-blue-500/10 text-blue-400',
    LEGAL_COMPLEX: 'bg-violet-500/10 text-violet-400',
    UNSAFE: 'bg-red-500/10 text-red-400',
    OUT_OF_DOMAIN: 'bg-orange-500/10 text-orange-400',
  }
  const cls = colorMap[category] ?? 'bg-gray-500/10 text-gray-400'
  return (
    <span
      className={`inline-flex px-2 py-0.5 rounded-full text-[10px] font-medium whitespace-nowrap ${cls}`}
    >
      {category}
    </span>
  )
}

function ConfidenceBadge({ confidence }: { confidence: string }) {
  const colorMap: Record<string, string> = {
    high: 'bg-emerald-500/10 text-emerald-400',
    medium: 'bg-amber-500/10 text-amber-400',
    low: 'bg-red-500/10 text-red-400',
  }
  const cls = colorMap[confidence?.toLowerCase()] ?? 'bg-gray-500/10 text-gray-400'
  return (
    <span
      className={`inline-flex px-2 py-0.5 rounded-full text-[10px] font-medium ${cls}`}
    >
      {confidence}
    </span>
  )
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function formatTime(iso: string): string {
  try {
    const d = new Date(iso)
    return d.toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    })
  } catch {
    return iso
  }
}

function formatModel(model: string): string {
  if (!model) return 'n/a'
  // Shorten "openai/gpt-oss-20b" → "gpt-oss-20b"
  return model.replace('openai/', '')
}
