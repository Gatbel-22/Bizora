import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as expensesApi from "../api/expenses";
import * as inventoryApi from "../api/inventory";
import { AuthContext } from "../context/authContext";
import ExpensesPage from "./ExpensesPage";

vi.mock("../api/expenses");
vi.mock("../api/inventory");

const page = (results) => ({ count: results.length, next: null, previous: null, results });

const rent = {
  id: "e1",
  description: "Shop rent",
  category: "c1",
  category_name: "Rent",
  category_affects_profit: true,
  amount: "150000.00",
  expense_date: "2026-10-01",
  payment_method: "CASH",
  supplier: null,
  supplier_name: null,
  notes: "",
};

const restock = {
  ...rent,
  id: "e2",
  description: "Wholesale restock",
  category: "c2",
  category_name: "Inventory",
  category_affects_profit: false,
  amount: "80000.00",
};

const summary = {
  total: "230000.00",
  count: 2,
  by_category: [
    { category: "c1", name: "Rent", affects_profit: true, total: "150000.00" },
    { category: "c2", name: "Inventory", affects_profit: false, total: "80000.00" },
  ],
};

function renderPage(role = "OWNER") {
  const auth = { role, business: { id: "b1", name: "Test Mart", currency: "SSP" } };
  return render(
    <AuthContext.Provider value={auth}>
      <ExpensesPage />
    </AuthContext.Provider>
  );
}

describe("ExpensesPage", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    expensesApi.listExpenseCategories.mockResolvedValue(page([]));
    inventoryApi.listSuppliers.mockResolvedValue(page([]));
    expensesApi.getExpenseSummary.mockResolvedValue(summary);
  });

  it("lists expenses with the total and flags ones not counted in profit", async () => {
    expensesApi.listExpenses.mockResolvedValue(page([rent, restock]));
    renderPage();
    expect(await screen.findByText("Shop rent")).toBeInTheDocument();
    expect(screen.getByText("Wholesale restock")).toBeInTheDocument();
    expect(await screen.findByText(/230,000/)).toBeInTheDocument();
    expect(screen.getByText("Not counted in profit")).toBeInTheDocument();
  });

  it("shows a helpful empty state", async () => {
    expensesApi.listExpenses.mockResolvedValue(page([]));
    expensesApi.getExpenseSummary.mockResolvedValue({ total: "0.00", count: 0, by_category: [] });
    renderPage();
    expect(await screen.findByText("No expenses yet")).toBeInTheDocument();
  });

  it("lets only the owner delete expenses", async () => {
    expensesApi.listExpenses.mockResolvedValue(page([rent]));
    const { unmount } = renderPage("OWNER");
    expect(await screen.findByRole("button", { name: "Delete: Shop rent" })).toBeInTheDocument();
    unmount();

    renderPage("MANAGER");
    expect(await screen.findByRole("button", { name: "Edit: Shop rent" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^Delete/ })).not.toBeInTheDocument();
  });

  it("asks for confirmation before deleting", async () => {
    expensesApi.listExpenses.mockResolvedValue(page([rent]));
    expensesApi.deleteExpense.mockResolvedValue({});
    const user = userEvent.setup();
    renderPage("OWNER");
    await user.click(await screen.findByRole("button", { name: "Delete: Shop rent" }));
    expect(expensesApi.deleteExpense).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Yes, delete" }));
    expect(expensesApi.deleteExpense).toHaveBeenCalledWith("e1");
  });

  it("recovers from a network error with Try again", async () => {
    expensesApi.listExpenses
      .mockRejectedValueOnce(new Error("Network Error"))
      .mockResolvedValueOnce(page([rent]));
    const user = userEvent.setup();
    renderPage();
    expect(await screen.findByText(/Can't reach the server/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByText("Shop rent")).toBeInTheDocument();
  });
});
