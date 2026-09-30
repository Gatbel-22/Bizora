import { Navigate, Outlet, useLocation } from "react-router-dom";
import useAuth from "../hooks/useAuth";
import PageLoader from "./ui/PageLoader";

export default function GuestRoute() {
  const { status } = useAuth();
  const location = useLocation();

  if (status === "loading") return <PageLoader />;
  if (status === "authenticated") {
    return <Navigate to={location.state?.from?.pathname ?? "/"} replace />;
  }
  return <Outlet />;
}
