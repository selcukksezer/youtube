import * as React from "react";
import { cn } from "@/lib/utils";

export const Textarea = React.forwardRef<HTMLTextAreaElement, React.TextareaHTMLAttributes<HTMLTextAreaElement>>(
  ({ className, ...props }, ref) => (
    <textarea
      ref={ref}
      className={cn(
        "flex min-h-[72px] w-full rounded-[10px] border border-border bg-surface px-3 py-2 text-[13px] text-foreground placeholder:text-muted-2",
        "shadow-[inset_0_1px_2px_rgba(19,24,41,0.04)] hover:border-border-strong",
        "focus:border-primary focus:outline-none focus:ring-[3px] focus:ring-primary/15 focus:shadow-none resize-y leading-relaxed",
        "disabled:cursor-not-allowed disabled:opacity-60 disabled:bg-surface-2",
        className
      )}
      {...props}
    />
  )
);
Textarea.displayName = "Textarea";
