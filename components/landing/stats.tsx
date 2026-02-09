const stats = [
  { value: "8", label: "Due Diligence Pillars" },
  { value: "50+", label: "KPIs Tracked" },
  { value: "< 5 min", label: "To First Score" },
  { value: "AI", label: "Powered Insights" },
]

export function Stats() {
  return (
    <section className="border-t border-border px-6 py-16">
      <div className="mx-auto grid max-w-5xl grid-cols-2 gap-6 lg:grid-cols-4">
        {stats.map((stat) => (
          <div key={stat.label} className="text-center">
            <div className="text-3xl font-bold text-foreground lg:text-4xl">
              {stat.value}
            </div>
            <div className="mt-1 text-sm text-muted-foreground">
              {stat.label}
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
