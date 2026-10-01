import { Route, Routes } from "react-router-dom";
import AppLayout from "./components/AppLayout";
import GuestRoute from "./components/GuestRoute";
import ProtectedRoute from "./components/ProtectedRoute";
import RequireRole from "./components/RequireRole";
import { ROLES } from "./config/roles";
import ComingSoonPage from "./pages/ComingSoonPage";
import DashboardPage from "./pages/DashboardPage";
import LoginPage from "./pages/LoginPage";
import NotFoundPage from "./pages/NotFoundPage";
import RegisterPage from "./pages/RegisterPage";
import ProductsPage from "./pages/ProductsPage";

export default function App() {
  return (
    <Routes>
      <Route element={<GuestRoute />}>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
      </Route>

      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="sales" element={<ComingSoonPage titleKey="nav.sales" />} />
          <Route path="products" element={<ProductsPage />} />
          <Route path="customers" element={<ComingSoonPage titleKey="nav.customers" />} />

          <Route element={<RequireRole roles={[ROLES.OWNER, ROLES.MANAGER]} />}>
            <Route path="expenses" element={<ComingSoonPage titleKey="nav.expenses" />} />
            <Route path="reports" element={<ComingSoonPage titleKey="nav.reports" />} />
            <Route path="settings" element={<ComingSoonPage titleKey="nav.settings" />} />
          </Route>

          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Route>
    </Routes>
  );
}
