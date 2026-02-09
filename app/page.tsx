import { BarChart3, Shield, TrendingUp, FileText, Brain, ArrowRight } from "lucide-react"

const features = [
  {
    icon: Shield,
    title: "Exit Readiness Score",
    description: "Real-time scoring across 8 key pillars to assess business value and exit preparedness.",
  },
  {
    icon: BarChart3,
    title: "Analytics Dashboard",
    description: "Deep-dive analytics with signal maps, trend analysis, and customizable card grids.",
  },
  {
    icon: Brain,
    title: "AI Analyst Copilot",
    description: "Ask questions about your business data and get AI-powered insights with source citations.",
  },
  {
    icon: FileText,
    title: "Document Ingestion",
    description: "Upload financial statements, contracts, and more. AI processes and extracts key data points.",
  },
  {
    icon: TrendingUp,
    title: "Valuation Multiples",
    description: "Track what moves your valuation multiple with actionable improvement recommendations.",
  },
]

export default function Home() {
  return (
    <main className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary">
              <span className="text-sm font-bold text-primary-foreground">BDE</span>
            </div>
            <span className="text-lg font-semibold text-foreground">Business Due Diligence Engine</span>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="mx-auto max-w-6xl px-6 py-20">
        <div className="flex flex-col items-center text-center">
          <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-border bg-muted px-4 py-1.5 text-sm text-muted-foreground">
            <span>AI-Powered Due Diligence</span>
          </div>
          <h1 className="max-w-3xl text-balance text-4xl font-bold tracking-tight text-foreground sm:text-5xl lg:text-6xl">
            Know Your Business Exit Readiness
          </h1>
          <p className="mt-6 max-w-2xl text-pretty text-lg leading-relaxed text-muted-foreground">
            Comprehensive AI-driven analysis across 8 key pillars of business value. 
            Upload your documents, connect your data sources, and get actionable insights 
            to maximize your exit potential.
          </p>
          <div className="mt-10 flex items-center gap-4">
            <a
              href="/dashboard"
              className="inline-flex items-center gap-2 rounded-lg bg-primary px-6 py-3 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
            >
              Go to Dashboard
              <ArrowRight className="h-4 w-4" />
            </a>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="border-t border-border bg-muted/50 py-20">
        <div className="mx-auto max-w-6xl px-6">
          <h2 className="mb-12 text-center text-2xl font-semibold text-foreground">
            Platform Capabilities
          </h2>
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {features.map((feature) => (
              <div
                key={feature.title}
                className="rounded-xl border border-border bg-card p-6 transition-shadow hover:shadow-md"
              >
                <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                  <feature.icon className="h-5 w-5 text-primary" />
                </div>
                <h3 className="mb-2 text-base font-semibold text-card-foreground">{feature.title}</h3>
                <p className="text-sm leading-relaxed text-muted-foreground">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border py-8">
        <div className="mx-auto max-w-6xl px-6 text-center text-sm text-muted-foreground">
          BDE - Business Due Diligence Engine
        </div>
      </footer>
    </main>
  )
}
