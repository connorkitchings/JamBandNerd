export default function Loading() {
  return (
    <div className="mx-auto max-w-6xl space-y-6" aria-live="polite" aria-busy="true">
      <section className="editorial-panel animate-pulse px-6 py-8 md:px-8 md:py-10">
        <div className="h-3 w-32 rounded-full bg-primary/20" />
        <div className="mt-6 h-10 max-w-xl rounded-xl bg-surface-container-high/70" />
        <div className="mt-4 h-4 max-w-2xl rounded-full bg-surface-container-high/55" />
        <div className="mt-3 h-4 max-w-lg rounded-full bg-surface-container-high/45" />
      </section>
      <section className="grid gap-4 md:grid-cols-3">
        {[0, 1, 2].map((item) => (
          <div
            className="editorial-panel h-32 animate-pulse rounded-[1.35rem] bg-surface-container-low"
            key={item}
          />
        ))}
      </section>
    </div>
  );
}
