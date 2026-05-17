export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <div>
      <div className="mx-auto mb-6 max-w-6xl rounded-b-[1.35rem] border-x border-b border-outline-variant/25 bg-surface-container px-5 py-3 text-center font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">
        Admin
      </div>
      {children}
    </div>
  );
}
