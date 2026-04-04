"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { motion, useAnimation } from "framer-motion";
import { Mail } from "lucide-react";
import { ApiError, apiPost } from "@/lib/api";

type VerifyOtpResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  partner_id: string;
  wallet_balance: number;
};

export default function VerifyPage() {
  const router = useRouter();
  const [otp, setOtp] = useState(["", "", "", "", "", ""]);
  const [error, setError] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [success, setSuccess] = useState(false);
  const [countdown, setCountdown] = useState(300); // 5 minutes
  const [loading, setLoading] = useState(false);
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);
  const shakeControls = useAnimation();

  const email = typeof window !== "undefined"
    ? sessionStorage.getItem("gridguard_email") || "rider@example.com"
    : "rider@example.com";

  const otpSessionId = typeof window !== "undefined"
    ? sessionStorage.getItem("gridguard_otp_session_id") || ""
    : "";

  useEffect(() => {
    if (typeof window === "undefined") return;
    const sessionId = sessionStorage.getItem("gridguard_otp_session_id");
    if (!sessionId) {
      router.replace("/login");
    }
  }, [router]);

  // Countdown timer
  useEffect(() => {
    if (countdown <= 0) return;
    const timer = setInterval(() => setCountdown((c) => c - 1), 1000);
    return () => clearInterval(timer);
  }, [countdown]);

  const minutes = Math.floor(countdown / 60);
  const seconds = countdown % 60;
  const countdownProgress = countdown / 300;

  const handleChange = useCallback((index: number, value: string) => {
    if (!/^\d*$/.test(value)) return;
    const newOtp = [...otp];
    newOtp[index] = value.slice(-1);
    setOtp(newOtp);
    setError(false);
    setErrorMessage("");

    if (value && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }

    // Auto-submit when all filled
    if (index === 5 && value) {
      const code = newOtp.join("");
      if (code.length === 6) {
        verifyOtp(code);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [otp]);

  const handleKeyDown = (index: number, e: React.KeyboardEvent) => {
    if (e.key === "Backspace" && !otp[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  };

  const verifyOtp = async (code: string) => {
    if (!otpSessionId) {
      router.replace("/login");
      return;
    }

    try {
      setLoading(true);
      setError(false);
      setErrorMessage("");

      const response = await apiPost<VerifyOtpResponse>("/auth/verify-otp", {
        otp_session_id: otpSessionId,
        otp_code: code,
      });

      localStorage.setItem("gridguard_access_token", response.access_token);
      localStorage.setItem("gridguard_refresh_token", response.refresh_token);
      localStorage.setItem("gridguard_partner_id", response.partner_id);
      localStorage.setItem("gridguard_wallet_balance", String(response.wallet_balance));

      setSuccess(true);
      setTimeout(() => router.push("/dashboard"), 600);
    } catch (err) {
      setError(true);
      if (err instanceof ApiError) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage("Verification failed. Please try again.");
      }
      shakeControls.start({
        x: [0, -10, 10, -10, 10, 0],
        transition: { duration: 0.4 },
      });
    } finally {
      setLoading(false);
    }
  };

  const handleVerify = () => {
    const code = otp.join("");
    if (code.length === 6) verifyOtp(code);
  };

  // SVG countdown ring
  const ringRadius = 22;
  const ringCircumference = 2 * Math.PI * ringRadius;
  const ringOffset = ringCircumference * (1 - countdownProgress);

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-sm bg-white rounded-3xl shadow-2xl p-8 text-center"
      >
        {/* Mail icon */}
        <motion.div
          initial={{ y: -10 }}
          animate={{ y: [0, -8, 0] }}
          transition={{ duration: 1.5, repeat: 2 }}
          className="flex justify-center mb-4"
        >
          <div className="w-16 h-16 rounded-full bg-navy/10 flex items-center justify-center">
            <Mail className="w-8 h-8 text-navy" />
          </div>
        </motion.div>

        <h2 className="text-2xl font-bold text-navy mb-2">Check your email</h2>
        <p className="text-sm text-ink-muted mb-8">
          We sent a 6-digit code to <span className="font-medium text-ink-primary">{email}</span>
        </p>

        {/* OTP boxes */}
        <motion.div animate={shakeControls} className="flex gap-3 justify-center mb-8">
          {otp.map((digit, idx) => (
            <input
              key={idx}
              ref={(el) => { inputRefs.current[idx] = el; }}
              type="text"
              inputMode="numeric"
              maxLength={1}
              value={digit}
              onChange={(e) => handleChange(idx, e.target.value)}
              onKeyDown={(e) => handleKeyDown(idx, e)}
              className={`w-12 h-14 border-2 rounded-lg text-center text-2xl font-bold transition-all outline-none
                ${success
                  ? "border-green-400 bg-green-50 text-green-600"
                  : error
                    ? "border-red-400 bg-red-50 text-red-600"
                    : "border-gray-200 focus:border-amber focus:ring-2 focus:ring-amber/30"
                }`}
            />
          ))}
        </motion.div>

        {/* Countdown Ring + Resend */}
        <div className="flex flex-col items-center gap-4 mb-6">
          <div className="relative">
            <svg width="56" height="56" viewBox="0 0 56 56">
              <circle
                cx="28" cy="28" r={ringRadius}
                fill="none" stroke="#e5e7eb" strokeWidth="3"
              />
              <circle
                cx="28" cy="28" r={ringRadius}
                fill="none" stroke="#F5A623" strokeWidth="3"
                strokeLinecap="round"
                strokeDasharray={ringCircumference}
                strokeDashoffset={ringOffset}
                transform="rotate(-90 28 28)"
                className="transition-all duration-1000"
              />
            </svg>
            <span className="absolute inset-0 flex items-center justify-center text-xs font-bold text-ink-primary">
              {minutes}:{seconds.toString().padStart(2, "0")}
            </span>
          </div>
          {countdown <= 0 && (
            <motion.button
              animate={{ opacity: [0.5, 1, 0.5] }}
              transition={{ duration: 1.5, repeat: Infinity }}
              onClick={() => router.push("/login")}
              className="text-sm font-semibold text-amber hover:text-amber-dark transition-colors"
            >
              Request New OTP
            </motion.button>
          )}
        </div>

        {/* Verify button */}
        <button
          onClick={handleVerify}
          disabled={loading || otp.join("").length < 6}
          className="w-full h-14 rounded-full text-white font-bold text-lg transition-all
            hover:scale-[1.02] hover:shadow-glow disabled:opacity-60 disabled:hover:scale-100
            flex items-center justify-center"
          style={{ background: "linear-gradient(135deg, #F5A623, #D4891A)" }}
        >
          {loading ? "Verifying..." : "Verify OTP"}
        </button>

        {errorMessage && (
          <p className="text-xs text-red-600 mt-4">{errorMessage}</p>
        )}
      </motion.div>
    </div>
  );
}
