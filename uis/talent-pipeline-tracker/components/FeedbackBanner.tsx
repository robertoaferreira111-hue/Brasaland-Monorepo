type FeedbackBannerProps = {
  tone: "info" | "success" | "error";
  message: string;
};

const toneClasses: Record<FeedbackBannerProps["tone"], string> = {
  info: "border-[var(--border)] bg-[var(--surface-muted)] text-[var(--ink)]",
  success: "border-emerald-300 bg-emerald-50 text-emerald-900",
  error: "border-red-300 bg-red-50 text-red-900",
};

export function FeedbackBanner({ tone, message }: FeedbackBannerProps) {
  return (
    <div
      role={tone === "error" ? "alert" : "status"}
      className={`rounded-md border px-3 py-2 text-sm ${toneClasses[tone]}`}
    >
      {message}
    </div>
  );
}
