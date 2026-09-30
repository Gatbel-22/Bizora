import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as authApi from "../api/auth";
import App from "../App";
import AuthProvider from "../context/AuthProvider";

vi.mock("../api/auth");

const loginResponse = {
  access: "access-token",
  refresh: "refresh-token",
  user: { id: "u1", email: "owner@example.com", full_name: "Test Owner" },
  memberships: [
    { id: "m1", business_id: "b1", business_name: "Test Mart", currency: "SSP", role: "OWNER" },
  ],
};

function renderApp(path = "/") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AuthProvider>
        <App />
      </AuthProvider>
    </MemoryRouter>
  );
}

describe("authentication flow", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("redirects anonymous visitors to the login page", async () => {
    renderApp("/");
    expect(await screen.findByRole("heading", { name: "Welcome back" })).toBeInTheDocument();
  });

  it("shows validation messages instead of calling the API for an empty form", async () => {
    const user = userEvent.setup();
    renderApp("/login");
    await user.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByText("Enter your email address.")).toBeInTheDocument();
    expect(screen.getByText("Enter your password.")).toBeInTheDocument();
    expect(authApi.loginRequest).not.toHaveBeenCalled();
  });

  it("shows a friendly message for wrong credentials", async () => {
    authApi.loginRequest.mockRejectedValue({
      response: { status: 401, data: { error: { message: "No active account found." } } },
    });
    const user = userEvent.setup();
    renderApp("/login");
    await user.type(screen.getByLabelText(/^email/i), "owner@example.com");
    await user.type(screen.getByLabelText(/^password/i), "wrong-password");
    await user.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByText("Incorrect email or password.")).toBeInTheDocument();
  });

  it("signs in and lands on the dashboard", async () => {
    authApi.loginRequest.mockResolvedValue(loginResponse);
    const user = userEvent.setup();
    renderApp("/login");
    await user.type(screen.getByLabelText(/^email/i), "owner@example.com");
    await user.type(screen.getByLabelText(/^password/i), "Str0ng-Pass-123");
    await user.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByRole("heading", { name: "Welcome, Test" })).toBeInTheDocument();
    expect(screen.getByText("No sales yet")).toBeInTheDocument();
  });
});
