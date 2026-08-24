import { apiClient } from "@aarogya/api-client";

export type DomainEventHandler = (event: string, data: any) => void;

class RealtimeService {
  private ws: WebSocket | null = null;
  private subscribers: Set<DomainEventHandler> = new Set();
  private processedEventIds: Set<string> = new Set();
  private reconnectAttempts = 0;
  private maxReconnectDelay = 30000;
  private reconnectTimeout: any = null;
  private isConnecting = false;
  private currentUserId: string | null = null;

  public subscribe(handler: DomainEventHandler): () => void {
    this.subscribers.add(handler);
    return () => {
      this.subscribers.delete(handler);
    };
  }

  public async connect(userId?: string) {
    if (this.isConnecting || (this.ws && this.ws.readyState === WebSocket.OPEN)) {
      return;
    }

    if (userId) {
      this.currentUserId = userId;
    }

    this.isConnecting = true;

    try {
      // Step 1: Request short-lived one-time ticket from backend
      const res = await apiClient.request<any>("/realtime/ticket", { method: "POST" });
      const { ticket } = res;

      if (!ticket) {
        throw new Error("No ticket returned from realtime ticket endpoint");
      }

      // Step 2: Establish WebSocket using ticket query param
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const host = window.location.hostname;
      const port = "8000"; // Backend port
      const wsUrl = `${protocol}//${host}:${port}/api/ws?ticket=${ticket}`;

      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        this.isConnecting = false;
        this.reconnectAttempts = 0;
        this.notifySubscribers("REALTIME_STATE", { status: "ONLINE" });
      };

      this.ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          const eventName = msg.event;
          const eventData = msg.data;

          // Event deduplication check
          const eventKey = `${eventName}_${eventData?.case_id || ""}_${msg.timestamp || Date.now()}`;
          if (this.processedEventIds.has(eventKey)) {
            return;
          }
          this.processedEventIds.add(eventKey);
          if (this.processedEventIds.size > 200) {
            // Trim set
            const first = this.processedEventIds.values().next().value;
            if (first) this.processedEventIds.delete(first);
          }

          this.notifySubscribers(eventName, eventData);
        } catch (e) {
          console.error("Error parsing WebSocket message:", e);
        }
      };

      this.ws.onclose = () => {
        this.isConnecting = false;
        this.ws = null;
        this.notifySubscribers("REALTIME_STATE", { status: "RECONNECTING" });
        this.scheduleReconnect();
      };

      this.ws.onerror = () => {
        this.isConnecting = false;
      };
    } catch (err) {
      this.isConnecting = false;
      this.notifySubscribers("REALTIME_STATE", { status: "OFFLINE" });
      this.scheduleReconnect();
    }
  }

  private scheduleReconnect() {
    if (this.reconnectTimeout) clearTimeout(this.reconnectTimeout);
    
    // Exponential backoff with jitter
    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts) + Math.random() * 500, this.maxReconnectDelay);
    this.reconnectAttempts++;

    this.reconnectTimeout = setTimeout(() => {
      if (this.currentUserId) {
        this.connect(this.currentUserId);
      }
    }, delay);
  }

  public disconnect() {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    this.currentUserId = null;
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.processedEventIds.clear();
    this.notifySubscribers("REALTIME_STATE", { status: "DISCONNECTED" });
  }

  private notifySubscribers(event: string, data: any) {
    this.subscribers.forEach((handler) => {
      try {
        handler(event, data);
      } catch (err) {
        console.error("Error in realtime subscriber:", err);
      }
    });
  }
}

export const realtimeService = new RealtimeService();
