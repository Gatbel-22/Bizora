import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as inventoryApi from "../api/inventory";
import { AuthContext } from "../context/authContext";
import ProductsPage from "./ProductsPage";

vi.mock("../api/inventory");

const page = (results) => ({ count: results.length, next: null, previous: null, results });

const cola = {
  id: "p1",
  name: "Cola 500ml",
  sku: "COLA",
  category_name: "Beverages",
  selling_price: "1000.00",
  purchase_price: "800.00",
  current_stock: "3.000",
  min_stock_threshold: "10.000",
  unit: "BOTTLE",
  stock_status: "low",
  is_active: true,
};

const water = {
  ...cola,
  id: "p2",
  name: "Water 1L",
  sku: "WATER",
  current_stock: "0.000",
  stock_status: "out",
};

function renderPage(role = "OWNER") {
  const auth = { role, business: { id: "b1", name: "Test Mart", currency: "SSP" } };
  return render(
    <AuthContext.Provider value={auth}>
      <ProductsPage />
    </AuthContext.Provider>
  );
}

describe("ProductsPage", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    inventoryApi.listCategories.mockResolvedValue(page([]));
  });

  it("lists products with low-stock and out-of-stock badges", async () => {
    inventoryApi.listProducts.mockResolvedValue(page([cola, water]));
    renderPage();
    expect(await screen.findByText("Cola 500ml")).toBeInTheDocument();
    expect(screen.getByText("Low stock", { selector: "span" })).toBeInTheDocument();
    expect(screen.getByText("Out of stock", { selector: "span" })).toBeInTheDocument();
  });

  it("shows a helpful empty state for a new business", async () => {
    inventoryApi.listProducts.mockResolvedValue(page([]));
    renderPage();
    expect(await screen.findByText("Your inventory is empty")).toBeInTheDocument();
    expect(screen.getByText("Add your first product to start tracking stock.")).toBeInTheDocument();
  });

  it("recovers from a network error with Try again", async () => {
    inventoryApi.listProducts
      .mockRejectedValueOnce(new Error("Network Error"))
      .mockResolvedValueOnce(page([cola]));
    const user = userEvent.setup();
    renderPage();
    expect(await screen.findByText(/Can't reach the server/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByText("Cola 500ml")).toBeInTheDocument();
  });

  it("hides management actions from staff", async () => {
    const staffView = { ...cola };
    delete staffView.purchase_price;
    inventoryApi.listProducts.mockResolvedValue(page([staffView]));
    renderPage("STAFF");
    expect(await screen.findByText("Cola 500ml")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Add product" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Adjust stock/ })).not.toBeInTheDocument();
    expect(screen.queryByText(/^Cost/)).not.toBeInTheDocument();
  });

  it("offers management actions to owners", async () => {
    inventoryApi.listProducts.mockResolvedValue(page([cola]));
    renderPage("OWNER");
    expect(await screen.findByRole("button", { name: "Add product" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Adjust stock: Cola 500ml" })).toBeInTheDocument();
    expect(screen.getByText(/^Cost/)).toBeInTheDocument();
  });
});
