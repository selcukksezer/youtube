import * as React from "react";
import { cn } from "@/lib/utils";

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, type, ...props }, ref) => (
    <input
      ref={ref}
      type={type}
      className={cn(
        "flex h-9 w-full rounded-[10px] border border-border bg-surface px-3 py-1 text-[13px] text-foreground placeholder:text-muted-2",
        "shadow-[inset_0_1px_2px_rgba(19,24,41,0.04)] hover:border-border-strong",
        "focus:border-primary focus:outline-none focus:ring-[3px] focus:ring-primary/15 focus:shadow-none",
        "disabled:cursor-not-allowed disabled:opacity-60 disabled:bg-surface-2",
        "aria-[invalid=true]:border-danger aria-[invalid=true]:ring-danger/15",
        className
      )}
      {...props}
    />
  )
);
Input.displayName = "Input";
