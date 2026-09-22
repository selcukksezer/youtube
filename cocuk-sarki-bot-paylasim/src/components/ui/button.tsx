"use client";

import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  [
    "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-[10px] text-sm font-medium select-none cursor-pointer",
    "focus-ring active:translate-y-px",
    "disabled:pointer-events-none disabled:opacity-50 disabled:shadow-none disabled:active:translate-y-0",
  ].join(" "),
  {
    variants: {
      variant: {
        // Birincil: duz kurumsal indigo — parlama yok, sade ve net
        default:
          "bg-primary text-white font-semibold shadow-[0_1px_2px_rgba(19,24,41,0.12)] hover:bg-primary-strong",
        secondary: "bg-surface-3 text-foreground border border-border hover:bg-surface-4 hover:border-border-strong",
        outline:
          "border border-border bg-surface text-foreground shadow-[0_1px_2px_rgba(19,24,41,0.04)] hover:bg-surface-2 hover:border-border-strong hover:shadow-[0_2px_6px_rgba(19,24,41,0.07)]",
        ghost: "text-muted hover:text-foreground hover:bg-surface-3",
        danger: "bg-danger-soft text-danger border border-danger/25 hover:border-danger/40 hover:brightness-[0.98]",
        success: "bg-success-soft text-success border border-success/25 hover:border-success/40 hover:brightness-[0.98]",
      },
      size: {
        default: "h-9 px-4",
        sm: "h-8 px-3 text-xs",
        lg: "h-10 px-6 text-[14px]",
        icon: "h-9 w-9",
      },
    },
    defaultVariants: { variant: "default", size: "default" },
  }
);

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {
  loading?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, loading, disabled, children, ...props }, ref) => (
    <button ref={ref} className={cn(buttonVariants({ variant, size }), className)} disabled={disabled || loading} {...props}>
      {loading && <Loader2 className="h-4 w-4 animate-spin" />}
      {children}
    </button>
  )
);
Button.displayName = "Button";
