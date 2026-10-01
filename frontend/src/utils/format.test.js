import { describe, expect, it } from "vitest";
import { formatMoney, formatQuantity } from "./format";

describe("formatMoney", () => {
  it("shows the currency code and groups thousands", () => {
    const text = formatMoney("1850000.00", "SSP");
    expect(text).toContain("SSP");
    expect(text).toMatch(/1.?850.?000/);
  });

  it("shows decimals only when needed", () => {
    expect(formatMoney("1500.50", "SSP")).toMatch(/1.?500\.50/);
    expect(formatMoney("1500.00", "SSP")).not.toMatch(/\.00/);
  });

  it("shows a dash for missing values", () => {
    expect(formatMoney(undefined)).toBe("-");
    expect(formatMoney("")).toBe("-");
  });
});

describe("formatQuantity", () => {
  it("drops trailing zeros", () => {
    expect(formatQuantity("24.000")).toBe("24");
    expect(formatQuantity("2.500")).toBe("2.5");
  });

  it("can show signs for stock changes", () => {
    expect(formatQuantity("10.000", { signed: true })).toBe("+10");
    expect(formatQuantity("-4.000", { signed: true })).toMatch(/4$/);
    expect(formatQuantity("-4.000", { signed: true })).toMatch(/^[-−]/);
  });
});
