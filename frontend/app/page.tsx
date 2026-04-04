"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { Shield, Zap, Wallet, ArrowRight, Activity, Map, Clock } from "lucide-react";

const RIDER_HIGHLIGHTS = [
  {
    icon: <Map className="w-5 h-5 text-amber-400" />,
    title: "Live Workability Zones",
    subtitle: "See risk conditions by hex-zone before starting your shift.",
  },
  {
    icon: <Zap className="w-5 h-5 text-blue-400" />,
    title: "Automatic Protection",
    subtitle: "Parametric payouts are triggered when disruption thresholds are crossed.",
  },
  {
    icon: <Wallet className="w-5 h-5 text-emerald-400" />,
    title: "Transparent Wallet",
    subtitle: "Track premium, payout source, and withdrawal status in one view.",
  },
];

export default function Home() {
  return (
    <main className="min-h-screen bg-[#060c14] text-white overflow-hidden relative selection:bg-amber-500/30">
      {/* Background Effects */}
      <div className="absolute inset-0 z-0 overflow-hidden pointer-events-none">
        <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-blue-900/20 blur-[120px] rounded-full mix-blend-screen" />
        <div className="absolute bottom-[-20%] right-[-10%] w-[60%] h-[60%] bg-amber-900/10 blur-[150px] rounded-full mix-blend-screen" />
        <div className="absolute top-[20%] right-[10%] w-[30%] h-[30%] bg-emerald-900/10 blur-[100px] rounded-full mix-blend-screen" />
        <div className="absolute inset-0 opacity-25 [background-image:radial-gradient(rgba(255,255,255,0.08)_1px,transparent_1px)] [background-size:3px_3px]"></div>
      </div>

      <div className="relative z-10 max-w-7xl mx-auto px-6 py-8 md:py-12 flex flex-col min-h-screen">
        {/* Navigation / Header */}
        <motion.nav 
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: "easeOut" }}
          className="flex items-center justify-between mb-16 md:mb-24 backdrop-blur-md bg-white/5 border border-white/10 rounded-2xl px-6 py-4"
        >
          <div className="flex items-center gap-2">
            <Shield className="w-6 h-6 text-amber-400" />
            <p className="font-bold tracking-widest uppercase text-sm">GridGuard</p>
          </div>
          <div className="flex items-center gap-6">
            <Link href="/admin" className="text-xs font-semibold uppercase tracking-[0.16em] text-white/60 hover:text-amber-400 transition-colors flex items-center gap-2">
              <Activity className="w-4 h-4" />
              <span className="hidden sm:inline">Operations Gateway</span>
            </Link>
          </div>
        </motion.nav>

        {/* Hero Content */}
        <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-8 items-center">
          <motion.div 
            initial={{ opacity: 0, x: -30 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
            className="lg:col-span-7 flex flex-col justify-center"
          >
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/5 border border-white/10 w-fit mb-6">
              <span className="animate-pulse w-2 h-2 rounded-full bg-emerald-400"></span>
              <span className="text-xs font-medium text-emerald-400 uppercase tracking-wider">Live & Active</span>
            </div>

            <h1 className="text-5xl md:text-7xl font-extrabold leading-[1.1] tracking-tight mb-6">
              Insurance that moves at <span className="text-transparent bg-clip-text bg-gradient-to-r from-amber-200 to-amber-500">rider speed.</span>
            </h1>
            
            <p className="text-white/60 text-lg md:text-xl leading-relaxed max-w-2xl mb-10 font-light">
              Protect your earnings during rain, heat, AQI spikes, and platform downtime with a
              real-time parametric safety net built exclusively for gig workers.
            </p>

            <div className="flex flex-col sm:flex-row gap-4">
              <Link href="/login" className="group h-14 px-8 inline-flex items-center justify-center gap-2 rounded-2xl bg-amber-500 text-slate-900 font-bold hover:bg-amber-400 transition-all shadow-[0_0_40px_-10px_rgba(245,158,11,0.4)] hover:shadow-[0_0_60px_-10px_rgba(245,158,11,0.6)]">
                Start Rider Onboarding
                <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </Link>
              <Link href="/dashboard" className="h-14 px-8 inline-flex items-center justify-center rounded-2xl border border-white/10 bg-white/5 font-semibold hover:bg-white/10 transition-colors backdrop-blur-md">
                Open Rider Demo
              </Link>
            </div>

            {/* Stats Row */}
            <div className="mt-16 grid grid-cols-2 md:grid-cols-3 gap-6 pt-8 border-t border-white/10">
              <div>
                <p className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-white/60">&lt; 90s</p>
                <p className="text-sm text-white/50 mt-1 uppercase tracking-wider font-medium">Payout Target</p>
              </div>
              <div>
                <p className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-white/60">7 Cities</p>
                <p className="text-sm text-white/50 mt-1 uppercase tracking-wider font-medium">Coverage Scope</p>
              </div>
              <div className="hidden md:block">
                <p className="text-3xl font-bold flex items-center gap-2">
                  <Clock className="w-6 h-6 text-amber-500" />
                  <span className="bg-clip-text text-transparent bg-gradient-to-r from-white to-white/60">24/7</span>
                </p>
                <p className="text-sm text-white/50 mt-1 uppercase tracking-wider font-medium">Protection</p>
              </div>
            </div>
          </motion.div>

          <motion.div 
            initial={{ opacity: 0, scale: 0.95, y: 30 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.4 }}
            className="lg:col-span-5"
          >
            <div className="relative rounded-3xl border border-white/10 bg-white/[0.03] backdrop-blur-xl p-8 shadow-2xl overflow-hidden">
              {/* Card internal glow */}
              <div className="absolute top-0 right-0 w-64 h-64 bg-amber-500/10 blur-[80px] rounded-full pointer-events-none" />
              
              <div className="relative z-10">
                <p className="text-xs uppercase tracking-widest text-amber-400 font-bold mb-8">Why Riders Trust GridGuard</p>
                
                <div className="space-y-4">
                  {RIDER_HIGHLIGHTS.map((item, idx) => (
                    <motion.div 
                      key={item.title} 
                      initial={{ opacity: 0, x: 20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ duration: 0.5, delay: 0.6 + idx * 0.1 }}
                      className="group rounded-2xl border border-white/5 bg-white/[0.02] p-5 hover:bg-white/[0.04] transition-colors"
                    >
                      <div className="flex gap-4">
                        <div className="mt-1 p-2 bg-white/5 rounded-xl h-fit border border-white/10 flex-shrink-0 group-hover:scale-110 transition-transform">
                          {item.icon}
                        </div>
                        <div>
                          <h2 className="font-bold text-white tracking-wide text-lg">{item.title}</h2>
                          <p className="text-sm text-white/60 mt-2 leading-relaxed">{item.subtitle}</p>
                        </div>
                      </div>
                    </motion.div>
                  ))}
                </div>

                <div className="mt-8 rounded-2xl border border-amber-500/20 bg-amber-500/5 p-5 flex gap-4 items-start">
                  <Shield className="w-5 h-5 text-amber-500/70 flex-shrink-0 mt-0.5" />
                  <p className="text-sm text-amber-200/70 leading-relaxed font-medium">
                    Admin, support, finance, and audit workflows are securely managed via the operations gateway.
                  </p>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </main>
  );
}
