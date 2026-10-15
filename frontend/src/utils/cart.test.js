import { describe, expect, it } from "vitest";
import {
  addToCart,
  buildSalePayload,
  cartSubtotal,
  exceedsStock,
  removeLine,
  saleTotals,
  setQuantity,
  stepQuantity,
} from "./cart";

const cola = {
  id: "p1",
  name: "Cola",
  sku: "COLA",
  unit: "BOTTLE",
  selling_price: "1000.00",
  current_stock: "5.000",
};
const water = { ...cola, id: "p2", name: "Water", selling_price: "500.00" };

describe("cart", () => {
  it("adding the same product again increases its quantity", () => {
    const cart = addToCart(addToCart([], cola), cola);
    expect(cart).toHaveLength(1);
    expect(cart[0].quantity).toBe("2");
  });

  it("adds up line totals", () => {
    let cart = addToCart([], cola);
    cart = addToCart(cart, water);
    cart = setQuantity(cart, "p1", "3");
    expect(cartSubtotal(cart)).toBe(3500);
  });

  it("ignores lines with an invalid quantity", () => {
    const cart = setQuantity(addToCart([], cola), "p1", "abc");
    expect(cartSubtotal(cart)).toBe(0);
  });

  it("stepping down to zero removes the line", () => {
    const cart = stepQuantity(addToCart([], cola), "p1", -1);
    expect(cart).toEqual([]);
  });

  it("removes a line", () => {
    const cart = removeLine(addToCart(addToCart([], cola), water), "p1");
    expect(cart.map((line) => line.productId)).toEqual(["p2"]);
  });

  it("flags quantities above the stock on hand", () => {
    const line = setQuantity(addToCart([], cola), "p1", "6")[0];
    expect(exceedsStock(line)).toBe(true);
    expect(exceedsStock({ ...line, quantity: "5" })).toBe(false);
  });

  it("applies a sale discount to the total", () => {
    const cart = setQuantity(addToCart([], cola), "p1", "2");
    expect(saleTotals(cart, "300")).toEqual({ subtotal: 2000, discount: 300, total: 1700 });
    expect(saleTotals(cart, "").total).toBe(2000);
  });

  it("builds the payload the API expects", () => {
    const cart = setQuantity(addToCart([], cola), "p1", "2");
    expect(
      buildSalePayload({
        cart,
        customerId: "c1",
        discount: "",
        paymentMethod: "CASH",
        amountPaid: "1500.00",
        dueDate: "",
        note: " thanks ",
        clientReference: "ref-1",
      })
    ).toEqual({
      items: [{ product: "p1", quantity: "2" }],
      payment_method: "CASH",
      customer: "c1",
      amount_paid: "1500.00",
      note: "thanks",
      client_reference: "ref-1",
    });
  });

  it("never sends an amount paid for credit sales", () => {
    const cart = addToCart([], cola);
    const payload = buildSalePayload({
      cart,
      customerId: "c1",
      discount: "",
      paymentMethod: "CREDIT",
      amountPaid: "1000.00",
      dueDate: "",
      note: "",
    });
    expect(payload).not.toHaveProperty("amount_paid");
  });
});
