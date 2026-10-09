import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as customersApi from "../api/customers";
import { AuthContext } from "../context/authContext";
import CustomersPage from "./CustomersPage";

vi.mock("../api/customers");

const page = (results) => ({ count: results.length, next: null, previous: null, results });

const rose = {
  id: "c1",
  name: "Mama Rose",
  phone: "+211911111111",
  email: "",
  is_active: true,
  outstanding_balance: "850000.00",
  overdue_balance: "850000.00",
};

const clear = {
  ...rose,
  id: "c2",
  name: "John Both",
  outstanding_balance: "0.00",
  overdue_balance: "0.00",
};

function renderPage(role = "OWNER") {
  const auth = { role, business: { id: "b1", name: "Test Mart", currency: "SSP" } };
  return render(
    <MemoryRouter>
      <AuthContext.Provider value={auth}>
        <CustomersPage />
      </AuthContext.Provider>
    </MemoryRouter>
  );
}

describe("CustomersPage", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("shows who owes money and how much is overdue", async () => {
    customersApi.listCustomers.mockResolvedValue(page([rose, clear]));
    renderPage();
    expect(await screen.findByRole("link", { name: "Mama Rose" })).toBeInTheDocument();
    expect(screen.getByText(/^Owes SSP/)).toBeInTheDocument();
    expect(screen.getByText(/overdue$/)).toBeInTheDocument();
    expect(screen.getByText("No balance")).toBeInTheDocument();
  });

  it("shows a helpful empty state for a new business", async () => {
    customersApi.listCustomers.mockResolvedValue(page([]));
    renderPage();
    expect(await screen.findByText("No customers yet")).toBeInTheDocument();
  });

  it("lets staff add customers but not edit them", async () => {
    customersApi.listCustomers.mockResolvedValue(page([rose]));
    renderPage("STAFF");
    expect(await screen.findByRole("link", { name: "Mama Rose" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add customer" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^Edit/ })).not.toBeInTheDocument();
  });

  it("lets managers edit customers", async () => {
    customersApi.listCustomers.mockResolvedValue(page([rose]));
    renderPage("MANAGER");
    expect(await screen.findByRole("button", { name: "Edit: Mama Rose" })).toBeInTheDocument();
  });
});
