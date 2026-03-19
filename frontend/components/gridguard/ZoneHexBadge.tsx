"use client";

interface ZoneHexBadgeProps {
  zone: string;
  className?: string;
}

export default function ZoneHexBadge({ zone, className = "" }: ZoneHexBadgeProps) {
  return (
    <span
      className={`
        inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold
        bg-navy/10 text-navy border border-navy/20
        ${className}
      `}
    >
      <svg className="w-3 h-3 mr-1.5" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 2L21.5 7.5V16.5L12 22L2.5 16.5V7.5L12 2Z" />
      </svg>
      {zone}
    </span>
  );
}
