import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as customersApi from "../../api/customers";
import RecordPaymentModal from "./RecordPaymentModal";

vi.mock("../../api/customers");

const customer = { id: "c1", name: "Mama Rose", outstanding_balance: "1000.00" };

function renderModal(props = {}) {
  const onSaved = vi.fn();
  render(
    <RecordPaymentModal
      customer={customer}
      openDebts={[]}
      currency="SSP"
      onClose={() => {}}
      onSaved={onSaved}
      {...props}
    />
  );
  return { onSaved };
}

describe("RecordPaymentModal", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("refuses an amount larger than the balance without calling the API", async () => {
    const user = userEvent.setup();
    renderModal();
    await user.type(screen.getByLabelText(/^Amount received/), "1500");
    await user.click(screen.getByRole("button", { name: "Record payment" }));
    expect(await screen.findByText(/more than the/)).toBeInTheDocument();
    expect(customersApi.recordCustomerPayment).not.toHaveBeenCalled();
  });

  it("refuses an empty or zero amount", async () => {
    const user = userEvent.setup();
    renderModal();
    await user.click(screen.getByRole("button", { name: "Record payment" }));
    expect(await screen.findByText(/Enter a valid amount/)).toBeInTheDocument();
    expect(customersApi.recordCustomerPayment).not.toHaveBeenCalled();
  });

  it("records a valid payment", async () => {
    customersApi.recordCustomerPayment.mockResolvedValue({});
    const user = userEvent.setup();
    const { onSaved } = renderModal();
    await user.type(screen.getByLabelText(/^Amount received/), "400");
    await user.click(screen.getByRole("button", { name: "Record payment" }));
    expect(customersApi.recordCustomerPayment).toHaveBeenCalledWith({
      customer: "c1",
      amount: "400",
      method: "CASH",
      note: "",
    });
    expect(await screen.findByRole("button", { name: "Record payment" })).toBeInTheDocument();
    expect(onSaved).toHaveBeenCalledWith("Payment recorded.");
  });

  it("can fill in the full balance", async () => {
    const user = userEvent.setup();
    renderModal();
    await user.click(screen.getByRole("button", { name: "Pay full balance" }));
    expect(screen.getByLabelText(/^Amount received/)).toHaveValue("1000.00");
  });
});
