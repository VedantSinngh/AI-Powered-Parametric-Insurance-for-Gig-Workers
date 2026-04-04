import Link from "next/link";

const ADMIN_MODULES = [
  {
    title: "Overview",
    subtitle: "Portfolio KPIs, risk posture, and active disruption summary.",
    href: "/overview",
  },
  {
    title: "Support Console",
    subtitle: "Partner lookup and incident triage workflow.",
    href: "/support",
  },
  {
    title: "Finance Reconciliation",
    subtitle: "Provider statuses, payout queue, and failure reasons.",
    href: "/finance",
  },
  {
    title: "Audit Trail",
    subtitle: "Immutable chronology of payouts and fraud decisions.",
    href: "/audit",
  },
];

export default function AdminGatewayPage() {
  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_left,_#1a2e45_0%,_#111f31_50%,_#0b1523_100%)] text-white">
      <div className="max-w-5xl mx-auto px-6 py-16">
        <p className="text-xs uppercase tracking-[0.18em] text-sky-300">GridGuard Operations</p>
        <h1 className="mt-4 text-4xl md:text-5xl font-extrabold leading-tight">
          Separate gateway for admin, support, finance, and audit teams.
        </h1>
        <p className="mt-4 text-white/70 max-w-3xl">
          This portal is intentionally isolated from the rider onboarding funnel. Use an approved
          admin account to access operational consoles.
        </p>

        <div className="mt-8 flex flex-wrap gap-3">
          <Link href="/admin/login" className="h-11 px-5 inline-flex items-center rounded-xl bg-sky-500 text-slate-950 font-bold hover:bg-sky-400">
            Continue to Admin Sign-In
          </Link>
          <Link href="/" className="h-11 px-5 inline-flex items-center rounded-xl border border-white/20 bg-white/10 font-semibold hover:bg-white/20">
            Back to Rider Landing
          </Link>
        </div>

        <section className="mt-10 grid grid-cols-1 md:grid-cols-2 gap-4">
          {ADMIN_MODULES.map((item) => (
            <Link
              key={item.title}
              href={item.href}
              className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-md p-5 hover:border-white/30 transition"
            >
              <h2 className="text-lg font-bold">{item.title}</h2>
              <p className="text-sm text-white/70 mt-2">{item.subtitle}</p>
              <p className="text-sm text-sky-200 mt-4 font-semibold">Open module →</p>
            </Link>
          ))}
        </section>
      </div>
    </main>
  );
}
