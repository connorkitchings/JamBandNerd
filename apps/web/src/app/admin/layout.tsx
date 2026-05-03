import { getBands } from "@/lib/data";

function serializeScriptJson(value: unknown): string {
  return JSON.stringify(value).replace(/</g, "\\u003c");
}

export default async function AdminLayout({ children }: { children: React.ReactNode }) {
  const bandsResult = await getBands();
  const bands = bandsResult.status === "ready" ? bandsResult.bands : [];

  return (
    <div>
      <div className="px-4 py-2 bg-surface border-b border-outline-variant text-xs tracking-widest text-on-surface-variant">
        ADMIN
      </div>
      {bands.length > 0 ? (
        <script
          id="admin-bands"
          type="application/json"
          dangerouslySetInnerHTML={{
            __html: serializeScriptJson(bands),
          }}
        />
      ) : null}
      {children}
    </div>
  );
}
