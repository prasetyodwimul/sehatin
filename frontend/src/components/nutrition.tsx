import Link from "next/link";
import { Badge, Card } from "./ui";

type NutritionCategory = "mpasi" | "toddler" | "lansia";

export function NutritionCard({
  category,
  title,
  description,
  ctaLabel,
  href,
}: {
  category: NutritionCategory;
  title: string;
  description: string;
  ctaLabel: string;
  href: string;
}) {
  return (
    <Link href={href} className="block h-full focus-visible:outline-none">
      <Card interactive large className="flex h-full flex-col">
        <Badge variant="neutral">{category.toUpperCase()}</Badge>
        <h2 className="mt-3 text-xl font-semibold text-text">{title}</h2>
        <p className="mt-2 flex-1 text-sm leading-6 text-secondary">{description}</p>
        <span className="mt-4 inline-block text-sm font-medium text-primary-dark">{ctaLabel} →</span>
      </Card>
    </Link>
  );
}
