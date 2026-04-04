"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { ChevronDown } from "lucide-react";

interface AccordionItemProps {
  title: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
}

export function AccordionItem({ title, children, defaultOpen = false }: AccordionItemProps) {
  const [open, setOpen] = React.useState(defaultOpen);
  return (
    <div className="border-b">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between py-4 text-sm font-medium transition-all hover:underline"
      >
        {title}
        <ChevronDown className={cn("h-4 w-4 shrink-0 transition-transform duration-200", open && "rotate-180")} />
      </button>
      {open && <div className="pb-4 pt-0 text-sm">{children}</div>}
    </div>
  );
}

export function Accordion({ children, className }: { children: React.ReactNode; className?: string }) {
  return <div className={cn("w-full", className)}>{children}</div>;
}
