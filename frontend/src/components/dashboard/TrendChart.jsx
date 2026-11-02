import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatCompact, formatMoney, formatShortDate } from "../../utils/format";

// One bar per day. Negative bars (a loss) are drawn in red below the zero line.
export default function TrendChart({ title, summary, data, dataKey, currency, color = "#0f766e" }) {
  return (
    <figure className="rounded-xl border border-slate-200 bg-white p-4">
      <figcaption className="mb-3 text-sm font-semibold text-slate-800">{title}</figcaption>
      <div role="img" aria-label={summary} className="h-56 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="#e2e8f0" vertical={false} />
            <XAxis
              dataKey="date"
              tickFormatter={formatShortDate}
              minTickGap={24}
              tick={{ fontSize: 12 }}
            />
            <YAxis tickFormatter={formatCompact} width={52} tick={{ fontSize: 12 }} />
            <Tooltip
              formatter={(value) => formatMoney(value, currency)}
              labelFormatter={formatShortDate}
            />
            <ReferenceLine y={0} stroke="#94a3b8" />
            <Bar dataKey={dataKey} radius={[3, 3, 0, 0]}>
              {data.map((entry) => (
                <Cell key={entry.date} fill={Number(entry[dataKey]) < 0 ? "#dc2626" : color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </figure>
  );
}
