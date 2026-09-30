import { useState } from "react";
import { Link } from "react-router-dom";
import AuthLayout from "../components/AuthLayout";
import Alert from "../components/ui/Alert";
import Button from "../components/ui/Button";
import TextField from "../components/ui/TextField";
import useAuth from "../hooks/useAuth";
import { t } from "../i18n";
import { getErrorMessage } from "../utils/errors";

export default function LoginPage() {
  const { login } = useAuth();
  const [form, setForm] = useState({ email: "", password: "" });
  const [fieldErrors, setFieldErrors] = useState({});
  const [formError, setFormError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleChange = (event) => {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    const errors = {};
    if (!form.email.trim()) errors.email = t("validation.emailRequired");
    if (!form.password) errors.password = t("validation.passwordRequired");
    setFieldErrors(errors);
    setFormError("");
    if (Object.keys(errors).length > 0) return;

    setSubmitting(true);
    try {
      // On success the router redirects automatically (see GuestRoute).
      await login(form.email.trim(), form.password);
    } catch (error) {
      setFormError(
        error.response?.status === 401 ? t("auth.login.badCredentials") : getErrorMessage(error)
      );
      setSubmitting(false);
    }
  };

  return (
    <AuthLayout
      title={t("auth.login.title")}
      subtitle={t("auth.login.subtitle")}
      footer={
        <>
          {t("auth.login.noAccount")}{" "}
          <Link to="/register" className="font-semibold text-brand-700 underline">
            {t("auth.login.createAccount")}
          </Link>
        </>
      }
    >
      <form onSubmit={handleSubmit} noValidate className="space-y-4">
        {formError && <Alert>{formError}</Alert>}
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
          label={t("field.password")}
          name="password"
          type="password"
          autoComplete="current-password"
          required
          value={form.password}
          onChange={handleChange}
          error={fieldErrors.password}
        />
        <Button type="submit" loading={submitting} className="w-full">
          {t("auth.login.submit")}
        </Button>
      </form>
    </AuthLayout>
  );
}
