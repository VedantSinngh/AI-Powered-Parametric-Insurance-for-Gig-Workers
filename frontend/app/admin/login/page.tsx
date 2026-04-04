"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Loader2, Mail, ShieldCheck } from "lucide-react";
import { ApiError, apiGet, apiPost } from "@/lib/api";

type AdminRequestOtpResponse = {
  otp_session_id: string;
  message: string;
};

type VerifyOtpResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  partner_id: string;
  wallet_balance: number;
};

type AuthMeResponse = {
  partner: {
    is_admin: boolean;
    full_name: string;
  };
};

export default function AdminLoginPage() {
  const router = useRouter();
  const [step, setStep] = useState<"email" | "otp">("email");
  const [email, setEmail] = useState("vedaantsinngh@gmail.com");
  const [otpSessionId, setOtpSessionId] = useState("");
  const [otpCode, setOtpCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  const otpComplete = useMemo(() => otpCode.trim().length === 6, [otpCode]);

  const requestOtp = async () => {
    try {
      setLoading(true);
      setErrorMessage("");
      setSuccessMessage("");

      const response = await apiPost<AdminRequestOtpResponse>("/auth/admin/request-otp", {
        email: email.trim().toLowerCase(),
      });

      setOtpSessionId(response.otp_session_id);
      setStep("otp");
      setSuccessMessage("OTP sent. Enter the 6-digit code from your email.");
    } catch (error) {
      if (error instanceof ApiError) {
        setErrorMessage(error.message);
      } else {
        setErrorMessage("Unable to start admin sign-in right now.");
      }
    } finally {
      setLoading(false);
    }
  };

  const verifyOtp = async () => {
    try {
      setLoading(true);
      setErrorMessage("");
      setSuccessMessage("");

      const verifyResponse = await apiPost<VerifyOtpResponse>("/auth/admin/verify-otp", {
        otp_session_id: otpSessionId,
        otp_code: otpCode.trim(),
      });

      const accessToken = verifyResponse.access_token;
      localStorage.setItem("gridguard_access_token", accessToken);
      localStorage.setItem("gridguard_refresh_token", verifyResponse.refresh_token);
      localStorage.setItem("gridguard_partner_id", verifyResponse.partner_id);
      localStorage.setItem("gridguard_wallet_balance", String(verifyResponse.wallet_balance));

      const me = await apiGet<AuthMeResponse>("/auth/me", accessToken);
      if (!me.partner.is_admin) {
        localStorage.removeItem("gridguard_access_token");
        localStorage.removeItem("gridguard_refresh_token");
        localStorage.removeItem("gridguard_partner_id");
        localStorage.removeItem("gridguard_wallet_balance");
        throw new ApiError("This account does not have admin privileges.", 403);
      }

      setSuccessMessage(`Welcome, ${me.partner.full_name}. Redirecting...`);
      window.setTimeout(() => router.push("/overview"), 400);
    } catch (error) {
      if (error instanceof ApiError) {
        setErrorMessage(error.message);
      } else {
        setErrorMessage("OTP verification failed. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_left,_#1a2e45_0%,_#111f31_50%,_#0b1523_100%)] text-white flex items-center justify-center p-6">
      <div className="w-full max-w-md rounded-3xl border border-white/15 bg-white/10 backdrop-blur-xl p-7 shadow-[0_20px_80px_rgba(0,0,0,0.35)]">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-sky-400/20 border border-sky-300/30 flex items-center justify-center">
            <ShieldCheck className="h-5 w-5 text-sky-200" />
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.18em] text-sky-200">Operations Access</p>
            <h1 className="text-2xl font-extrabold leading-tight">Admin Sign-In</h1>
          </div>
        </div>

        <p className="mt-4 text-sm text-white/70">
          This login is separate from rider onboarding and is limited to approved admin emails.
        </p>

        {step === "email" ? (
          <div className="mt-6 space-y-4">
            <label className="block text-sm text-white/80">
              Admin email
              <div className="mt-2 relative">
                <Mail className="h-4 w-4 text-white/60 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="admin@gridguard.ai"
                  className="w-full h-11 rounded-xl bg-white/10 border border-white/20 pl-10 pr-3 text-sm outline-none focus:border-sky-300"
                />
              </div>
            </label>

            <button
              type="button"
              disabled={loading || !email.trim()}
              onClick={requestOtp}
              className="w-full h-11 rounded-xl bg-sky-400 text-slate-950 font-bold hover:bg-sky-300 disabled:opacity-60 inline-flex items-center justify-center gap-2"
            >
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              Send Admin OTP
            </button>
          </div>
        ) : (
          <div className="mt-6 space-y-4">
            <label className="block text-sm text-white/80">
              OTP code
              <input
                type="text"
                value={otpCode}
                onChange={(event) => setOtpCode(event.target.value.replace(/\D/g, "").slice(0, 6))}
                placeholder="123456"
                className="mt-2 w-full h-11 rounded-xl bg-white/10 border border-white/20 px-3 text-sm tracking-[0.25em] font-semibold outline-none focus:border-sky-300"
              />
            </label>

            <button
              type="button"
              disabled={loading || !otpComplete}
              onClick={verifyOtp}
              className="w-full h-11 rounded-xl bg-emerald-400 text-slate-950 font-bold hover:bg-emerald-300 disabled:opacity-60 inline-flex items-center justify-center gap-2"
            >
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              Verify and Enter Console
            </button>

            <button
              type="button"
              disabled={loading}
              onClick={() => {
                setStep("email");
                setOtpCode("");
                setErrorMessage("");
                setSuccessMessage("");
              }}
              className="w-full h-10 rounded-xl border border-white/20 text-white/80 text-sm hover:bg-white/10"
            >
              Use different email
            </button>
          </div>
        )}

        {errorMessage ? (
          <p className="mt-4 text-sm text-rose-300">{errorMessage}</p>
        ) : null}
        {successMessage ? (
          <p className="mt-4 text-sm text-emerald-200">{successMessage}</p>
        ) : null}

        <div className="mt-6 flex items-center justify-between text-xs text-white/70">
          <Link href="/admin" className="hover:text-white">Back to operations gateway</Link>
          <Link href="/login" className="hover:text-white">Rider onboarding</Link>
        </div>
      </div>
    </main>
  );
}