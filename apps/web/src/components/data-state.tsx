type Props = {
  title: string;
  body: string;
};

export function DataState({ title, body }: Props) {
  return (
    <div className="editorial-panel border-dashed p-6 md:p-7">
      <div className="relative max-w-2xl">
        <p className="font-label text-[10px] font-semibold uppercase tracking-[0.24em] text-primary">
          Data state
        </p>
        <h1 className="mt-3 font-headline text-2xl font-semibold uppercase tracking-[-0.03em] text-on-surface">
          {title}
        </h1>
        <p className="mt-3 text-sm leading-7 text-on-surface-variant">{body}</p>
      </div>
    </div>
  );
}
