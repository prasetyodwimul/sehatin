export type ButtonVariant = "primary" | "secondary" | "ghost" | "destructive";
export type ButtonSize = "sm" | "md" | "lg";

const buttonVariantClasses: Record<ButtonVariant, string> = {
  primary: "bg-primary text-white hover:bg-primary-dark shadow-[0_8px_22px_rgba(15,118,110,.15)] disabled:bg-muted",
  secondary: "bg-transparent text-primary-dark border border-primary/45 hover:bg-primary-light disabled:border-muted disabled:text-muted",
  ghost: "bg-transparent text-secondary hover:bg-primary-light/50 hover:text-primary-dark disabled:text-muted",
  destructive: "bg-error text-white hover:bg-error/90 disabled:bg-muted",
};
const buttonSizeClasses: Record<ButtonSize, string> = {
  sm: "min-h-10 px-4 py-2 text-sm",
  md: "min-h-11 px-5 py-2.5 text-sm",
  lg: "min-h-12 px-6 py-3 text-base",
};

export function getButtonClasses({ variant = "primary", size = "md", className = "" }: { variant?: ButtonVariant; size?: ButtonSize; className?: string } = {}) {
  return `inline-flex items-center justify-center gap-2 rounded-full font-semibold transition-all duration-300 ease-out hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-70 disabled:hover:translate-y-0 ${buttonVariantClasses[variant]} ${buttonSizeClasses[size]} ${className}`;
}
