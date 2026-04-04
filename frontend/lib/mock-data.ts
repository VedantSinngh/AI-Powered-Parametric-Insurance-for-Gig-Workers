// // ──────────────────────────── Mock Data for GridGuard ────────────────────────────

// export const CITIES = ["Bengaluru", "Mumbai", "Chennai", "Delhi", "Hyderabad", "Pune", "Kolkata"] as const;
// export type City = (typeof CITIES)[number];

// export const PLATFORMS = [
//   { name: "Zomato", emoji: "🔴" },
//   { name: "Swiggy", emoji: "🟠" },
//   { name: "Zepto", emoji: "🟣" },
//   { name: "Blinkit", emoji: "🟡" },
// ] as const;

// export const ZONES = ["B4F2", "A2C1", "D7E9", "C3F1", "E5A2", "F8B3"] as const;

// export interface Partner {
//   id: string;
//   name: string;
//   deviceId: string;
//   email: string;
//   phone: string;
//   city: City;
//   platform: string;
//   zone: string;
//   riskTier: "low" | "medium" | "high";
//   premium: number;
//   lastPayout: string;
//   status: "active" | "suspended" | "pending";
//   workabilityScore: number;
// }

// export interface Payout {
//   id: string;
//   partnerId: string;
//   partnerName: string;
//   zone: string;
//   eventType: "rain" | "heat" | "aqi" | "outage";
//   eventName: string;
//   amount: number;
//   timestamp: string;
//   status: "paid" | "pending" | "flagged";
//   txHash: string;
//   city: string;
//   duration: string;
//   partnerCount?: number;
// }

// export interface FraudAlert {
//   id: string;
//   partnerId: string;
//   partnerName: string;
//   rule: string;
//   severity: "critical" | "warning" | "info";
//   timestamp: string;
//   status: "pending" | "confirmed" | "dismissed";
//   lat: number;
//   lng: number;
//   details: string;
// }

// const NAMES = [
//   "Rajesh K.", "Priya M.", "Arjun S.", "Divya R.", "Karan P.",
//   "Meera N.", "Suresh B.", "Anita V.", "Vikram D.", "Lakshmi G.",
//   "Rohan T.", "Sneha L.", "Aditya M.", "Pooja S.", "Nikhil R.",
//   "Kavita B.", "Rahul J.", "Deepa K.", "Sanjay P.", "Nisha A.",
//   "Amit C.", "Rekha D.", "Varun H.", "Swati F.", "Pankaj N.",
//   "Jaya M.", "Sunil K.", "Ritu S.", "Manoj V.", "Geeta R.",
//   "Ajay B.", "Sonal P.", "Vinod T.", "Manju L.", "Prakash G.",
//   "Usha K.", "Ravi A.", "Ankita D.", "Harish M.", "Sunita J.",
//   "Govind S.", "Pallavi R.", "Ashok N.", "Lalita B.", "Vijay C.",
//   "Smita H.", "Dinesh F.", "Bhavna P.", "Ramesh T.", "Asha G.",
// ];

// function generateDeviceId(): string {
//   return "DEV-" + Math.random().toString(36).substring(2, 10).toUpperCase();
// }

// export const mockPartners: Partner[] = NAMES.map((name, i) => ({
//   id: `partner-${i + 1}`,
//   name,
//   deviceId: generateDeviceId(),
//   email: name.toLowerCase().replace(/[\s.]/g, "") + "@gmail.com",
//   phone: `+91 ${9800000000 + i * 123456}`,
//   city: CITIES[i % CITIES.length],
//   platform: PLATFORMS[i % PLATFORMS.length].name,
//   zone: ZONES[i % ZONES.length],
//   riskTier: (["low", "medium", "high"] as const)[i % 3],
//   premium: [12, 15, 18, 21, 24][i % 5],
//   lastPayout: i < 5 ? "Today" : i < 15 ? "Yesterday" : `${Math.floor(i / 5)} days ago`,
//   status: i % 10 === 0 ? "suspended" : i % 7 === 0 ? "pending" : "active",
//   workabilityScore: Number((0.45 + Math.random() * 0.5).toFixed(2)),
// }));

// export const mockPayouts: Payout[] = [
//   { id: "p1", partnerId: "partner-1", partnerName: "Rajesh K.", zone: "B4F2", eventType: "rain", eventName: "Bengaluru Rainfall", amount: 50, timestamp: "Today 3:15 PM", status: "paid", txHash: "MOCK-RAIN-a3f2b1c9", city: "Bengaluru", duration: "1 hour", partnerCount: 234 },
//   { id: "p2", partnerId: "partner-2", partnerName: "Priya M.", zone: "A2C1", eventType: "heat", eventName: "Mumbai Heat Alert", amount: 35, timestamp: "Yesterday", status: "paid", txHash: "MOCK-HEAT-b4e2c1d8", city: "Mumbai", duration: "45 min", partnerCount: 89 },
//   { id: "p3", partnerId: "partner-3", partnerName: "Arjun S.", zone: "D7E9", eventType: "outage", eventName: "App Outage", amount: 45, timestamp: "Mon 10:00 AM", status: "paid", txHash: "MOCK-OUTG-c5f3d2e7", city: "Delhi", duration: "30 min", partnerCount: 45 },
//   { id: "p4", partnerId: "partner-4", partnerName: "Divya R.", zone: "C3F1", eventType: "aqi", eventName: "Delhi AQI Spike", amount: 40, timestamp: "Sun 2:00 PM", status: "paid", txHash: "MOCK-AQII-d6g4e3f6", city: "Delhi", duration: "1.5 hours", partnerCount: 156 },
//   { id: "p5", partnerId: "partner-5", partnerName: "Karan P.", zone: "E5A2", eventType: "rain", eventName: "Chennai Heavy Rain", amount: 55, timestamp: "Sat 11:00 AM", status: "paid", txHash: "MOCK-RAIN-e7h5f4g5", city: "Chennai", duration: "2 hours", partnerCount: 178 },
//   { id: "p6", partnerId: "partner-6", partnerName: "Meera N.", zone: "F8B3", eventType: "heat", eventName: "Hyderabad Heat Wave", amount: 30, timestamp: "Fri 4:30 PM", status: "paid", txHash: "MOCK-HEAT-f8i6g5h4", city: "Hyderabad", duration: "1 hour", partnerCount: 67 },
//   { id: "p7", partnerId: "partner-7", partnerName: "Suresh B.", zone: "B4F2", eventType: "outage", eventName: "Swiggy Outage", amount: 45, timestamp: "Thu 9:00 AM", status: "paid", txHash: "MOCK-OUTG-g9j7h6i3", city: "Bengaluru", duration: "40 min", partnerCount: 112 },
//   { id: "p8", partnerId: "partner-8", partnerName: "Anita V.", zone: "A2C1", eventType: "rain", eventName: "Mumbai Monsoon", amount: 60, timestamp: "Wed 1:00 PM", status: "paid", txHash: "MOCK-RAIN-h0k8i7j2", city: "Mumbai", duration: "2.5 hours", partnerCount: 290 },
// ];

// export const mockTimelinePayouts: Payout[] = [
//   { id: "tl1", partnerId: "", partnerName: "", zone: "B4F2", eventType: "rain", eventName: "Bengaluru Rainfall", amount: 11700, timestamp: "Today 3:00 PM", status: "paid", txHash: "MOCK-RAIN-001", city: "Bengaluru", duration: "2 hours", partnerCount: 234 },
//   { id: "tl2", partnerId: "", partnerName: "", zone: "A2C1", eventType: "heat", eventName: "Mumbai Heat", amount: 3115, timestamp: "Today 11:00 AM", status: "paid", txHash: "MOCK-HEAT-002", city: "Mumbai", duration: "1 hour", partnerCount: 89 },
//   { id: "tl3", partnerId: "", partnerName: "", zone: "D7E9", eventType: "aqi", eventName: "Delhi AQI", amount: 6240, timestamp: "Yesterday", status: "paid", txHash: "MOCK-AQII-003", city: "Delhi", duration: "3 hours", partnerCount: 156 },
//   { id: "tl4", partnerId: "", partnerName: "", zone: "C3F1", eventType: "outage", eventName: "Chennai App Outage", amount: 2450, timestamp: "Yesterday", status: "paid", txHash: "MOCK-OUTG-004", city: "Chennai", duration: "45 min", partnerCount: 70 },
//   { id: "tl5", partnerId: "", partnerName: "", zone: "E5A2", eventType: "rain", eventName: "Hyderabad Rain", amount: 8900, timestamp: "2 days ago", status: "paid", txHash: "MOCK-RAIN-005", city: "Hyderabad", duration: "2 hours", partnerCount: 178 },
//   { id: "tl6", partnerId: "", partnerName: "", zone: "F8B3", eventType: "heat", eventName: "Pune Heat Alert", amount: 4200, timestamp: "3 days ago", status: "paid", txHash: "MOCK-HEAT-006", city: "Pune", duration: "1.5 hours", partnerCount: 120 },
//   { id: "tl7", partnerId: "", partnerName: "", zone: "B4F2", eventType: "aqi", eventName: "Kolkata AQI", amount: 5670, timestamp: "4 days ago", status: "paid", txHash: "MOCK-AQII-007", city: "Kolkata", duration: "2 hours", partnerCount: 135 },
//   { id: "tl8", partnerId: "", partnerName: "", zone: "A2C1", eventType: "rain", eventName: "Mumbai Heavy Rain", amount: 15400, timestamp: "5 days ago", status: "paid", txHash: "MOCK-RAIN-008", city: "Mumbai", duration: "4 hours", partnerCount: 310 },
// ];

// export const mockFraudAlerts: FraudAlert[] = [
//   { id: "fa1", partnerId: "partner-12", partnerName: "Rohan T.", rule: "wrong_zone", severity: "critical", timestamp: "2 min ago", status: "pending", lat: 12.9352, lng: 77.6245, details: "GPS coordinates outside claimed zone B4F2" },
//   { id: "fa2", partnerId: "partner-15", partnerName: "Nikhil R.", rule: "stationary_device", severity: "critical", timestamp: "5 min ago", status: "pending", lat: 19.0760, lng: 72.8777, details: "Device stationary for 45min during claimed disruption" },
//   { id: "fa3", partnerId: "partner-8", partnerName: "Anita V.", rule: "no_pre_activity", severity: "warning", timestamp: "15 min ago", status: "pending", lat: 13.0827, lng: 80.2707, details: "No delivery activity 2hr before claiming disruption" },
//   { id: "fa4", partnerId: "partner-22", partnerName: "Rekha D.", rule: "velocity_abuse", severity: "warning", timestamp: "28 min ago", status: "pending", lat: 28.6139, lng: 77.2090, details: "3 claims in 24hr exceeds threshold" },
//   { id: "fa5", partnerId: "partner-30", partnerName: "Ajay B.", rule: "multi_account", severity: "info", timestamp: "1 hr ago", status: "dismissed", lat: 12.9716, lng: 77.5946, details: "Same device ID registered under 2 accounts" },
//   { id: "fa6", partnerId: "partner-45", partnerName: "Vijay C.", rule: "no_pre_activity", severity: "info", timestamp: "2 hr ago", status: "dismissed", lat: 17.3850, lng: 78.4867, details: "No delivery activity before claim" },
// ];

// export const EVENT_ICONS: Record<string, string> = {
//   rain: "🌧",
//   heat: "🌡",
//   aqi: "💨",
//   outage: "📱",
// };

// export const EVENT_COLORS: Record<string, string> = {
//   rain: "bg-blue-100 text-blue-700",
//   heat: "bg-orange-100 text-orange-700",
//   aqi: "bg-purple-100 text-purple-700",
//   outage: "bg-violet-100 text-violet-700",
// };

// // Generate chart data
// export function generateLossRatioData(days: number = 30) {
//   return Array.from({ length: days }, (_, i) => ({
//     date: new Date(Date.now() - (days - 1 - i) * 86400000).toLocaleDateString("en-IN", { day: "2-digit", month: "short" }),
//     ratio: Number((45 + Math.random() * 20).toFixed(1)),
//   }));
// }

// export function generatePremiumPayoutData(weeks: number = 8) {
//   return Array.from({ length: weeks }, (_, i) => ({
//     week: `W${i + 1}`,
//     premium: Math.floor(180000 + Math.random() * 80000),
//     payouts: Math.floor(90000 + Math.random() * 60000),
//   }));
// }

// export function generatePartnerGrowthData(days: number = 30) {
//   const base = 38000;
//   return Array.from({ length: days }, (_, i) => ({
//     date: new Date(Date.now() - (days - 1 - i) * 86400000).toLocaleDateString("en-IN", { day: "2-digit", month: "short" }),
//     partners: Math.floor(base + (i / days) * 4800 + Math.random() * 500),
//   }));
// }

// export const topZonesData = [
//   { zone: "B4F2", payouts: 245000 },
//   { zone: "A2C1", payouts: 198000 },
//   { zone: "D7E9", payouts: 176000 },
//   { zone: "C3F1", payouts: 154000 },
//   { zone: "E5A2", payouts: 132000 },
//   { zone: "F8B3", payouts: 118000 },
//   { zone: "G2D4", payouts: 95000 },
//   { zone: "H1E6", payouts: 78000 },
//   { zone: "I9F7", payouts: 62000 },
//   { zone: "J3A8", payouts: 45000 },
// ];

// export const weeklyForecast = [
//   { day: "Mon", weather: "🌧", risk: "high", amount: 24 },
//   { day: "Tue", weather: "☀️", risk: "low", amount: 12 },
//   { day: "Wed", weather: "🌡", risk: "medium", amount: 18 },
//   { day: "Thu", weather: "🌧", risk: "high", amount: 24 },
//   { day: "Fri", weather: "☀️", risk: "low", amount: 12 },
//   { day: "Sat", weather: "💨", risk: "medium", amount: 18 },
//   { day: "Sun", weather: "☀️", risk: "low", amount: 12 },
// ];

// // Mock hex cells for map
// export const mockHexCells = [
//   { h3Index: "882a1008a3fffff", lat: 12.9716, lng: 77.5946, score: 0.72, zoneName: "B4F2", event: "Rain Disruption", rate: 50 },
//   { h3Index: "882a1008a7fffff", lat: 12.9816, lng: 77.6046, score: 0.85, zoneName: "A2C1", event: "Clear", rate: 35 },
//   { h3Index: "882a1008abfffff", lat: 12.9616, lng: 77.5846, score: 0.35, zoneName: "D7E9", event: "Heat Alert", rate: 45 },
//   { h3Index: "882a1008affffff", lat: 12.9516, lng: 77.6146, score: 0.55, zoneName: "C3F1", event: "AQI Warning", rate: 40 },
//   { h3Index: "882a1008b3fffff", lat: 12.9916, lng: 77.5746, score: 0.92, zoneName: "E5A2", event: "Clear", rate: 30 },
//   { h3Index: "882a1008b7fffff", lat: 12.9416, lng: 77.5546, score: 0.28, zoneName: "F8B3", event: "App Outage", rate: 55 },
//   { h3Index: "882a1008bbfffff", lat: 12.9316, lng: 77.6246, score: 0.65, zoneName: "G2D4", event: "Light Rain", rate: 38 },
//   { h3Index: "882a1008bffffff", lat: 13.0016, lng: 77.5646, score: 0.45, zoneName: "H1E6", event: "Heat Advisory", rate: 42 },
//   { h3Index: "882a1008c3fffff", lat: 12.9216, lng: 77.6346, score: 0.78, zoneName: "I9F7", event: "Clear", rate: 32 },
//   { h3Index: "882a1008c7fffff", lat: 13.0116, lng: 77.6446, score: 0.18, zoneName: "J3A8", event: "Heavy Rain", rate: 60 },
//   { h3Index: "882a1008cbfffff", lat: 12.9116, lng: 77.5446, score: 0.62, zoneName: "K5B9", event: "Moderate Wind", rate: 36 },
//   { h3Index: "882a1008cffffff", lat: 13.0216, lng: 77.5546, score: 0.88, zoneName: "L7C2", event: "Clear", rate: 28 },
//   { h3Index: "882a1008d3fffff", lat: 12.9016, lng: 77.6546, score: 0.42, zoneName: "M8D3", event: "AQI Alert", rate: 48 },
//   { h3Index: "882a1008d7fffff", lat: 13.0316, lng: 77.5346, score: 0.73, zoneName: "N1E4", event: "Light Rain", rate: 34 },
//   { h3Index: "882a1008dbfffff", lat: 12.8916, lng: 77.6646, score: 0.31, zoneName: "O4F5", event: "Storm", rate: 65 },
//   { h3Index: "882a1008dffffff", lat: 13.0416, lng: 77.5246, score: 0.81, zoneName: "P6A7", event: "Clear", rate: 30 },
//   { h3Index: "882a1008e3fffff", lat: 12.8816, lng: 77.5146, score: 0.56, zoneName: "Q2B8", event: "Heat", rate: 44 },
//   { h3Index: "882a1008e7fffff", lat: 13.0516, lng: 77.6746, score: 0.69, zoneName: "R9C1", event: "Drizzle", rate: 38 },
//   { h3Index: "882a1008ebfffff", lat: 12.8716, lng: 77.5046, score: 0.47, zoneName: "S3D6", event: "AQI Warning", rate: 42 },
//   { h3Index: "882a1008effffff", lat: 13.0616, lng: 77.6846, score: 0.91, zoneName: "T8E2", event: "Clear", rate: 25 },
// ];

// // Accelerometer mock data for fraud
// export const mockAccelerometerData = Array.from({ length: 30 }, (_, i) => ({
//   time: `${i}s`,
//   value: i > 10 && i < 20 ? 0.05 + Math.random() * 0.08 : 0.3 + Math.random() * 0.4,
// }));

// export function formatINR(amount: number): string {
//   return new Intl.NumberFormat("en-IN", {
//     style: "currency",
//     currency: "INR",
//     maximumFractionDigits: 0,
//   }).format(amount);
// }

// export function formatINRCompact(amount: number): string {
//   if (amount >= 100000) return `₹${(amount / 100000).toFixed(1)}L`;
//   if (amount >= 1000) return `₹${(amount / 1000).toFixed(1)}K`;
//   return `₹${amount}`;
// }

// export const mockFraudData = {
//   riskScores: [
//     { range: "0-20", count: 450 },
//     { range: "21-40", count: 320 },
//     { range: "41-60", count: 180 },
//     { range: "61-80", count: 85 },
//     { range: "81-100", count: 42 },
//   ],
//   flaggedPartners: [
//     { id: "P-8821", name: "Suresh Kumar", zone: "B4F2", frequency: "4 claims/wk", score: 92 },
//     { id: "P-4492", name: "Anita Singh", zone: "A2C1", frequency: "3 claims/wk", score: 84 },
//     { id: "P-1103", name: "Vikram Das", zone: "D7E9", frequency: "5 claims/mo", score: 76 },
//     { id: "P-5561", name: "Rahul Jain", zone: "C3F1", frequency: "2 claims/wk", score: 68 },
//   ]
// };

// ──────────────────────────── Mock Data for GridGuard ────────────────────────────

export const CITIES = ["Bengaluru", "Mumbai", "Chennai", "Delhi", "Hyderabad", "Pune", "Kolkata"] as const;
export type City = (typeof CITIES)[number];

export const PLATFORMS = [
  { name: "Zomato", emoji: "🔴" },
  { name: "Swiggy", emoji: "🟠" },
  { name: "Zepto", emoji: "🟣" },
  { name: "Blinkit", emoji: "🟡" },
] as const;

export const ZONES = ["B4F2", "A2C1", "D7E9", "C3F1", "E5A2", "F8B3"] as const;

export interface Partner {
  id: string;
  name: string;
  deviceId: string;
  email: string;
  phone: string;
  city: City;
  platform: string;
  zone: string;
  riskTier: "low" | "medium" | "high";
  premium: number;
  lastPayout: string;
  status: "active" | "suspended" | "pending";
  workabilityScore: number;
  // PartnersPage fields
  joined: string;
  trustScore: number;
}

export interface Payout {
  id: string;
  partnerId: string;
  partnerName: string;
  zone: string;
  eventType: "rain" | "heat" | "aqi" | "outage" | "traffic";
  eventName: string;
  amount: number;
  timestamp: string;
  status: "paid" | "pending" | "flagged";
  txHash: string;
  city: string;
  duration: string;
  provider?: string;
  partnerCount?: number;
}

export interface FraudAlert {
  id: string;
  partnerId: string;
  partnerName: string;
  rule: string;
  severity: "critical" | "warning" | "info";
  timestamp: string;
  status: "pending" | "confirmed" | "dismissed";
  lat: number;
  lng: number;
  details: string;
}

const NAMES = [
  "Rajesh K.", "Priya M.", "Arjun S.", "Divya R.", "Karan P.",
  "Meera N.", "Suresh B.", "Anita V.", "Vikram D.", "Lakshmi G.",
  "Rohan T.", "Sneha L.", "Aditya M.", "Pooja S.", "Nikhil R.",
  "Kavita B.", "Rahul J.", "Deepa K.", "Sanjay P.", "Nisha A.",
  "Amit C.", "Rekha D.", "Varun H.", "Swati F.", "Pankaj N.",
  "Jaya M.", "Sunil K.", "Ritu S.", "Manoj V.", "Geeta R.",
  "Ajay B.", "Sonal P.", "Vinod T.", "Manju L.", "Prakash G.",
  "Usha K.", "Ravi A.", "Ankita D.", "Harish M.", "Sunita J.",
  "Govind S.", "Pallavi R.", "Ashok N.", "Lalita B.", "Vijay C.",
  "Smita H.", "Dinesh F.", "Bhavna P.", "Ramesh T.", "Asha G.",
];

const JOIN_DATES = [
  "Jan 2023", "Feb 2023", "Mar 2023", "Apr 2023", "May 2023",
  "Jun 2023", "Jul 2023", "Aug 2023", "Sep 2023", "Oct 2023",
  "Nov 2023", "Dec 2023", "Jan 2024", "Feb 2024", "Mar 2024",
  "Apr 2024", "May 2024", "Jun 2024", "Jul 2024", "Aug 2024",
];

function generateDeviceId(): string {
  return "DEV-" + Math.random().toString(36).substring(2, 10).toUpperCase();
}

export const mockPartners: Partner[] = NAMES.map((name, i) => ({
  id: `partner-${i + 1}`,
  name,
  deviceId: generateDeviceId(),
  email: name.toLowerCase().replace(/[\s.]/g, "") + "@gmail.com",
  phone: `+91 ${9800000000 + i * 123456}`,
  city: CITIES[i % CITIES.length],
  platform: PLATFORMS[i % PLATFORMS.length].name,
  zone: ZONES[i % ZONES.length],
  riskTier: (["low", "medium", "high"] as const)[i % 3],
  premium: [12, 15, 18, 21, 24][i % 5],
  lastPayout: i < 5 ? "Today" : i < 15 ? "Yesterday" : `${Math.floor(i / 5)} days ago`,
  status: i % 10 === 0 ? "suspended" : i % 7 === 0 ? "pending" : "active",
  workabilityScore: Number((0.45 + Math.random() * 0.5).toFixed(2)),
  // PartnersPage fields
  joined: JOIN_DATES[i % JOIN_DATES.length],
  trustScore: Math.floor(60 + Math.random() * 40),
}));

export const mockPayouts: Payout[] = [
  { id: "p1", partnerId: "partner-1", partnerName: "Rajesh K.", zone: "B4F2", eventType: "rain", eventName: "Bengaluru Rainfall", amount: 50, timestamp: "Today 3:15 PM", status: "paid", txHash: "MOCK-RAIN-a3f2b1c9", city: "Bengaluru", duration: "1 hour", partnerCount: 234 },
  { id: "p2", partnerId: "partner-2", partnerName: "Priya M.", zone: "A2C1", eventType: "heat", eventName: "Mumbai Heat Alert", amount: 35, timestamp: "Yesterday", status: "paid", txHash: "MOCK-HEAT-b4e2c1d8", city: "Mumbai", duration: "45 min", partnerCount: 89 },
  { id: "p3", partnerId: "partner-3", partnerName: "Arjun S.", zone: "D7E9", eventType: "outage", eventName: "App Outage", amount: 45, timestamp: "Mon 10:00 AM", status: "paid", txHash: "MOCK-OUTG-c5f3d2e7", city: "Delhi", duration: "30 min", partnerCount: 45 },
  { id: "p4", partnerId: "partner-4", partnerName: "Divya R.", zone: "C3F1", eventType: "aqi", eventName: "Delhi AQI Spike", amount: 40, timestamp: "Sun 2:00 PM", status: "paid", txHash: "MOCK-AQII-d6g4e3f6", city: "Delhi", duration: "1.5 hours", partnerCount: 156 },
  { id: "p5", partnerId: "partner-5", partnerName: "Karan P.", zone: "E5A2", eventType: "rain", eventName: "Chennai Heavy Rain", amount: 55, timestamp: "Sat 11:00 AM", status: "paid", txHash: "MOCK-RAIN-e7h5f4g5", city: "Chennai", duration: "2 hours", partnerCount: 178 },
  { id: "p6", partnerId: "partner-6", partnerName: "Meera N.", zone: "F8B3", eventType: "heat", eventName: "Hyderabad Heat Wave", amount: 30, timestamp: "Fri 4:30 PM", status: "paid", txHash: "MOCK-HEAT-f8i6g5h4", city: "Hyderabad", duration: "1 hour", partnerCount: 67 },
  { id: "p7", partnerId: "partner-7", partnerName: "Suresh B.", zone: "B4F2", eventType: "outage", eventName: "Swiggy Outage", amount: 45, timestamp: "Thu 9:00 AM", status: "paid", txHash: "MOCK-OUTG-g9j7h6i3", city: "Bengaluru", duration: "40 min", partnerCount: 112 },
  { id: "p8", partnerId: "partner-8", partnerName: "Anita V.", zone: "A2C1", eventType: "rain", eventName: "Mumbai Monsoon", amount: 60, timestamp: "Wed 1:00 PM", status: "paid", txHash: "MOCK-RAIN-h0k8i7j2", city: "Mumbai", duration: "2.5 hours", partnerCount: 290 },
];

export const mockTimelinePayouts: Payout[] = [
  { id: "tl1", partnerId: "", partnerName: "", zone: "B4F2", eventType: "rain", eventName: "Bengaluru Rainfall", amount: 11700, timestamp: "Today 3:00 PM", status: "paid", txHash: "MOCK-RAIN-001", city: "Bengaluru", duration: "2 hours", partnerCount: 234 },
  { id: "tl2", partnerId: "", partnerName: "", zone: "A2C1", eventType: "heat", eventName: "Mumbai Heat", amount: 3115, timestamp: "Today 11:00 AM", status: "paid", txHash: "MOCK-HEAT-002", city: "Mumbai", duration: "1 hour", partnerCount: 89 },
  { id: "tl3", partnerId: "", partnerName: "", zone: "D7E9", eventType: "aqi", eventName: "Delhi AQI", amount: 6240, timestamp: "Yesterday", status: "paid", txHash: "MOCK-AQII-003", city: "Delhi", duration: "3 hours", partnerCount: 156 },
  { id: "tl4", partnerId: "", partnerName: "", zone: "C3F1", eventType: "outage", eventName: "Chennai App Outage", amount: 2450, timestamp: "Yesterday", status: "paid", txHash: "MOCK-OUTG-004", city: "Chennai", duration: "45 min", partnerCount: 70 },
  { id: "tl5", partnerId: "", partnerName: "", zone: "E5A2", eventType: "rain", eventName: "Hyderabad Rain", amount: 8900, timestamp: "2 days ago", status: "paid", txHash: "MOCK-RAIN-005", city: "Hyderabad", duration: "2 hours", partnerCount: 178 },
  { id: "tl6", partnerId: "", partnerName: "", zone: "F8B3", eventType: "heat", eventName: "Pune Heat Alert", amount: 4200, timestamp: "3 days ago", status: "paid", txHash: "MOCK-HEAT-006", city: "Pune", duration: "1.5 hours", partnerCount: 120 },
  { id: "tl7", partnerId: "", partnerName: "", zone: "B4F2", eventType: "aqi", eventName: "Kolkata AQI", amount: 5670, timestamp: "4 days ago", status: "paid", txHash: "MOCK-AQII-007", city: "Kolkata", duration: "2 hours", partnerCount: 135 },
  { id: "tl8", partnerId: "", partnerName: "", zone: "A2C1", eventType: "rain", eventName: "Mumbai Heavy Rain", amount: 15400, timestamp: "5 days ago", status: "paid", txHash: "MOCK-RAIN-008", city: "Mumbai", duration: "4 hours", partnerCount: 310 },
];

export const mockFraudAlerts: FraudAlert[] = [
  { id: "fa1", partnerId: "partner-12", partnerName: "Rohan T.", rule: "wrong_zone", severity: "critical", timestamp: "2 min ago", status: "pending", lat: 12.9352, lng: 77.6245, details: "GPS coordinates outside claimed zone B4F2" },
  { id: "fa2", partnerId: "partner-15", partnerName: "Nikhil R.", rule: "stationary_device", severity: "critical", timestamp: "5 min ago", status: "pending", lat: 19.0760, lng: 72.8777, details: "Device stationary for 45min during claimed disruption" },
  { id: "fa3", partnerId: "partner-8", partnerName: "Anita V.", rule: "no_pre_activity", severity: "warning", timestamp: "15 min ago", status: "pending", lat: 13.0827, lng: 80.2707, details: "No delivery activity 2hr before claiming disruption" },
  { id: "fa4", partnerId: "partner-22", partnerName: "Rekha D.", rule: "velocity_abuse", severity: "warning", timestamp: "28 min ago", status: "pending", lat: 28.6139, lng: 77.2090, details: "3 claims in 24hr exceeds threshold" },
  { id: "fa5", partnerId: "partner-30", partnerName: "Ajay B.", rule: "multi_account", severity: "info", timestamp: "1 hr ago", status: "dismissed", lat: 12.9716, lng: 77.5946, details: "Same device ID registered under 2 accounts" },
  { id: "fa6", partnerId: "partner-45", partnerName: "Vijay C.", rule: "no_pre_activity", severity: "info", timestamp: "2 hr ago", status: "dismissed", lat: 17.3850, lng: 78.4867, details: "No delivery activity before claim" },
];

export const EVENT_ICONS: Record<string, string> = {
  rain: "🌧",
  heat: "🌡",
  aqi: "💨",
  outage: "📱",
  traffic: "🚦",
};

export const EVENT_COLORS: Record<string, string> = {
  rain: "bg-blue-100 text-blue-700",
  heat: "bg-orange-100 text-orange-700",
  aqi: "bg-purple-100 text-purple-700",
  outage: "bg-violet-100 text-violet-700",
  traffic: "bg-amber-100 text-amber-700",
};

// Generate chart data
export function generateLossRatioData(days: number = 30) {
  return Array.from({ length: days }, (_, i) => ({
    date: new Date(Date.now() - (days - 1 - i) * 86400000).toLocaleDateString("en-IN", { day: "2-digit", month: "short" }),
    ratio: Number((45 + Math.random() * 20).toFixed(1)),
  }));
}

export function generatePremiumPayoutData(weeks: number = 8) {
  return Array.from({ length: weeks }, (_, i) => ({
    week: `W${i + 1}`,
    premium: Math.floor(180000 + Math.random() * 80000),
    payouts: Math.floor(90000 + Math.random() * 60000),
  }));
}

export function generatePartnerGrowthData(days: number = 30) {
  const base = 38000;
  return Array.from({ length: days }, (_, i) => ({
    date: new Date(Date.now() - (days - 1 - i) * 86400000).toLocaleDateString("en-IN", { day: "2-digit", month: "short" }),
    partners: Math.floor(base + (i / days) * 4800 + Math.random() * 500),
  }));
}

// ← Fixed: added count + growth fields required by PartnersPage
export const topZonesData = [
  { zone: "B4F2", count: 8420, growth: 12, payouts: 245000 },
  { zone: "A2C1", count: 6310, growth: 9,  payouts: 198000 },
  { zone: "D7E9", count: 5870, growth: 15, payouts: 176000 },
  { zone: "C3F1", count: 4200, growth: 7,  payouts: 154000 },
  { zone: "E5A2", count: 3950, growth: 11, payouts: 132000 },
  { zone: "F8B3", count: 3100, growth: 8,  payouts: 118000 },
  { zone: "G2D4", count: 2800, growth: 5,  payouts: 95000  },
  { zone: "H1E6", count: 2400, growth: 6,  payouts: 78000  },
  { zone: "I9F7", count: 1900, growth: 4,  payouts: 62000  },
  { zone: "J3A8", count: 1500, growth: 3,  payouts: 45000  },
];

export const weeklyForecast = [
  { day: "Mon", weather: "🌧", risk: "high",   amount: 24 },
  { day: "Tue", weather: "☀️", risk: "low",    amount: 12 },
  { day: "Wed", weather: "🌡", risk: "medium", amount: 18 },
  { day: "Thu", weather: "🌧", risk: "high",   amount: 24 },
  { day: "Fri", weather: "☀️", risk: "low",    amount: 12 },
  { day: "Sat", weather: "💨", risk: "medium", amount: 18 },
  { day: "Sun", weather: "☀️", risk: "low",    amount: 12 },
];

export const mockHexCells = [
  { h3Index: "882a1008a3fffff", lat: 12.9716, lng: 77.5946, score: 0.72, zoneName: "B4F2", event: "Rain Disruption", rate: 50 },
  { h3Index: "882a1008a7fffff", lat: 12.9816, lng: 77.6046, score: 0.85, zoneName: "A2C1", event: "Clear", rate: 35 },
  { h3Index: "882a1008abfffff", lat: 12.9616, lng: 77.5846, score: 0.35, zoneName: "D7E9", event: "Heat Alert", rate: 45 },
  { h3Index: "882a1008affffff", lat: 12.9516, lng: 77.6146, score: 0.55, zoneName: "C3F1", event: "AQI Warning", rate: 40 },
  { h3Index: "882a1008b3fffff", lat: 12.9916, lng: 77.5746, score: 0.92, zoneName: "E5A2", event: "Clear", rate: 30 },
  { h3Index: "882a1008b7fffff", lat: 12.9416, lng: 77.5546, score: 0.28, zoneName: "F8B3", event: "App Outage", rate: 55 },
  { h3Index: "882a1008bbfffff", lat: 12.9316, lng: 77.6246, score: 0.65, zoneName: "G2D4", event: "Light Rain", rate: 38 },
  { h3Index: "882a1008bffffff", lat: 13.0016, lng: 77.5646, score: 0.45, zoneName: "H1E6", event: "Heat Advisory", rate: 42 },
  { h3Index: "882a1008c3fffff", lat: 12.9216, lng: 77.6346, score: 0.78, zoneName: "I9F7", event: "Clear", rate: 32 },
  { h3Index: "882a1008c7fffff", lat: 13.0116, lng: 77.6446, score: 0.18, zoneName: "J3A8", event: "Heavy Rain", rate: 60 },
  { h3Index: "882a1008cbfffff", lat: 12.9116, lng: 77.5446, score: 0.62, zoneName: "K5B9", event: "Moderate Wind", rate: 36 },
  { h3Index: "882a1008cffffff", lat: 13.0216, lng: 77.5546, score: 0.88, zoneName: "L7C2", event: "Clear", rate: 28 },
  { h3Index: "882a1008d3fffff", lat: 12.9016, lng: 77.6546, score: 0.42, zoneName: "M8D3", event: "AQI Alert", rate: 48 },
  { h3Index: "882a1008d7fffff", lat: 13.0316, lng: 77.5346, score: 0.73, zoneName: "N1E4", event: "Light Rain", rate: 34 },
  { h3Index: "882a1008dbfffff", lat: 12.8916, lng: 77.6646, score: 0.31, zoneName: "O4F5", event: "Storm", rate: 65 },
  { h3Index: "882a1008dffffff", lat: 13.0416, lng: 77.5246, score: 0.81, zoneName: "P6A7", event: "Clear", rate: 30 },
  { h3Index: "882a1008e3fffff", lat: 12.8816, lng: 77.5146, score: 0.56, zoneName: "Q2B8", event: "Heat", rate: 44 },
  { h3Index: "882a1008e7fffff", lat: 13.0516, lng: 77.6746, score: 0.69, zoneName: "R9C1", event: "Drizzle", rate: 38 },
  { h3Index: "882a1008ebfffff", lat: 12.8716, lng: 77.5046, score: 0.47, zoneName: "S3D6", event: "AQI Warning", rate: 42 },
  { h3Index: "882a1008effffff", lat: 13.0616, lng: 77.6846, score: 0.91, zoneName: "T8E2", event: "Clear", rate: 25 },
];

export const mockAccelerometerData = Array.from({ length: 30 }, (_, i) => ({
  time: `${i}s`,
  value: i > 10 && i < 20 ? 0.05 + Math.random() * 0.08 : 0.3 + Math.random() * 0.4,
}));

export function formatINR(amount: number): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(amount);
}

export function formatINRCompact(amount: number): string {
  if (amount >= 100000) return `₹${(amount / 100000).toFixed(1)}L`;
  if (amount >= 1000) return `₹${(amount / 1000).toFixed(1)}K`;
  return `₹${amount}`;
}

export const mockFraudData = {
  riskScores: [
    { range: "0-20",   count: 450 },
    { range: "21-40",  count: 320 },
    { range: "41-60",  count: 180 },
    { range: "61-80",  count: 85  },
    { range: "81-100", count: 42  },
  ],
  flaggedPartners: [
    { id: "P-8821", name: "Suresh Kumar", zone: "B4F2", frequency: "4 claims/wk", score: 92 },
    { id: "P-4492", name: "Anita Singh",  zone: "A2C1", frequency: "3 claims/wk", score: 84 },
    { id: "P-1103", name: "Vikram Das",   zone: "D7E9", frequency: "5 claims/mo", score: 76 },
    { id: "P-5561", name: "Rahul Jain",   zone: "C3F1", frequency: "2 claims/wk", score: 68 },
  ],
};