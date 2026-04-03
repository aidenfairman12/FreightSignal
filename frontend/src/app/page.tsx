"use client";

import Link from "next/link";

export default function LandingPage() {
  return (
    <main className="min-h-screen bg-gray-950 text-white flex flex-col">
      {/* Hero */}
      <section className="flex-1 flex flex-col items-center justify-center px-6 py-24 text-center">
        <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-4 py-1.5 text-sm text-emerald-400">
          <span className="inline-block h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
          Live corpus · updated every 6 hours
        </div>

        <h1 className="max-w-3xl text-5xl font-bold tracking-tight text-white sm:text-6xl">
          Supply chain intelligence,{" "}
          <span className="text-emerald-400">grounded in real news</span>
        </h1>

        <p className="mt-6 max-w-2xl text-lg text-gray-400 leading-relaxed">
          FreightSignal monitors live logistics and trade news and answers your
          questions about disruptions — citing the exact sources it used.
          Built on open-source retrieval-augmented generation with rigorous
          evaluation.
        </p>

        <div className="mt-10 flex flex-wrap gap-4 justify-center">
          <Link
            href="/search"
            className="rounded-lg bg-emerald-500 px-8 py-3.5 text-base font-semibold text-gray-950 hover:bg-emerald-400 transition-colors"
          >
            Ask a question
          </Link>
          <Link
            href="/about"
            className="rounded-lg border border-gray-700 px-8 py-3.5 text-base font-semibold text-gray-300 hover:border-gray-500 hover:text-white transition-colors"
          >
            How it works
          </Link>
        </div>
      </section>

      {/* Feature strip */}
      <section className="border-t border-gray-800 bg-gray-900/50">
        <div className="mx-auto max-w-5xl grid grid-cols-1 sm:grid-cols-3 divide-y sm:divide-y-0 sm:divide-x divide-gray-800">
          {[
            {
              icon: "📡",
              title: "Live corpus",
              body: "FreightWaves, Supply Chain Dive, Journal of Commerce, and more — refreshed every 6 hours.",
            },
            {
              icon: "🔍",
              title: "Source-attributed answers",
              body: "Every answer shows the exact article chunks retrieved — so you can verify the reasoning yourself.",
            },
            {
              icon: "📊",
              title: "Measured, not just vibed",
              body: "RAGAS evaluation scores (faithfulness, context precision, recall) are public and updated with each model change.",
            },
          ].map(({ icon, title, body }) => (
            <div key={title} className="flex flex-col gap-2 px-8 py-10">
              <span className="text-3xl">{icon}</span>
              <h3 className="text-base font-semibold text-white">{title}</h3>
              <p className="text-sm text-gray-400 leading-relaxed">{body}</p>
            </div>
          ))}
        </div>
      </section>

      <footer className="border-t border-gray-800 py-6 text-center text-xs text-gray-600">
        FreightSignal · Built with{" "}
        <a href="https://huggingface.co/BAAI/bge-small-en-v1.5" className="underline hover:text-gray-400">BGE</a>
        {" · "}
        <a href="https://groq.com" className="underline hover:text-gray-400">Groq Llama 3.3 70B</a>
        {" · "}
        <a href="https://docs.ragas.io" className="underline hover:text-gray-400">RAGAS</a>
      </footer>
    </main>
  );
}
