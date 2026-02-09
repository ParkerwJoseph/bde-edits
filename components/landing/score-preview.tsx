const pillars = [
  { name: "Revenue", score: 82, color: "hsl(var(--chart-1))" },
  { name: "Profitability", score: 71, color: "hsl(var(--chart-2))" },
  { name: "Growth", score: 88, color: "hsl(var(--chart-1))" },
  { name: "Customer", score: 65, color: "hsl(var(--chart-3))" },
  { name: "Market", score: 74, color: "hsl(var(--chart-2))" },
  { name: "Team", score: 79, color: "hsl(var(--chart-1))" },
  { name: "Operations", score: 62, color: "hsl(var(--chart-3))" },
  { name: "Legal", score: 90, color: "hsl(var(--chart-1))" },
]

function ScoreRing({ score, size = 120 }: { score: number; size?: number }) {
  const radius = (size - 12) / 2
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (score / 100) * circumference

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="hsl(var(--border))"
          strokeWidth="6"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="hsl(var(--primary))"
          strokeWidth="6"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className="transition-all duration-1000"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-3xl font-bold text-foreground">{score}</span>
        <span className="text-xs text-muted-foreground">/ 100</span>
      </div>
    </div>
  )
}

function PillarBar({ name, score, color }: { name: string; score: number; color: string }) {
  return (
    <div className="flex items-center gap-3">
      <span className="w-24 shrink-0 text-right text-sm text-muted-foreground">{name}</span>
      <div className="relative h-2 flex-1 overflow-hidden rounded-full bg-border">
        <div
          className="absolute left-0 top-0 h-full rounded-full transition-all duration-1000"
          style={{ width: `${score}%`, backgroundColor: color }}
        />
      </div>
      <span className="w-8 text-right text-sm font-medium text-foreground">{score}</span>
    </div>
  )
}

export function ScorePreview() {
  return (
    <section className="border-t border-border px-6 py-20">
      <div className="mx-auto max-w-5xl">
        <div className="overflow-hidden rounded-2xl border border-border bg-card">
          {/* Mock Dashboard Header */}
          <div className="flex items-center gap-2 border-b border-border px-6 py-3">
            <div className="h-3 w-3 rounded-full bg-destructive/60" />
            <div className="h-3 w-3 rounded-full bg-chart-3/60" />
            <div className="h-3 w-3 rounded-full bg-primary/60" />
            <span className="ml-4 text-xs text-muted-foreground">
              BDE Dashboard - Exit Readiness Overview
            </span>
          </div>

          {/* Mock Dashboard Content */}
          <div className="p-6 lg:p-10">
            <div className="flex flex-col items-center gap-10 lg:flex-row lg:items-start lg:gap-16">
              {/* Score Ring */}
              <div className="flex flex-col items-center gap-3">
                <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Exit Readiness Score
                </span>
                <ScoreRing score={76} size={140} />
                <div className="mt-1 inline-flex items-center gap-1.5 rounded-full bg-primary/10 px-3 py-1">
                  <span className="h-1.5 w-1.5 rounded-full bg-primary" />
                  <span className="text-xs font-medium text-primary">
                    Strong
                  </span>
                </div>
              </div>

              {/* Pillar Bars */}
              <div className="flex-1 space-y-3">
                <span className="mb-4 block text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  8-Pillar Breakdown
                </span>
                {pillars.map((p) => (
                  <PillarBar key={p.name} {...p} />
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
