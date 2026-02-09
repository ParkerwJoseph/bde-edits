import { Header } from "@/components/landing/header"
import { Hero } from "@/components/landing/hero"
import { Stats } from "@/components/landing/stats"
import { ScorePreview } from "@/components/landing/score-preview"
import { Features } from "@/components/landing/features"
import { Footer } from "@/components/landing/footer"

export default function Home() {
  return (
    <main className="min-h-screen bg-background font-sans">
      <Header />
      <Hero />
      <Stats />
      <ScorePreview />
      <Features />
      <Footer />
    </main>
  )
}
