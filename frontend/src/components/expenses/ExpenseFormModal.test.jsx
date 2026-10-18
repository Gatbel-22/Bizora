import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as expensesApi from "../../api/expenses";
import ExpenseFormModal from "./ExpenseFormModal";

vi.mock("../../api/expenses");

const categories = [
  { id: "c1", name: "Rent" },
  { id: "c2", name: "Transport" },
];

function renderModal() {
  const onSaved = vi.fn();
  render(
    <ExpenseFormModal
      expense={null}
      categories={categories}
      suppliers={[]}
      onClose={() => {}}
      onSaved={onSaved}
    />
  );
  return { onSaved };
}

describe("ExpenseFormModal", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("asks for the missing details without calling the API", async () => {
    const user = userEvent.setup();
    renderModal();
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(await screen.findByText("Choose a category.")).toBeInTheDocument();
    expect(screen.getByText(/Enter a valid amount/)).toBeInTheDocument();
    expect(expensesApi.createExpense).not.toHaveBeenCalled();
  });

  it("refuses an amount of zero", async () => {
    const user = userEvent.setup();
    renderModal();
    await user.type(screen.getByLabelText(/^What was it for/), "Fuel");
    await user.selectOptions(screen.getByLabelText("Category"), "c2");
    await user.type(screen.getByLabelText(/^Amount/), "0");
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(await screen.findByText(/Enter a valid amount/)).toBeInTheDocument();
    expect(expensesApi.createExpense).not.toHaveBeenCalled();
  });

  it("records a valid expense", async () => {
    expensesApi.createExpense.mockResolvedValue({});
    const user = userEvent.setup();
    const { onSaved } = renderModal();
    await user.type(screen.getByLabelText(/^What was it for/), "Fuel");
    await user.selectOptions(screen.getByLabelText("Category"), "c2");
    await user.type(screen.getByLabelText(/^Amount/), "1500");
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(expensesApi.createExpense).toHaveBeenCalledWith(
      expect.objectContaining({
        description: "Fuel",
        category: "c2",
        amount: "1500",
        payment_method: "CASH",
        supplier: null,
      })
    );
    expect(await screen.findByRole("button", { name: "Save" })).toBeInTheDocument();
    expect(onSaved).toHaveBeenCalledWith("Expense saved.");
  });
});
