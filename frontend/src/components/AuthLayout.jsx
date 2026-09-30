import { t } from "../i18n";
import Logo from "./Logo";

export default function AuthLayout({ title, subtitle, footer, children }) {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center px-4 py-10">
      <Logo />
      <p className="mt-1 text-sm text-slate-600">{t("brand.tagline")}</p>
      <div className="mt-6 w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
        <h1 className="text-xl font-semibold text-slate-900">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-slate-600">{subtitle}</p>}
        <div className="mt-6">{children}</div>
      </div>
      {footer && <p className="mt-6 text-sm text-slate-600">{footer}</p>}
    </main>
  );
}
