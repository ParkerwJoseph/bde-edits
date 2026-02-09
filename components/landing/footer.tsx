export function Footer() {
  return (
    <footer className="border-t border-border px-6 py-10">
      <div className="mx-auto flex max-w-5xl flex-col items-center justify-between gap-4 sm:flex-row">
        <div className="flex items-center gap-3">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary">
            <span className="text-[10px] font-bold text-primary-foreground">B</span>
          </div>
          <span className="text-sm font-medium text-foreground">
            Business Due Diligence Engine
          </span>
        </div>
        <p className="text-sm text-muted-foreground">
          AI-powered exit readiness analysis
        </p>
      </div>
    </footer>
  )
}
