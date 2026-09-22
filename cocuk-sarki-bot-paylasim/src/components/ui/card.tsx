import * as React from "react";
import { cn } from "@/lib/utils";

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Fare ile uzerine gelindiginde hafifce yukselir (tiklanabilir kartlar icin). */
  interactive?: boolean;
  /** Zemine gomulu, daha sakin yuzey (ic ice kart / yardim blogu). */
  muted?: boolean;
}

export function Card({ className, interactive, muted, ...props }: CardProps) {
  return (
    <div
      className={cn(
        "rounded-[16px] border border-border hairline-top",
        muted ? "bg-surface-2" : "bg-surface",
        "card-shadow",
        interactive && "cursor-pointer hover:border-border-strong hover:-translate-y-0.5 hover:card-shadow-hover",
        className
      )}
      {...props}
    />
  );
}

export function CardHeader({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("flex flex-col gap-1 px-5 pt-5 pb-3", className)} {...props} />;
}

export function CardTitle({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) {
  return <h3 className={cn("text-[14px] font-semibold tracking-[-0.01em] leading-snug", className)} {...props} />;
}

export function CardDescription({ className, ...props }: React.HTMLAttributes<HTMLParagraphElement>) {
  return <p className={cn("text-[11.5px] text-muted leading-relaxed", className)} {...props} />;
}

export function CardContent({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("px-5 pb-5 pt-2", className)} {...props} />;
}

export function CardFooter({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("flex items-center gap-2 px-5 pb-5 pt-0", className)} {...props} />;
}
