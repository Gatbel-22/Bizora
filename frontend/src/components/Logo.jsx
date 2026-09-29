export default function Logo({ className = "" }) {
  return (
    <span
      className={`inline-flex items-center gap-2 text-2xl font-bold tracking-tight ${className}`}
    >
      <span
        aria-hidden="true"
        className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-700 text-white"
      >
        B
      </span>
      <span>Bizora</span>
    </span>
  );
}
