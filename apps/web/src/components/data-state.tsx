type Props = {
  title: string;
  body: string;
  headingLevel?: "h1" | "h2";
};

// Default to h1 for full-page states; embedded states must opt down to h2.
export function DataState({ title, body, headingLevel = "h1" }: Props) {
  const Heading = headingLevel;

  return (
    <div className="editorial-panel border-dashed p-5 md:p-6">
      <div className="relative max-w-2xl">
        <p className="text-xs font-bold uppercase tracking-[0.08em] text-accent-text">
          Data state
        </p>
        <Heading className="mt-2 text-xl font-bold text-on-surface">{title}</Heading>
        <p className="mt-2 text-sm text-on-surface-variant">{body}</p>
      </div>
    </div>
  );
}
