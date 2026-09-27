import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { getButtonClasses } from "@/components/button-styles";

export function Eyebrow({ children }: { children: React.ReactNode }) {
  return <p className="eyebrow">{children}</p>;
}

export function EditorialHeader({
  eyebrow,
  title,
  description,
  align = "left",
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  align?: "left" | "center";
}) {
  return (
    <div className={align === "center" ? "mx-auto max-w-3xl text-center" : "max-w-3xl"}>
      {eyebrow && <Eyebrow>{eyebrow}</Eyebrow>}
      <h1 className="display-title mt-4">{title}</h1>
      {description && <p className="lede mt-5">{description}</p>}
    </div>
  );
}

export function SectionIntro({
  eyebrow,
  title,
  body,
}: {
  eyebrow: string;
  title: string;
  body?: string;
}) {
  return (
    <div className="max-w-3xl">
      <Eyebrow>{eyebrow}</Eyebrow>
      <h2 className="section-title mt-3">{title}</h2>
      {body && <p className="mt-4 max-w-2xl text-base leading-7 text-secondary md:text-lg">{body}</p>}
    </div>
  );
}

export function TextLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link href={href} className="group inline-flex min-h-11 items-center gap-2 text-sm font-semibold text-primary-dark underline decoration-primary/30 underline-offset-4 transition-colors hover:decoration-primary">
      {children}<ArrowUpRight size={16} className="transition-transform duration-300 group-hover:-translate-y-0.5 group-hover:translate-x-0.5" aria-hidden="true" />
    </Link>
  );
}

export function ActionLink({ href, children, secondary = false }: { href: string; children: React.ReactNode; secondary?: boolean }) {
  return <Link href={href} className={getButtonClasses({ variant: secondary ? "secondary" : "primary", size: "lg" })}>{children}</Link>;
}

export function ResultSection({
  eyebrow,
  title,
  children,
  className = "",
}: {
  eyebrow: string;
  title: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={`result-section ${className}`}>
      <div className="result-section-label">
        <span>{eyebrow}</span>
      </div>
      <div className="result-section-content">
        <h2 className="text-2xl font-semibold tracking-tight text-text md:text-3xl">{title}</h2>
        <div className="mt-5">{children}</div>
      </div>
    </section>
  );
}
