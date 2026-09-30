import { useState } from "react";
import { Link } from "react-router-dom";
import AuthLayout from "../components/AuthLayout";
import Alert from "../components/ui/Alert";
import Button from "../components/ui/Button";
import SelectField from "../components/ui/SelectField";
import TextField from "../components/ui/TextField";
import { BUSINESS_TYPES, CURRENCIES } from "../config/options";
import useAuth from "../hooks/useAuth";
import { t } from "../i18n";
import { getErrorMessage, getFieldErrors } from "../utils/errors";

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function validate(form) {
  const errors = {};
  if (!form.full_name.trim()) errors.full_name = t("validation.required");
  if (!form.business_name.trim()) errors.business_name = t("validation.required");
  if (!form.email.trim()) errors.email = t("validation.emailRequired");
  else if (!EMAIL_PATTERN.test(form.email.trim())) errors.email = t("validation.emailInvalid");
  if (form.password.length < 8) errors.password = t("validation.passwordShort");
  if (form.confirm_password !== form.password) {
    errors.confirm_password = t("validation.passwordMismatch");
  }
  return errors;
}

export default function RegisterPage() {
  const { register } = useAuth();
  const [form, setForm] = useState({
    full_name: "",
    email: "",
    phone: "",
    business_name: "",
    business_type: "RETAIL",
    currency: "SSP",
    password: "",
    confirm_password: "",
  });
  const [fieldErrors, setFieldErrors] = useState({});
  const [formError, setFormError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleChange = (event) => {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    const errors = validate(form);
    setFieldErrors(errors);
    setFormError("");
    if (Object.keys(errors).length > 0) return;

    setSubmitting(true);
    try {
      await register({
        full_name: form.full_name.trim(),
        email: form.email.trim(),
        phone: form.phone.trim(),
        business_name: form.business_name.trim(),
        business_type: form.business_type,
        currency: form.currency,
        password: form.password,
      });
    } catch (error) {
      const serverErrors = getFieldErrors(error);
      setFieldErrors(serverErrors);
      // Show the banner only when there's no specific field to point at.
      if (Object.keys(serverErrors).length === 0) setFormError(getErrorMessage(error));
      setSubmitting(false);
    }
  };

  return (
    <AuthLayout
      title={t("auth.register.title")}
      subtitle={t("auth.register.subtitle")}
      footer={
        <>
          {t("auth.register.haveAccount")}{" "}
          <Link to="/login" className="font-semibold text-brand-700 underline">
            {t("auth.register.signIn")}
          </Link>
        </>
      }
    >
      <form onSubmit={handleSubmit} noValidate className="space-y-4">
        {formError && <Alert>{formError}</Alert>}
        <TextField
          label={t("field.fullName")}
          name="full_name"
          autoComplete="name"
          required
          value={form.full_name}
          onChange={handleChange}
          error={fieldErrors.full_name}
        />
        <TextField
          label={t("field.email")}
          name="email"
          type="email"
          autoComplete="email"
          inputMode="email"
          required
          value={form.email}
          onChange={handleChange}
          error={fieldErrors.email}
        />
        <TextField
          label={t("field.phone")}
          name="phone"
          type="tel"
          autoComplete="tel"
          inputMode="tel"
          value={form.phone}
          onChange={handleChange}
          error={fieldErrors.phone}
        />
        <TextField
          label={t("field.businessName")}
          name="business_name"
          autoComplete="organization"
          required
          value={form.business_name}
          onChange={handleChange}
          error={fieldErrors.business_name}
        />
        <div className="grid gap-4 sm:grid-cols-2">
          <SelectField
            label={t("field.businessType")}
            name="business_type"
            options={BUSINESS_TYPES}
            value={form.business_type}
            onChange={handleChange}
            error={fieldErrors.business_type}
          />
          <SelectField
            label={t("field.currency")}
            name="currency"
            options={CURRENCIES}
            value={form.currency}
            onChange={handleChange}
            error={fieldErrors.currency}
          />
        </div>
        <TextField
          label={t("field.password")}
          name="password"
          type="password"
          autoComplete="new-password"
          required
          hint={t("field.passwordHint")}
          value={form.password}
          onChange={handleChange}
          error={fieldErrors.password}
        />
        <TextField
          label={t("field.confirmPassword")}
          name="confirm_password"
          type="password"
          autoComplete="new-password"
          required
          value={form.confirm_password}
          onChange={handleChange}
          error={fieldErrors.confirm_password}
        />
        <Button type="submit" loading={submitting} className="w-full">
          {t("auth.register.submit")}
        </Button>
      </form>
    </AuthLayout>
  );
}
