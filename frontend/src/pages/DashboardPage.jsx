import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { getDashboard } from "../api/dashboard";
import BarList from "../components/dashboard/BarList";
import InsightList from "../components/dashboard/InsightList";
import LowStockList from "../components/dashboard/LowStockList";
import ProfitBreakdown from "../components/dashboard/ProfitBreakdown";
import StatCard from "../components/dashboard/StatCard";
import TrendChart from "../components/dashboard/TrendChart";
import Alert from "../components/ui/Alert";
import Button from "../components/ui/Button";
import EmptyState from "../components/ui/EmptyState";
import SelectField from "../components/ui/SelectField";
import Spinner from "../components/ui/Spinner";
import { ROLES } from "../config/roles";
import useAuth from "../hooks/useAuth";
import useFetch from "../hooks/useFetch";
import { t } from "../i18n";
import { getErrorMessage } from "../utils/errors";
import { formatMoney, formatQuantity } from "../utils/format";

const PERIODS = ["today", "last_7_days", "this_month", "last_30_days", "last_month"];

const PRIMARY_LINK =
  "inline-flex min-h-11 items-center justify-center rounded-lg bg-brand-700 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-900";
const SECONDARY_LINK =
  "inline-flex min-h-11 items-center justify-center rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-800 hover:bg-slate-50";

function StaffHome({ user, business }) {
  const firstName = user.full_name.trim().split(" ")[0];
  return (
    <>
      <header className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">
          {t("dashboard.greeting", { name: firstName })}
        </h1>
        <p className="mt-1 text-slate-600">
          {business.name} · {t("dashboard.staff.subtitle")}
        </p>
      </header>
      <div className="grid gap-3 sm:grid-cols-3">
        <Link to="/sales/new" className={PRIMARY_LINK}>
          {t("dashboard.staff.newSale")}
        </Link>
        <Link to="/products" className={SECONDARY_LINK}>
          {t("dashboard.staff.products")}
        </Link>
        <Link to="/customers" className={SECONDARY_LINK}>
          {t("dashboard.staff.customers")}
        </Link>
      </div>
    </>
  );
}

function ManagerDashboard({ user, business, role }) {
  const [period, setPeriod] = useState("this_month");
  const dashboard = useFetch(() => getDashboard({ period }), `dashboard-${period}`);
  const data = dashboard.data;
  const currency = business.currency;
  const money = (value) => formatMoney(value, currency);
  const firstName = user.full_name.trim().split(" ")[0];

  const chartData = useMemo(
    () =>
      (data?.daily ?? []).map((day) => ({
        date: day.date,
        revenue: Number(day.revenue),
        total_spending: Number(day.total_spending),
        net_profit: Number(day.net_profit),
      })),
    [data]
  );

  const periodOptions = PERIODS.map((value) => ({ value, label: t(`dashboard.period.${value}`) }));

  const header = (
    <header className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">
          {t("dashboard.greeting", { name: firstName })}
        </h1>
        <p className="mt-1 text-slate-600">
          {business.name} · {t(`role.${role}`)}
        </p>
      </div>
      <SelectField
        className="w-full sm:w-52"
        label={t("dashboard.period.label")}
        options={periodOptions}
        value={period}
        onChange={(event) => setPeriod(event.target.value)}
      />
    </header>
  );

  if (!data) {
    return (
      <>
        {header}
        {dashboard.error ? (
          <Alert>
            {t("dashboard.loadError")} {getErrorMessage(dashboard.error)}{" "}
            <button type="button" onClick={dashboard.reload} className="font-semibold underline">
              {t("common.tryAgain")}
            </button>
          </Alert>
        ) : (
          <div role="status" className="flex justify-center py-16 text-brand-700">
            <Spinner className="h-8 w-8" />
          </div>
        )}
      </>
    );
  }

  const f = data.figures;
  const c = data.changes;
  const compare = t(`dashboard.compare.${data.period.name}`);
  const isEmpty = f.sales_count === 0 && Number(f.total_spending) === 0;
  const margin = f.gross_margin_percent;

  const topItems = data.top_products.map((product) => ({
    key: product.product,
    label: product.name,
    value: Number(product.revenue),
    display: money(product.revenue),
    detail: `${t("dashboard.top.units", { qty: formatQuantity(product.quantity) })} · ${t(
      "dashboard.top.profit",
      { amount: money(product.profit) }
    )}`,
  }));

  const categoryTotal = data.sales_by_category.reduce((sum, item) => sum + Number(item.revenue), 0);
  const categoryItems = data.sales_by_category.map((item) => ({
    key: item.category ?? "uncategorized",
    label: item.category ?? t("dashboard.uncategorized"),
    value: Number(item.revenue),
    display: money(item.revenue),
    detail: `${categoryTotal > 0 ? Math.round((Number(item.revenue) / categoryTotal) * 100) : 0}%`,
  }));

  const restockCount = data.inventory.low_stock_count + data.inventory.out_of_stock_count;
  const debt = data.receivables;

  return (
    <>
      {header}

      {dashboard.error && (
        <Alert className="mb-4">
          {t("dashboard.loadError")} {getErrorMessage(dashboard.error)}{" "}
          <button type="button" onClick={dashboard.reload} className="font-semibold underline">
            {t("common.tryAgain")}
          </button>
        </Alert>
      )}

      <div
        aria-busy={dashboard.loading}
        className={dashboard.loading ? "opacity-60 transition-opacity" : ""}
      >
        <section aria-label={t("dashboard.today")} className="mb-6 grid gap-3 sm:grid-cols-2">
          <StatCard
            label={t("dashboard.todaySales")}
            value={money(data.today.sales_total)}
            hint={t("dashboard.salesCount", { count: data.today.sales_count })}
          />
          <StatCard label={t("dashboard.todayExpenses")} value={money(data.today.total_spending)} />
        </section>

        <section aria-labelledby="insights-heading" className="mb-6">
          <h2 id="insights-heading" className="mb-2 text-lg font-semibold text-slate-900">
            {t("dashboard.insights.title")}
          </h2>
          <InsightList insights={data.insights} />
        </section>

        <section
          aria-label={t(`dashboard.period.${data.period.name}`)}
          className="mb-6 grid gap-3 sm:grid-cols-3"
        >
          <StatCard
            label={t("dashboard.sales")}
            value={money(f.revenue)}
            change={c.revenue}
            compareLabel={compare}
            hint={t("dashboard.salesCount", { count: f.sales_count })}
          />
          <StatCard
            label={t("dashboard.expenses")}
            value={money(f.total_spending)}
            change={c.total_spending}
            compareLabel={compare}
            upIsGood={false}
            hint={
              Number(f.other_spending) > 0
                ? t("dashboard.notCounted", { amount: money(f.other_spending) })
                : undefined
            }
          />
          <StatCard
            label={t("dashboard.estimatedProfit")}
            value={money(f.estimated_net_profit)}
            change={c.estimated_net_profit}
            compareLabel={compare}
            estimate
            hint={margin !== null ? t("dashboard.margin", { percent: margin }) : undefined}
          />
        </section>

        <div className="mb-6 grid gap-4 lg:grid-cols-2">
          <ProfitBreakdown figures={f} currency={currency} />
          <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-1">
            <StatCard
              label={t("dashboard.debt.title")}
              value={money(debt.outstanding)}
              hint={
                Number(debt.overdue_amount) > 0
                  ? t("dashboard.debt.overdue", { amount: money(debt.overdue_amount) })
                  : Number(debt.outstanding) === 0
                    ? t("dashboard.debt.none")
                    : undefined
              }
            />
            <StatCard
              label={t("dashboard.inventory.title")}
              value={money(data.inventory.value)}
              hint={t("dashboard.inventory.hint")}
            />
            <StatCard
              label={t("dashboard.lowStock.title")}
              value={String(restockCount)}
              hint={t("dashboard.lowStock.hint", {
                low: data.inventory.low_stock_count,
                out: data.inventory.out_of_stock_count,
              })}
            />
          </div>
        </div>

        {isEmpty ? (
          <EmptyState title={t("dashboard.empty.title")} message={t("dashboard.empty.message")}>
            <Link to="/sales/new" className={PRIMARY_LINK}>
              {t("dashboard.staff.newSale")}
            </Link>
          </EmptyState>
        ) : (
          <div className="mb-6 grid gap-4 lg:grid-cols-2">
            <TrendChart
              title={t("dashboard.chart.sales")}
              summary={t("dashboard.chart.summary", {
                title: t("dashboard.chart.sales"),
                total: money(f.revenue),
              })}
              data={chartData}
              dataKey="revenue"
              currency={currency}
            />
            <TrendChart
              title={t("dashboard.chart.expenses")}
              summary={t("dashboard.chart.summary", {
                title: t("dashboard.chart.expenses"),
                total: money(f.total_spending),
              })}
              data={chartData}
              dataKey="total_spending"
              currency={currency}
              color="#b45309"
            />
            <div className="lg:col-span-2">
              <TrendChart
                title={t("dashboard.chart.profit")}
                summary={t("dashboard.chart.summary", {
                  title: t("dashboard.chart.profit"),
                  total: money(f.estimated_net_profit),
                })}
                data={chartData}
                dataKey="net_profit"
                currency={currency}
              />
            </div>
          </div>
        )}

        <div className="mb-6 grid gap-4 lg:grid-cols-2">
          <section
            aria-labelledby="top-heading"
            className="rounded-xl border border-slate-200 bg-white p-4"
          >
            <h2 id="top-heading" className="mb-3 text-base font-semibold text-slate-900">
              {t("dashboard.top.title")}
            </h2>
            <BarList items={topItems} emptyText={t("dashboard.noData")} />
          </section>
          <section
            aria-labelledby="category-heading"
            className="rounded-xl border border-slate-200 bg-white p-4"
          >
            <h2 id="category-heading" className="mb-3 text-base font-semibold text-slate-900">
              {t("dashboard.category.title")}
            </h2>
            <BarList items={categoryItems} emptyText={t("dashboard.noData")} />
          </section>
        </div>

        <section
          aria-labelledby="restock-heading"
          className="rounded-xl border border-slate-200 bg-white p-4"
        >
          <h2 id="restock-heading" className="mb-2 text-base font-semibold text-slate-900">
            {t("dashboard.lowStock.title")}
          </h2>
          <LowStockList items={data.inventory.needs_restock} />
        </section>
      </div>
    </>
  );
}

export default function DashboardPage() {
  const { user, business, role } = useAuth();
  if (role === ROLES.STAFF) return <StaffHome user={user} business={business} />;
  return <ManagerDashboard user={user} business={business} role={role} />;
}
