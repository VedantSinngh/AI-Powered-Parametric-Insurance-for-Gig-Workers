"use client";

interface ConnectionStatusProps {
  isLive?: boolean;
  label?: string;
}

export default function ConnectionStatus({ isLive = true, label = "Live" }: ConnectionStatusProps) {
  return (
    <div className="flex items-center gap-1.5">
      <span className="relative flex h-2.5 w-2.5">
        {isLive && (
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
        )}
        <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${isLive ? "bg-green-500" : "bg-gray-400"}`} />
      </span>
      <span className={`text-xs font-medium ${isLive ? "text-green-600" : "text-gray-500"}`}>
        {label}
      </span>
    </div>
  );
}
