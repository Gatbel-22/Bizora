import { describe, expect, it } from "vitest";
import { t } from "../i18n";
import { getErrorMessage, getFieldErrors } from "./errors";

const apiFailure = (status, error) => ({ response: { status, data: { error } } });

describe("getErrorMessage", () => {
  it("explains network failures in plain language", () => {
    expect(getErrorMessage(new Error("Network Error"))).toBe(t("error.network"));
  });

  it("explains timeouts", () => {
    expect(getErrorMessage({ code: "ECONNABORTED" })).toBe(t("error.timeout"));
  });

  it("never leaks server error details", () => {
    const error = apiFailure(500, { message: "IntegrityError: duplicate key" });
    expect(getErrorMessage(error)).toBe(t("error.server"));
  });

  it("explains rate limiting", () => {
    expect(getErrorMessage(apiFailure(429, { message: "Request was throttled." }))).toBe(
      t("error.throttled")
    );
  });

  it("uses the API message for permission errors", () => {
    const error = apiFailure(403, { message: "Only the business owner can do this." });
    expect(getErrorMessage(error)).toBe("Only the business owner can do this.");
  });

  it("uses non-field validation errors when present", () => {
    const error = apiFailure(400, {
      message: "Please correct the highlighted fields.",
      details: { non_field_errors: ["Something is inconsistent."] },
    });
    expect(getErrorMessage(error)).toBe("Something is inconsistent.");
  });
});

describe("getFieldErrors", () => {
  it("maps API validation details to one message per field", () => {
    const error = apiFailure(400, {
      details: {
        email: ["This email is already registered."],
        password: ["Too short.", "Too common."],
      },
    });
    expect(getFieldErrors(error)).toEqual({
      email: "This email is already registered.",
      password: "Too short. Too common.",
    });
  });

  it("returns an empty object when there are no details", () => {
    expect(getFieldErrors(new Error("Network Error"))).toEqual({});
  });
});
