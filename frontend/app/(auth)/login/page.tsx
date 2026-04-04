"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Loader2 } from "lucide-react";
import { ApiError, apiPost } from "@/lib/api";

const loginSchema = z.object({
  deviceId: z.string().min(6, "Device ID must be at least 6 characters"),
  email: z.string().email("Please enter a valid email"),
  fullName: z.string().min(2, "Name must be at least 2 characters"),
  city: z.string().min(1, "Please select a city"),
  platform: z.string().min(1, "Please select a platform"),
});

type LoginFormData = z.infer<typeof loginSchema>;

const CITIES = ["Bengaluru", "Mumbai", "Chennai", "Delhi", "Hyderabad", "Pune", "Kolkata"];
const PLATFORMS = [
  { value: "zomato", label: "🔴 Zomato" },
  { value: "swiggy", label: "🟠 Swiggy" },
  { value: "zepto", label: "🟣 Zepto" },
  { value: "blinkit", label: "🟡 Blinkit" },
];

type RegisterResponse = {
  partner_id: string;
  otp_session_id: string;
  message: string;
};

// Particle component
function FloatingParticles() {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {Array.from({ length: 20 }).map((_, i) => (
        <motion.div
          key={i}
          className="absolute w-1 h-1 bg-white/20 rounded-full"
          initial={{
            x: Math.random() * (typeof window !== "undefined" ? window.innerWidth : 1000),
            y: Math.random() * (typeof window !== "undefined" ? window.innerHeight : 800),
          }}
          animate={{
            y: [null, -20, 20],
            x: [null, Math.random() * 40 - 20],
            opacity: [0.2, 0.6, 0.2],
          }}
          transition={{
            duration: 4 + Math.random() * 4,
            repeat: Infinity,
            repeatType: "reverse",
            delay: Math.random() * 3,
          }}
          style={{
            width: 2 + Math.random() * 4,
            height: 2 + Math.random() * 4,
          }}
        />
      ))}
    </div>
  );
}

export default function LoginPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [lang, setLang] = useState<"en" | "hi">("en");
  const [submitError, setSubmitError] = useState("");

  const {
    register,
    handleSubmit,
    formState: { errors, dirtyFields },
    watch,
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    mode: "onChange",
  });

  const email = watch("email");
  const emailValid = email && !errors.email && dirtyFields.email;
  const emailInvalid = errors.email && dirtyFields.email;

  const onSubmit = async (data: LoginFormData) => {
    try {
      setLoading(true);
      setSubmitError("");

      const response = await apiPost<RegisterResponse>("/auth/register", {
        device_id: data.deviceId,
        email: data.email.trim().toLowerCase(),
        full_name: data.fullName.trim(),
        city: data.city.trim().toLowerCase(),
        platform: data.platform,
      });

      sessionStorage.setItem("gridguard_email", data.email.trim().toLowerCase());
      sessionStorage.setItem("gridguard_name", data.fullName.trim());
      sessionStorage.setItem("gridguard_otp_session_id", response.otp_session_id);
      sessionStorage.setItem("gridguard_partner_id", response.partner_id);
      router.push("/verify");
    } catch (error) {
      if (error instanceof ApiError) {
        setSubmitError(error.message);
      } else {
        setSubmitError("Unable to register right now. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 relative">
      <FloatingParticles />

      {/* Language toggle */}
      <div className="absolute top-6 right-6 z-10">
        <div className="bg-white/10 backdrop-blur-md rounded-full p-1 flex">
          <button
            onClick={() => setLang("en")}
            className={`px-3 py-1 rounded-full text-sm font-medium transition-all ${
              lang === "en" ? "bg-white text-navy" : "text-white/70 hover:text-white"
            }`}
          >
            EN
          </button>
          <button
            onClick={() => setLang("hi")}
            className={`px-3 py-1 rounded-full text-sm font-medium transition-all ${
              lang === "hi" ? "bg-white text-navy" : "text-white/70 hover:text-white"
            }`}
          >
            हि
          </button>
        </div>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 30, scale: 0.95 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.6, ease: "easeOut" }}
        className="w-full max-w-md bg-white rounded-3xl shadow-2xl p-10 relative z-10"
      >
        {/* Logo */}
        <div className="flex justify-center mb-6">
          <motion.div
            animate={{ scale: [1, 1.05, 1] }}
            transition={{ duration: 2, repeat: Infinity }}
          >
            <svg width="64" height="64" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M32 4L56 16V40C56 52 44 60 32 60C20 60 8 52 8 40V16L32 4Z" fill="#1A3C5E" />
              <path d="M32 12L48 20V38C48 47 40 53 32 53C24 53 16 47 16 38V20L32 12Z" fill="#2A5A8E" />
              <path d="M30 24L26 36H30L28 44L38 30H33L36 24H30Z" fill="#F5A623" />
            </svg>
          </motion.div>
        </div>

        {/* Tagline */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="text-center text-lg font-light text-ink-muted mb-8"
        >
          {lang === "en"
            ? "Your earnings. Protected. Always."
            : "आपकी कमाई। सुरक्षित। हमेशा।"}
        </motion.p>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {/* Device ID */}
          <div>
            <label className="block text-sm font-medium text-ink-primary mb-1.5">
              {lang === "en" ? "Device ID" : "डिवाइस आईडी"}
            </label>
            <input
              {...register("deviceId")}
              placeholder="DEV-A1B2C3D4"
              className={`w-full h-12 px-4 rounded-lg border font-mono text-sm transition-all outline-none
                ${errors.deviceId
                  ? "border-red-400 focus:border-red-500 focus:ring-2 focus:ring-red-200"
                  : "border-gray-200 focus:border-navy focus:ring-2 focus:ring-navy/20"}`}
            />
            {errors.deviceId && (
              <p className="text-xs text-red-500 mt-1">{errors.deviceId.message}</p>
            )}
          </div>

          {/* Email */}
          <div>
            <label className="block text-sm font-medium text-ink-primary mb-1.5">
              {lang === "en" ? "Email" : "ईमेल"}
            </label>
            <div className="relative">
              <input
                {...register("email")}
                type="email"
                placeholder="rider@example.com"
                className={`w-full h-12 px-4 pr-10 rounded-lg border text-sm transition-all outline-none
                  ${errors.email && dirtyFields.email
                    ? "border-red-400 focus:border-red-500 focus:ring-2 focus:ring-red-200"
                    : "border-gray-200 focus:border-navy focus:ring-2 focus:ring-navy/20"}`}
              />
              {emailValid && (
                <span className="absolute right-3 top-1/2 -translate-y-1/2 text-green-500 text-lg">✓</span>
              )}
              {emailInvalid && (
                <span className="absolute right-3 top-1/2 -translate-y-1/2 text-red-500 text-lg">✗</span>
              )}
            </div>
            {errors.email && dirtyFields.email && (
              <p className="text-xs text-red-500 mt-1">{errors.email.message}</p>
            )}
          </div>

          {/* Full Name */}
          <div>
            <label className="block text-sm font-medium text-ink-primary mb-1.5">
              {lang === "en" ? "Full Name" : "पूरा नाम"}
            </label>
            <input
              {...register("fullName")}
              placeholder="Rajesh Kumar"
              className={`w-full h-12 px-4 rounded-lg border text-sm transition-all outline-none
                ${errors.fullName
                  ? "border-red-400 focus:ring-2 focus:ring-red-200"
                  : "border-gray-200 focus:border-navy focus:ring-2 focus:ring-navy/20"}`}
            />
          </div>

          {/* City */}
          <div>
            <label className="block text-sm font-medium text-ink-primary mb-1.5">
              {lang === "en" ? "City" : "शहर"}
            </label>
            <select
              {...register("city")}
              className={`w-full h-12 px-4 rounded-lg border text-sm transition-all outline-none appearance-none bg-white
                ${errors.city
                  ? "border-red-400"
                  : "border-gray-200 focus:border-navy focus:ring-2 focus:ring-navy/20"}`}
            >
              <option value="">{lang === "en" ? "Select city" : "शहर चुनें"}</option>
              {CITIES.map((city) => (
                <option key={city} value={city}>{city}</option>
              ))}
            </select>
          </div>

          {/* Platform */}
          <div>
            <label className="block text-sm font-medium text-ink-primary mb-1.5">
              {lang === "en" ? "Platform" : "प्लेटफार्म"}
            </label>
            <select
              {...register("platform")}
              className={`w-full h-12 px-4 rounded-lg border text-sm transition-all outline-none appearance-none bg-white
                ${errors.platform
                  ? "border-red-400"
                  : "border-gray-200 focus:border-navy focus:ring-2 focus:ring-navy/20"}`}
            >
              <option value="">{lang === "en" ? "Select platform" : "प्लेटफार्म चुनें"}</option>
              {PLATFORMS.map((p) => (
                <option key={p.value} value={p.value}>{p.label}</option>
              ))}
            </select>
          </div>

          {/* Submit */}
          <button
            type="submit"
            disabled={loading}
            className="w-full h-14 rounded-full text-white font-bold text-lg transition-all
              hover:scale-[1.02] hover:shadow-glow disabled:opacity-70 disabled:hover:scale-100
              flex items-center justify-center gap-2"
            style={{ background: "linear-gradient(135deg, #F5A623, #D4891A)" }}
          >
            {loading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                {lang === "en" ? "Sending OTP..." : "OTP भेज रहे हैं..."}
              </>
            ) : (
              lang === "en" ? "Get Started" : "शुरू करें"
            )}
          </button>

          {submitError && (
            <p className="text-sm text-red-600 text-center">{submitError}</p>
          )}

          <p className="text-xs text-center text-ink-muted pt-1">
            Admin / Ops user? Use the separate
            <a href="/admin/login" className="font-semibold text-navy hover:underline ml-1">admin sign-in</a>.
          </p>
        </form>
      </motion.div>
    </div>
  );
}
