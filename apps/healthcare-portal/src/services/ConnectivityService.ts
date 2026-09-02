import { apiClient } from '@aarogya/api-client';

export type ConnectivityState = 'ONLINE' | 'DEGRADED' | 'OFFLINE' | 'CHECKING' | 'SYNCING' | 'AUTH_REQUIRED';

type Listener = (state: ConnectivityState) => void;

class ConnectivityService {
  private state: ConnectivityState = 'CHECKING';
  private listeners: Set<Listener> = new Set();
  private checkInterval: any = null;
  private syncInProgress: boolean = false;

  constructor() {
    if (typeof window !== 'undefined') {
      window.addEventListener('online', this.checkBackendHealth.bind(this));
      window.addEventListener('offline', () => this.setState('OFFLINE'));
      window.addEventListener('focus', this.checkBackendHealth.bind(this));
      
      this.state = navigator.onLine ? 'CHECKING' : 'OFFLINE';
      if (this.state === 'CHECKING') {
        this.checkBackendHealth();
      }
      
      this.startPeriodicChecks();
    }
  }

  private startPeriodicChecks() {
    this.checkInterval = setInterval(() => {
      if (navigator.onLine && !this.syncInProgress) {
        this.checkBackendHealth();
      }
    }, 15000); // Check every 15s
  }

  public async checkBackendHealth() {
    if (!navigator.onLine) {
      this.setState('OFFLINE');
      return;
    }
    
    // Don't interrupt if we are actively syncing or authenticating
    if (this.state === 'SYNCING' || this.state === 'AUTH_REQUIRED') {
      return;
    }
    
    try {
      const result = await apiClient.checkHealth(5000);
      if (result.ok) {
        this.setState('ONLINE');
      } else {
        this.setState('DEGRADED');
      }
    } catch {
      this.setState('DEGRADED');
    }
  }

  public setState(newState: ConnectivityState) {
    if (this.state !== newState) {
      this.state = newState;
      if (newState === 'SYNCING') this.syncInProgress = true;
      else if (newState === 'ONLINE' || newState === 'DEGRADED' || newState === 'OFFLINE' || newState === 'AUTH_REQUIRED') this.syncInProgress = false;
      this.notifyListeners();
    }
  }

  public getState(): ConnectivityState {
    return this.state;
  }

  public isOffline(): boolean {
    return this.state === 'OFFLINE' || this.state === 'DEGRADED';
  }

  public subscribe(listener: Listener): () => void {
    this.listeners.add(listener);
    // Notify immediately on subscribe
    listener(this.state);
    return () => {
      this.listeners.delete(listener);
    };
  }

  private notifyListeners() {
    this.listeners.forEach(listener => listener(this.state));
  }
}

export const connectivityService = new ConnectivityService();
