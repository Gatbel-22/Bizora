import {
  FileText,
  LayoutDashboard,
  Package,
  Receipt,
  Settings,
  ShoppingCart,
  Users,
} from "lucide-react";
import { ROLES } from "./roles";

const ALL = [ROLES.OWNER, ROLES.MANAGER, ROLES.STAFF];
const MANAGEMENT = [ROLES.OWNER, ROLES.MANAGER];

export const NAV_ITEMS = [
  { to: "/", labelKey: "nav.dashboard", icon: LayoutDashboard, end: true, roles: ALL },
  { to: "/sales", labelKey: "nav.sales", icon: ShoppingCart, roles: ALL },
  { to: "/products", labelKey: "nav.products", icon: Package, roles: ALL },
  { to: "/customers", labelKey: "nav.customers", icon: Users, roles: ALL },
  { to: "/expenses", labelKey: "nav.expenses", icon: Receipt, roles: MANAGEMENT },
  { to: "/reports", labelKey: "nav.reports", icon: FileText, roles: MANAGEMENT },
  { to: "/settings", labelKey: "nav.settings", icon: Settings, roles: MANAGEMENT },
];
