type Props = {
  title: string;
  body: string;
};

export function DataState({ title, body }: Props) {
  return (
    <div className="rounded-xl border border-dashed border-outline-variant bg-surface-container/80 p-6 text-on-surface-variant">
      <h2 className="font-headline text-lg font-semibold text-on-surface">{title}</h2>
      <p className="mt-2 max-w-2xl text-sm leading-6 text-on-surface-variant">{body}</p>
    </div>
  );
}
