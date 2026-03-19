// import type { Config } from "tailwindcss";

// const config: Config = {
//   content: [
//     "./pages/**/*.{js,ts,jsx,tsx,mdx}",
//     "./components/**/*.{js,ts,jsx,tsx,mdx}",
//     "./app/**/*.{js,ts,jsx,tsx,mdx}",
//   ],
//   theme: {
//     extend: {
//       colors: {
//         background: "var(--background)",
//         foreground: "var(--foreground)",
//         navy: {
//           DEFAULT: "#1A3C5E",
//           light: "#2A5A8E",
//           dark: "#0F2238",
//         },
//         amber: {
//           DEFAULT: "#F5A623",
//           light: "#F7BC5A",
//           dark: "#D4891A",
//         },
//         success: {
//           DEFAULT: "#27AE60",
//         },
//         danger: {
//           DEFAULT: "#E74C3C",
//         },
//         warning: {
//           DEFAULT: "#F39C12",
//         },
//         surface: {
//           DEFAULT: "#F4F6F9",
//           card: "#FFFFFF",
//         },
//         ink: {
//           primary: "#2C3E50",
//           muted: "#7F8C8D",
//         },
//       },
//       fontFamily: {
//         sans: ["Inter", "system-ui", "sans-serif"],
//         mono: ["JetBrains Mono", "Fira Code", "monospace"],
//       },
//       boxShadow: {
//         card: "0 2px 12px rgba(0,0,0,0.06)",
//         "card-hover": "0 8px 30px rgba(0,0,0,0.12)",
//         glow: "0 0 20px rgba(245,166,35,0.3)",
//       },
//       animation: {
//         "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
//         "bounce-slow": "bounce 2s infinite",
//         float: "float 3s ease-in-out infinite",
//         "scale-pulse": "scalePulse 2s ease-in-out infinite",
//       },
//       keyframes: {
//         float: {
//           "0%, 100%": { transform: "translateY(0px)" },
//           "50%": { transform: "translateY(-10px)" },
//         },
//         scalePulse: {
//           "0%, 100%": { transform: "scale(1)" },
//           "50%": { transform: "scale(1.05)" },
//         },
//       },
//     },
//   },
//   plugins: [],
// };
// export default config;

import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Shadcn UI System Colors (Maps to your globals.css variables)
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },

        // Your Custom Brand Colors
        navy: {
          DEFAULT: "#1A3C5E",
          light: "#2A5A8E",
          dark: "#0F2238",
        },
        amber: {
          DEFAULT: "#F5A623",
          light: "#F7BC5A",
          dark: "#D4891A",
        },
        success: {
          DEFAULT: "#27AE60",
        },
        danger: {
          DEFAULT: "#E74C3C",
        },
        warning: {
          DEFAULT: "#F39C12",
        },
        surface: {
          DEFAULT: "#F4F6F9",
          card: "#FFFFFF",
        },
        ink: {
          primary: "#2C3E50",
          muted: "#7F8C8D",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },
      boxShadow: {
        card: "0 2px 12px rgba(0,0,0,0.06)",
        "card-hover": "0 8px 30px rgba(0,0,0,0.12)",
        glow: "0 0 20px rgba(245,166,35,0.3)",
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "bounce-slow": "bounce 2s infinite",
        float: "float 3s ease-in-out infinite",
        "scale-pulse": "scalePulse 2s ease-in-out infinite",
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
      },
      keyframes: {
        float: {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-10px)" },
        },
        scalePulse: {
          "0%, 100%": { transform: "scale(1)" },
          "50%": { transform: "scale(1.05)" },
        },
        "accordion-down": {
          from: { height: "0" },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: "0" },
        },
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;