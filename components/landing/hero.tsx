import { ArrowRight } from "lucide-react"

export function Hero() {
  return (
    <section className="relative px-6 pb-20 pt-24 lg:pt-32">
      <div className="mx-auto max-w-5xl text-center">
        <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-border bg-secondary px-4 py-1.5">
          <span className="h-1.5 w-1.5 rounded-full bg-primary" />
          <span className="text-sm font-medium text-muted-foreground">
            AI-Powered Due Diligence Platform
          </span>
        </div>

        <h1 className="mx-auto max-w-4xl text-balance text-4xl font-bold tracking-tight text-foreground sm:text-5xl lg:text-7xl">
          Know your exit readiness before the buyer does
        </h1>

        <p className="mx-auto mt-6 max-w-2xl text-pretty text-lg leading-relaxed text-muted-foreground">
          Comprehensive AI-driven analysis across 8 key pillars of business
          value. Upload documents, connect data sources, and get actionable
          insights to maximize your exit potential.
        </p>

        <div className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
          <a
            href="/dashboard"
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-6 py-3 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary/90"
          >
            Open Dashboard
            <ArrowRight className="h-4 w-4" />
          </a>
          <a
            href="#features"
            className="inline-flex items-center gap-2 rounded-lg border border-border bg-secondary px-6 py-3 text-sm font-semibold text-secondary-foreground transition-colors hover:bg-border"
          >
            Explore Features
          </a>
        </div>
      </div>
    </section>
  )
}
