import React, { createContext, useContext, useState, useEffect } from "react";
import { apiClient } from "@aarogya/api-client";
import { UserRole, type UserSession } from "@aarogya/shared-types";
import { db } from "../db/offlineDb";
import { ashaSyncService } from "../services/AshaSyncService";
import { LocationService } from "@aarogya/location";

interface AuthContextType {
  user: UserSession | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (identifier: string, password: string) => Promise<UserSession>;
  logout: () => Promise<void>;
  updateUser: (updatedData: Partial<UserSession>) => void;
  checkPendingOfflineData: () => Promise<{ pendingCount: number; draftsCount: number }>;
  logoutWithChoice: (choice: 'SYNC_AND_LOGOUT' | 'KEEP_DATA' | 'FORCE_DELETE') => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserSession | null>(() => {
    const saved = localStorage.getItem("aarogya_user");
    return saved ? JSON.parse(saved) : null;
  });
  const [token, setToken] = useState<string | null>(() => {
    return localStorage.getItem("aarogya_token");
  });
  const [isLoading, setIsLoading] = useState(() => {
    return Boolean(localStorage.getItem("aarogya_token")) && !localStorage.getItem("aarogya_user");
  });

  useEffect(() => {
    if (token) {
      apiClient.setToken(token);
      setIsLoading(true);
      // Fetch authoritative user principal from /api/auth/me
      apiClient.getCurrentUser()
        .then((res: any) => {
          const authUser = res?.data || res;
          if (authUser && authUser.id) {
            setUser(authUser);
            localStorage.setItem("aarogya_user", JSON.stringify(authUser));
          }
        })
        .catch((err: any) => {
          console.warn("Failed to refresh user profile from /auth/me:", err);
          // If token is invalid or account suspended, clear state
          if (err?.status === 401 || err?.status === 403 || err?.code === "UNAUTHORIZED" || err?.code === "ACCOUNT_INACTIVE") {
            logout();
          }
        })
        .finally(() => {
          setIsLoading(false);
        });
    } else {
      setIsLoading(false);
    }
    if (user) {
      ashaSyncService.setUser(user.id, user.role);
      LocationService.setUserContext(user.id, user.role);
    } else {
      ashaSyncService.setUser(null, null);
      LocationService.setUserContext(null, null);
    }
  }, [token]);

  useEffect(() => {
    if (user) {
      ashaSyncService.setUser(user.id, user.role);
      LocationService.setUserContext(user.id, user.role);
    }
  }, [user]);

  const login = async (identifier: string, password: string): Promise<UserSession> => {
    setIsLoading(true);
    try {
      // Clear any prior cached session / user data before storing new login
      localStorage.removeItem("aarogya_token");
      localStorage.removeItem("aarogya_user");

      const response = await apiClient.login(identifier, password);
      const { access_token, user: userData } = response;

      setToken(access_token);
      apiClient.setToken(access_token);

      // Authoritative hydration from /api/auth/me immediately
      let authoritativeUser = userData;
      try {
        const meRes = await apiClient.getCurrentUser();
        if (meRes?.data || meRes?.id) {
          authoritativeUser = meRes?.data || meRes;
        }
      } catch (meErr) {
        console.warn("Direct /auth/me call fallback to login payload:", meErr);
      }

      setUser(authoritativeUser);
      localStorage.setItem("aarogya_token", access_token);
      localStorage.setItem("aarogya_user", JSON.stringify(authoritativeUser));

      ashaSyncService.setUser(authoritativeUser.id, authoritativeUser.role);
      LocationService.setUserContext(authoritativeUser.id, authoritativeUser.role);

      return authoritativeUser;
    } finally {
      setIsLoading(false);
    }
  };

  const checkPendingOfflineData = async (): Promise<{ pendingCount: number; draftsCount: number }> => {
    if (!user) return { pendingCount: 0, draftsCount: 0 };
    
    try {
      const pendingCount = await db.pendingActions
        .where('status')
        .anyOf('PENDING', 'FAILED_RETRYABLE', 'CONFLICT_REQUIRES_REVIEW')
        .and(a => !a.ownerUserId || a.ownerUserId === user.id)
        .count();

      const draftsCount = await db.visitDrafts
        .filter(d => !d.ownerUserId || d.ownerUserId === user.id)
        .count();

      return { pendingCount, draftsCount };
    } catch (err) {
      console.error("Error checking pending offline data", err);
      return { pendingCount: 0, draftsCount: 0 };
    }
  };

  const logoutWithChoice = async (choice: 'SYNC_AND_LOGOUT' | 'KEEP_DATA' | 'FORCE_DELETE') => {
    if (choice === 'SYNC_AND_LOGOUT') {
      try {
        await ashaSyncService.syncPendingActions();
      } catch (e) {
        console.error("Sync before logout failed:", e);
      }
    } else if (choice === 'FORCE_DELETE' && user) {
      try {
        // Only delete records belonging to this user
        await db.pendingActions.where('ownerUserId').equals(user.id).delete();
        await db.visitDrafts.where('ownerUserId').equals(user.id).delete();
        await db.conflicts.where('ownerUserId').equals(user.id).delete();
      } catch (err) {
        console.error("Failed to delete user records", err);
      }
    }

    setUser(null);
    setToken(null);
    apiClient.setToken(null);
    LocationService.clearTemporaryLocation();
    LocationService.setUserContext(null, null);
    localStorage.removeItem("aarogya_token");
    localStorage.removeItem("aarogya_user");
    ashaSyncService.setUser(null, null);
  };

  const updateUser = (updatedData: Partial<UserSession>) => {
    if (!user) return;
    const merged = { ...user, ...updatedData };
    setUser(merged);
    localStorage.setItem("aarogya_user", JSON.stringify(merged));
  };

  const logout = async () => {
    // Non-destructive logout by default (preserves scoped data safely on device)
    await logoutWithChoice('KEEP_DATA');
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!user,
        isLoading,
        login,
        logout,
        updateUser,
        checkPendingOfflineData,
        logoutWithChoice
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

