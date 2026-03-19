export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen" style={{
      background: "radial-gradient(ellipse at 20% 50%, #2A5A8E 0%, #1A3C5E 60%, #0F2238 100%)",
    }}>
      {children}
    </div>
  );
}
