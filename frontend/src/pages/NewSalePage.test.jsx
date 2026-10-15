import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as customersApi from "../api/customers";
import * as inventoryApi from "../api/inventory";
import * as salesApi from "../api/sales";
import { AuthContext } from "../context/authContext";
import NewSalePage from "./NewSalePage";

vi.mock("../api/inventory");
vi.mock("../api/customers");
vi.mock("../api/sales");

const page = (results) => ({ count: results.length, next: null, previous: null, results });

const cola = {
  id: "p1",
  name: "Cola 500ml",
  sku: "COLA",
  unit: "BOTTLE",
  selling_price: "1000.00",
  current_stock: "24.000",
  stock_status: "in_stock",
};

function renderPage() {
  const auth = {
    role: "OWNER",
    business: { id: "b1", name: "Test Mart", currency: "SSP" },
  };

  return render(
    <MemoryRouter initialEntries={["/sales/new"]}>
      <AuthContext.Provider value={auth}>
        <Routes>
          <Route path="/sales/new" element={<NewSalePage />} />
          <Route path="/sales/:id" element={<p>Receipt page</p>} />
        </Routes>
      </AuthContext.Provider>
    </MemoryRouter>
  );
}

async function addColaAndOpenCheckout(user) {
  await user.click(await screen.findByRole("button", { name: /Cola 500ml/ }));
  await user.click(screen.getByRole("button", { name: /^Checkout/ }));
}

describe("NewSalePage", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    inventoryApi.listProducts.mockResolvedValue(page([cola]));
    customersApi.listCustomers.mockResolvedValue(page([]));
  });

  it("adds products to the cart and keeps the total up to date", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(await screen.findByRole("button", { name: /Cola 500ml/ }));

    expect(screen.getByRole("button", { name: /^Checkout · .*1,000/ })).toBeEnabled();

    await user.click(screen.getByRole("button", { name: "Increase quantity" }));

    expect(screen.getByRole("button", { name: /^Checkout · .*2,000/ })).toBeInTheDocument();
  });

  it("warns when the quantity is more than the stock", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(await screen.findByRole("button", { name: /Cola 500ml/ }));

    const quantity = screen.getByLabelText("Quantity");
    await user.clear(quantity);
    await user.type(quantity, "30");

    expect(screen.getByText("Only 24 in stock.")).toBeInTheDocument();
  });

  it("completes a cash sale and shows the receipt", async () => {
    salesApi.createSale.mockResolvedValue({ id: "s1" });

    const user = userEvent.setup();
    renderPage();

    await addColaAndOpenCheckout(user);
    await user.click(screen.getByRole("button", { name: "Complete sale" }));

    expect(salesApi.createSale).toHaveBeenCalledWith(
      expect.objectContaining({
        items: [{ product: "p1", quantity: "1" }],
        payment_method: "CASH",
        amount_paid: "1000.00",
      })
    );

    expect(await screen.findByText("Receipt page")).toBeInTheDocument();
  });

  it("won't sell on credit without a customer", async () => {
    const user = userEvent.setup();
    renderPage();

    await addColaAndOpenCheckout(user);
    await user.click(screen.getByLabelText("Credit"));
    await user.click(screen.getByRole("button", { name: "Complete sale" }));

    expect(await screen.findByText("Choose a customer to sell on credit.")).toBeInTheDocument();

    expect(salesApi.createSale).not.toHaveBeenCalled();
  });

  it("shows the server's stock message and keeps the cart", async () => {
    salesApi.createSale.mockRejectedValue({
      response: {
        status: 400,
        data: {
          error: {
            message: "Please correct the highlighted fields.",
            details: {
              items: ["Not enough stock: Cola 500ml has 3 available but 5 was requested."],
            },
          },
        },
      },
    });

    const user = userEvent.setup();
    renderPage();

    await addColaAndOpenCheckout(user);
    await user.click(screen.getByRole("button", { name: "Complete sale" }));

    expect(await screen.findByText(/Not enough stock/)).toBeInTheDocument();
    expect(screen.queryByText("Receipt page")).not.toBeInTheDocument();
  });

  it("creating a customer from checkout does not complete the sale", async () => {
    customersApi.createCustomer.mockResolvedValue({
      id: "c9",
      name: "Mama Rose",
    });

    const user = userEvent.setup();
    renderPage();

    await addColaAndOpenCheckout(user);

    await user.click(screen.getByRole("button", { name: "New customer" }));
    await user.type(screen.getByLabelText(/^Customer name/), "Mama Rose");
    await user.click(screen.getByRole("button", { name: "Save" }));

    expect(await screen.findByText("Mama Rose")).toBeInTheDocument();
    expect(salesApi.createSale).not.toHaveBeenCalled();

    expect(screen.getByRole("button", { name: "Complete sale" })).toBeInTheDocument();
  });
});
