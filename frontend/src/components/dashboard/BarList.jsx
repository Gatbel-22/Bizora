export default function BarList({ items, emptyText }) {
  if (items.length === 0) return <p className="text-sm text-slate-600">{emptyText}</p>;
  const max = Math.max(...items.map((item) => item.value), 0);

  return (
    <ul className="space-y-3">
      {items.map((item) => (
        <li key={item.key}>
          <div className="flex justify-between gap-3 text-sm">
            <span className="min-w-0 truncate font-medium text-slate-900">{item.label}</span>
            <span className="shrink-0 font-semibold text-slate-900">{item.display}</span>
          </div>
          <div className="mt-1 h-2 rounded-full bg-slate-100" aria-hidden="true">
            <div
              className="h-2 rounded-full bg-brand-600"
              style={{ width: `${max > 0 ? Math.max((item.value / max) * 100, 2) : 0}%` }}
            />
          </div>
          {item.detail && <p className="mt-0.5 text-xs text-slate-600">{item.detail}</p>}
        </li>
      ))}
    </ul>
  );
}
