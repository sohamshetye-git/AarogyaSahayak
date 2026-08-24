import { useEffect, useState, useCallback } from "react";
import { realtimeService, DomainEventHandler } from "../services/RealtimeService";
import { useAuth } from "../auth/AuthContext";

export function useRealtime(onEvent?: DomainEventHandler) {
  const { user, isAuthenticated } = useAuth();
  const [connectionStatus, setConnectionStatus] = useState<"ONLINE" | "RECONNECTING" | "OFFLINE" | "DISCONNECTED">("DISCONNECTED");

  useEffect(() => {
    if (isAuthenticated && user?.id) {
      realtimeService.connect(user.id);
    } else {
      realtimeService.disconnect();
    }
  }, [isAuthenticated, user?.id]);

  useEffect(() => {
    const unsubscribe = realtimeService.subscribe((event, data) => {
      if (event === "REALTIME_STATE") {
        setConnectionStatus(data.status);
      }
      if (onEvent) {
        onEvent(event, data);
      }
    });

    return () => {
      unsubscribe();
    };
  }, [onEvent]);

  return { connectionStatus };
}
