import { ArrowRight } from "lucide-react"

export function Header() {
  return (
    <header className="sticky top-0 z-50 border-b border-border bg-background/80 backdrop-blur-md">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
            <span className="text-xs font-bold text-primary-foreground">B</span>
          </div>
          <span className="text-base font-semibold text-foreground">BDE</span>
        </div>

        <nav className="hidden items-center gap-8 md:flex">
          <a
            href="#features"
            className="text-sm text-muted-foreground transition-colors hover:text-foreground"
          >
            Features
          </a>
          <a
            href="#preview"
            className="text-sm text-muted-foreground transition-colors hover:text-foreground"
          >
            Platform
          </a>
        </nav>

        <a
          href="/dashboard"
          className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
        >
          Dashboard
          <ArrowRight className="h-3.5 w-3.5" />
        </a>
      </div>
    </header>
  )
}
