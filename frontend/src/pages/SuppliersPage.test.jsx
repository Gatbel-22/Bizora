import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as inventoryApi from "../api/inventory";
import SuppliersPage from "./SuppliersPage";

vi.mock("../api/inventory");

const page = (results) => ({ count: results.length, next: null, previous: null, results });

describe("SuppliersPage", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("lists suppliers with how many products use them", async () => {
    inventoryApi.listSuppliers.mockResolvedValue(
      page([{ id: "s1", name: "Juba Wholesale", phone: "0911", email: "", product_count: 3 }])
    );
    render(<SuppliersPage />);
    expect(await screen.findByText("Juba Wholesale")).toBeInTheDocument();
    expect(screen.getByText("3 products")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Delete: Juba Wholesale" })).toBeInTheDocument();
  });

  it("shows a helpful empty state", async () => {
    inventoryApi.listSuppliers.mockResolvedValue(page([]));
    render(<SuppliersPage />);
    expect(await screen.findByText("No suppliers yet")).toBeInTheDocument();
  });
});
