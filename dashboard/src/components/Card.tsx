interface CardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: "up" | "down" | "neutral";
}

export default function Card({ title, value, subtitle, trend }: CardProps) {
  const trendColor = trend === "up" ? "text-[var(--accent)]" : trend === "down" ? "text-[var(--accent-red)]" : "text-[var(--muted)]";

  return (
    <div className="bg-[var(--card)] border border-[var(--card-border)] rounded-xl p-5">
      <p className="text-xs text-[var(--muted)] uppercase tracking-wider mb-1">{title}</p>
      <p className={`text-2xl font-bold ${trendColor}`}>{value}</p>
      {subtitle && <p className="text-xs text-[var(--muted)] mt-1">{subtitle}</p>}
    </div>
  );
}
