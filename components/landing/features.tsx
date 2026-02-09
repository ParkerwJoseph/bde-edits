import {
  BarChart3,
  Shield,
  TrendingUp,
  FileText,
  Brain,
  Target,
} from "lucide-react"

const features = [
  {
    icon: Shield,
    title: "Exit Readiness Score",
    description:
      "Real-time scoring across 8 key pillars to assess business value and exit preparedness.",
  },
  {
    icon: BarChart3,
    title: "Analytics Dashboard",
    description:
      "Deep-dive analytics with signal maps, trend analysis, and customizable card grids.",
  },
  {
    icon: Brain,
    title: "AI Analyst Copilot",
    description:
      "Ask questions about your business data and get AI-powered insights with source citations.",
  },
  {
    icon: FileText,
    title: "Document Ingestion",
    description:
      "Upload financial statements, contracts, and more. AI processes and extracts key data points.",
  },
  {
    icon: TrendingUp,
    title: "Valuation Multiples",
    description:
      "Track what moves your valuation multiple with actionable improvement recommendations.",
  },
  {
    icon: Target,
    title: "Risk Identification",
    description:
      "Surface top exit risks early so you can remediate issues before they impact deal value.",
  },
]

export function Features() {
  return (
    <section id="features" className="border-t border-border px-6 py-20">
      <div className="mx-auto max-w-5xl">
        <div className="mb-12 text-center">
          <h2 className="text-2xl font-bold text-foreground sm:text-3xl">
            Platform Capabilities
          </h2>
          <p className="mt-3 text-muted-foreground">
            Everything you need to assess, analyze, and accelerate exit
            readiness.
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {features.map((feature) => (
            <div
              key={feature.title}
              className="group rounded-xl border border-border bg-card p-6 transition-colors hover:border-primary/30"
            >
              <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                <feature.icon className="h-5 w-5 text-primary" />
              </div>
              <h3 className="mb-2 text-base font-semibold text-card-foreground">
                {feature.title}
              </h3>
              <p className="text-sm leading-relaxed text-muted-foreground">
                {feature.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
