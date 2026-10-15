import { describe, expect, it } from "vitest";
import { buildReceiptText } from "./receipt";

const receipt = {
  business: { name: "Gatbel Mini Mart", address: "Juba", phone: "+211900000000", currency: "SSP" },
  number: "S-000007",
  sold_at: "2026-10-12T10:30:00Z",
  served_by: "Ann",
  customer: "Mama Rose",
  items: [{ name: "Cola", quantity: "3.000", unit_price: "1000.00", line_total: "3000.00" }],
  subtotal: "3000.00",
  discount: "0.00",
  total: "3000.00",
  amount_paid: "1000.00",
  outstanding_amount: "2000.00",
};

describe("buildReceiptText", () => {
  it("includes the key details", () => {
    const text = buildReceiptText(receipt);
    expect(text).toContain("Gatbel Mini Mart");
    expect(text).toContain("Sale S-000007");
    expect(text).toContain("Cola");
    expect(text).toContain("Mama Rose");
    expect(text).toContain("Balance owed");
  });

  it("leaves out the balance and discount when there are none", () => {
    const text = buildReceiptText({
      ...receipt,
      amount_paid: "3000.00",
      outstanding_amount: "0.00",
    });
    expect(text).not.toContain("Balance owed");
    expect(text).not.toContain("Discount");
  });

  it("shows the discount when there is one", () => {
    const text = buildReceiptText({ ...receipt, subtotal: "3500.00", discount: "500.00" });
    expect(text).toContain("Discount");
  });
});
