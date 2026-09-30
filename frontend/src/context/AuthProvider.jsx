import { useCallback, useEffect, useMemo, useState } from "react";
import { fetchMe, loginRequest, logoutRequest, registerAccount } from "../api/auth";
import { setAuthFailureHandler } from "../api/client";
import { tokenStorage } from "../utils/tokenStorage";
import { AuthContext } from "./authContext";

// status: "loading" | "authenticated" | "anonymous" | "error" (server unreachable)
export default function AuthProvider({ children }) {
  const [status, setStatus] = useState(tokenStorage.hasSession() ? "loading" : "anonymous");
  const [user, setUser] = useState(null);
  const [memberships, setMemberships] = useState([]);
  const [activeBusinessId, setActiveBusinessId] = useState(tokenStorage.getBusinessId());

  const applyProfile = useCallback((profile) => {
    const list = profile.memberships ?? [];
    const stored = tokenStorage.getBusinessId();
    const active = list.find((m) => m.business_id === stored) ?? list[0] ?? null;
    tokenStorage.setBusinessId(active?.business_id ?? null);
    setActiveBusinessId(active?.business_id ?? null);
    setUser(profile.user);
    setMemberships(list);
    setStatus("authenticated");
  }, []);

  const clearSession = useCallback(() => {
    tokenStorage.clear();
    setUser(null);
    setMemberships([]);
    setActiveBusinessId(null);
    setStatus("anonymous");
  }, []);

  // Only a rejected login signs the user out. A network problem keeps the
  // session and lets the user retry.
  const handleProfileError = useCallback(
    (error) => {
      if (error.response?.status === 401) clearSession();
      else setStatus("error");
    },
    [clearSession]
  );

  useEffect(() => {
    setAuthFailureHandler(clearSession);
  }, [clearSession]);

  // Restore the session on first load.
  useEffect(() => {
    if (!tokenStorage.hasSession()) return undefined;
    let active = true;
    fetchMe()
      .then((profile) => {
        if (active) applyProfile(profile);
      })
      .catch((error) => {
        if (active) handleProfileError(error);
      });
    return () => {
      active = false;
    };
  }, [applyProfile, handleProfileError]);

  const retry = useCallback(() => {
    setStatus("loading");
    fetchMe().then(applyProfile).catch(handleProfileError);
  }, [applyProfile, handleProfileError]);

  const startSession = useCallback(
    (data) => {
      tokenStorage.setTokens({ access: data.access, refresh: data.refresh });
      applyProfile(data);
    },
    [applyProfile]
  );

  const login = useCallback(
    async (email, password) => startSession(await loginRequest(email, password)),
    [startSession]
  );

  const register = useCallback(
    async (payload) => startSession(await registerAccount(payload)),
    [startSession]
  );

  const logout = useCallback(async () => {
    const refresh = tokenStorage.getRefresh();
    try {
      if (refresh) await logoutRequest(refresh);
    } catch {
      // Even if the server can't be reached, sign out locally.
    } finally {
      clearSession();
    }
  }, [clearSession]);

  const value = useMemo(() => {
    const activeMembership = memberships.find((m) => m.business_id === activeBusinessId) ?? null;
    return {
      status,
      user,
      memberships,
      activeMembership,
      role: activeMembership?.role ?? null,
      business: activeMembership
        ? {
            id: activeMembership.business_id,
            name: activeMembership.business_name,
            currency: activeMembership.currency,
          }
        : null,
      login,
      register,
      logout,
      retry,
    };
  }, [status, user, memberships, activeBusinessId, login, register, logout, retry]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
