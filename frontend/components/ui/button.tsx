import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-xl text-sm font-black tracking-[-0.01em] transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:pointer-events-none disabled:opacity-45",
  {
    variants: {
      variant: {
        default: "border border-primary/30 bg-primary text-primary-foreground shadow-[0_10px_35px_hsl(var(--primary)/0.18)] hover:-translate-y-0.5 hover:bg-primary/90 hover:shadow-[0_16px_45px_hsl(var(--primary)/0.28)]",
        outline: "border border-border/80 bg-card/[0.55] text-foreground shadow-[0_10px_30px_hsl(var(--primary)/0.045)] backdrop-blur-md hover:-translate-y-0.5 hover:border-primary/35 hover:bg-primary/10 hover:text-primary",
        ghost: "text-muted-foreground hover:-translate-y-0.5 hover:bg-card/[0.55] hover:text-foreground",
      },
      size: {
        default: "h-11 px-5 py-2.5",
        lg: "h-12 px-8",
        sm: "h-10 rounded-lg px-4",
      },
    },
    defaultVariants: { variant: "default", size: "default" },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  },
);
Button.displayName = "Button";

export { Button, buttonVariants };
