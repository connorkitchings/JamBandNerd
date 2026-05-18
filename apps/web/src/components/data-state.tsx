type Props = {
  title: string;
  body: string;
  headingLevel?: "h1" | "h2";
};

export function DataState({ title, body, headingLevel = "h1" }: Props) {
  const Heading = headingLevel;

  return (
    <div className="editorial-panel border-dashed p-6 md:p-7">
      <div className="relative max-w-2xl">
        <p className="font-label text-[10px] font-semibold uppercase tracking-[0.24em] text-primary">
          Data state
        </p>
        <Heading className="mt-3 font-headline text-2xl font-semibold uppercase tracking-[-0.03em] text-on-surface">
          {title}
        </Heading>
        <p className="mt-3 text-sm leading-7 text-on-surface-variant">{body}</p>
      </div>
    </div>
  );
}
