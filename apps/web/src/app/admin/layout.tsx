export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <div>
      <div
        style={{
          padding: "8px 16px",
          background: "#1a1a1a",
          borderBottom: "1px solid #333",
          fontSize: "12px",
          color: "#888",
          letterSpacing: "0.05em",
        }}
      >
        ADMIN
      </div>
      {children}
    </div>
  );
}
