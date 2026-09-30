import { LogOut, Menu, X } from "lucide-react";
import { useEffect, useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { NAV_ITEMS } from "../config/navigation";
import useAuth from "../hooks/useAuth";
import { t } from "../i18n";
import Logo from "./Logo";

function SidebarContent({ items, business, user, role, onNavigate, onLogout }) {
  return (
    <div className="flex h-full flex-col">
      <div className="px-5 pb-4 pt-6">
        <Logo className="text-xl" />
        <p className="mt-3 truncate text-sm font-medium text-slate-700">{business.name}</p>
      </div>

      <nav aria-label={t("nav.main")} className="flex-1 space-y-1 px-3">
        {items.map(({ to, labelKey, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            onClick={onNavigate}
            className={({ isActive }) =>
              `flex min-h-11 items-center gap-3 rounded-lg px-3 py-2 text-sm ${
                isActive
                  ? "bg-brand-50 font-semibold text-brand-900"
                  : "font-medium text-slate-700 hover:bg-slate-100"
              }`
            }
          >
            <Icon className="h-5 w-5 shrink-0" aria-hidden="true" />
            {t(labelKey)}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-slate-200 p-4">
        <p className="truncate text-sm font-medium text-slate-900">{user.full_name}</p>
        <p className="text-xs text-slate-600">{t(`role.${role}`)}</p>
        <button
          type="button"
          onClick={onLogout}
          className="mt-3 flex min-h-11 w-full items-center gap-2 rounded-lg px-3 text-sm font-medium text-slate-700 hover:bg-slate-100"
        >
          <LogOut className="h-5 w-5" aria-hidden="true" />
          {t("common.signOut")}
        </button>
      </div>
    </div>
  );
}

export default function AppLayout() {
  const { user, business, role, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const items = NAV_ITEMS.filter((item) => item.roles.includes(role));

  useEffect(() => {
    if (!menuOpen) return undefined;
    const onKeyDown = (event) => {
      if (event.key === "Escape") setMenuOpen(false);
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [menuOpen]);

  const sidebar = (
    <SidebarContent
      items={items}
      business={business}
      user={user}
      role={role}
      onNavigate={() => setMenuOpen(false)}
      onLogout={logout}
    />
  );

  return (
    <div className="min-h-screen">
      {/* Desktop sidebar */}
      <aside className="hidden border-r border-slate-200 bg-white lg:fixed lg:inset-y-0 lg:flex lg:w-64 lg:flex-col">
        {sidebar}
      </aside>

      {/* Mobile top bar */}
      <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-slate-200 bg-white px-2 pt-[env(safe-area-inset-top)] lg:hidden">
        <button
          type="button"
          onClick={() => setMenuOpen(true)}
          aria-label={t("nav.openMenu")}
          aria-expanded={menuOpen}
          className="flex h-11 w-11 items-center justify-center rounded-lg text-slate-700 hover:bg-slate-100"
        >
          <Menu className="h-6 w-6" aria-hidden="true" />
        </button>
        <Logo className="text-lg" />
        <span className="w-11" aria-hidden="true" />
      </header>

      {/* Mobile drawer */}
      {menuOpen && (
        <div
          className="fixed inset-0 z-40 lg:hidden"
          role="dialog"
          aria-modal="true"
          aria-label={t("nav.main")}
        >
          <button
            type="button"
            aria-label={t("nav.closeMenu")}
            onClick={() => setMenuOpen(false)}
            className="absolute inset-0 bg-slate-900/50"
          />
          <div className="relative h-full w-72 max-w-[85%] bg-white shadow-xl">
            <button
              type="button"
              autoFocus
              onClick={() => setMenuOpen(false)}
              aria-label={t("nav.closeMenu")}
              className="absolute right-2 top-2 flex h-11 w-11 items-center justify-center rounded-lg text-slate-600 hover:bg-slate-100"
            >
              <X className="h-6 w-6" aria-hidden="true" />
            </button>
            {sidebar}
          </div>
        </div>
      )}

      <div className="lg:pl-64">
        <main className="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6 lg:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
