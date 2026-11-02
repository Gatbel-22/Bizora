import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as dashboardApi from "../api/dashboard";
import { AuthContext } from "../context/authContext";
import DashboardPage from "./DashboardPage";

vi.mock("../api/dashboard");
vi.mock("../components/dashboard/TrendChart", () => ({ default: () => null }));

const figures = {
  revenue: "1250000.00",
  cost_of_goods_sold: "800000.00",
  gross_profit: "450000.00",
  gross_margin_percent: 36.0,
  operating_expenses: "300000.00",
  other_spending: "50000.00",
  total_spending: "350000.00",
  estimated_net_profit: "150000.00",
  credit_sales: "200000.00",
  sales_count: 48,
  average_sale: "26041.67",
};

const dashboard = {
  currency: "SSP",
  period: { name: "this_month", start: "2026-10-01", end: "2026-10-14", days: 14 },
  today: {
    date: "2026-10-14",
    sales_total: "45000.00",
    sales_count: 6,
    total_spending: "12000.00",
  },
  figures,
  previous: figures,
  changes: {
    revenue: 18.0,
    gross_profit: 10.0,
    operating_expenses: 31.0,
    total_spending: 25.0,
    estimated_net_profit: -5.0,
  },
  daily: [
    {
      date: "2026-10-13",
      revenue: "1000.00",
      total_spending: "0.00",
      gross_profit: "400.00",
      operating_expenses: "0.00",
      net_profit: "400.00",
    },
  ],
  top_products: [
    {
      product: "p1",
      name: "Cola 500ml",
      quantity: "120.000",
      revenue: "120000.00",
      profit: "48000.00",
    },
  ],
  sales_by_category: [{ category: "Beverages", revenue: "300000.00" }],
  receivables: { outstanding: "850000.00", overdue_amount: "500000.00", overdue_customers: 2 },
  inventory: {
    value: "2400000.00",
    low_stock_count: 3,
    out_of_stock_count: 1,
    needs_restock: [
      {
        id: "p2",
        name: "Water 1L",
        current_stock: "2.000",
        min_stock_threshold: "10.000",
        unit: "BOTTLE",
        status: "low",
      },
    ],
  },
  insights: [
    {
      type: "debt",
      severity: "WARNING",
      title: "Overdue customer debts",
      message: "2 customers have overdue balances totaling 500,000 SSP.",
      related: { type: "customers" },
    },
  ],
};

function renderPage(role = "OWNER") {
  const auth = {
    role,
    user: { full_name: "Gatbel Deng" },
    business: { id: "b1", name: "Test Mart", currency: "SSP" },
  };
  return render(
    <MemoryRouter>
      <AuthContext.Provider value={auth}>
        <DashboardPage />
      </AuthContext.Provider>
    </MemoryRouter>
  );
}

describe("DashboardPage", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("shows today's numbers, estimated profit and the profit breakdown", async () => {
    dashboardApi.getDashboard.mockResolvedValue(dashboard);
    renderPage();
    expect(await screen.findByText("Today's sales")).toBeInTheDocument();
    expect(screen.getByText(/45,000/)).toBeInTheDocument();
    expect(screen.getByText("Today's expenses")).toBeInTheDocument();
    expect(screen.getAllByText("Estimate").length).toBeGreaterThan(0);
    expect(screen.getByText(/not audited accounting figures/)).toBeInTheDocument();
    expect(screen.getByText("Gross profit")).toBeInTheDocument();
  });

  it("shows how things changed compared with the previous period", async () => {
    dashboardApi.getDashboard.mockResolvedValue(dashboard);
    renderPage();
    await screen.findByText("Today's sales");
    expect(screen.getAllByText(/same days last month/).length).toBeGreaterThan(0);
  });

  it("shows insights with a clear severity label", async () => {
    dashboardApi.getDashboard.mockResolvedValue(dashboard);
    renderPage();
    expect(
      await screen.findByText("2 customers have overdue balances totaling 500,000 SSP.")
    ).toBeInTheDocument();
    expect(screen.getByText(/^Watch:/)).toBeInTheDocument();
  });

  it("says so when nothing needs attention", async () => {
    dashboardApi.getDashboard.mockResolvedValue({ ...dashboard, insights: [] });
    renderPage();
    expect(await screen.findByText("Nothing needs your attention right now.")).toBeInTheDocument();
  });

  it("lists products that need restocking", async () => {
    dashboardApi.getDashboard.mockResolvedValue(dashboard);
    renderPage();
    expect(await screen.findByText("Water 1L")).toBeInTheDocument();
    expect(screen.getByText("Low stock", { selector: "span" })).toBeInTheDocument();
  });

  it("shows a helpful empty state when nothing happened in the period", async () => {
    dashboardApi.getDashboard.mockResolvedValue({
      ...dashboard,
      figures: { ...figures, sales_count: 0, total_spending: "0.00" },
    });
    renderPage();
    expect(await screen.findByText("No activity in this period")).toBeInTheDocument();
  });

  it("loads the chosen time period", async () => {
    dashboardApi.getDashboard.mockResolvedValue(dashboard);
    const user = userEvent.setup();
    renderPage();
    await screen.findByText("Today's sales");
    await user.selectOptions(screen.getByLabelText("Time period"), "last_7_days");
    expect(dashboardApi.getDashboard).toHaveBeenLastCalledWith({ period: "last_7_days" });
  });

  it("recovers from a network error with Try again", async () => {
    dashboardApi.getDashboard
      .mockRejectedValueOnce(new Error("Network Error"))
      .mockResolvedValueOnce(dashboard);
    const user = userEvent.setup();
    renderPage();
    expect(await screen.findByText(/Can't reach the server/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByText("Today's sales")).toBeInTheDocument();
  });

  it("gives staff a simple home screen without any profit figures", async () => {
    renderPage("STAFF");
    expect(await screen.findByRole("link", { name: "New sale" })).toBeInTheDocument();
    expect(screen.queryByText("Estimated profit")).not.toBeInTheDocument();
    expect(dashboardApi.getDashboard).not.toHaveBeenCalled();
  });
});
