export type ConnectivityState = 'ONLINE' | 'LIMITED' | 'OFFLINE' | 'CHECKING';

type Listener = (state: ConnectivityState) => void;

class ConnectivityService {
  private state: ConnectivityState = 'CHECKING';
  private listeners: Set<Listener> = new Set();
  private checkInterval: any = null;

  constructor() {
    if (typeof window !== 'undefined') {
      window.addEventListener('online', this.checkBackendHealth.bind(this));
      window.addEventListener('offline', () => this.setState('OFFLINE'));
      
      this.state = navigator.onLine ? 'CHECKING' : 'OFFLINE';
      if (this.state === 'CHECKING') {
        this.checkBackendHealth();
      }
      
      this.startPeriodicChecks();
    }
  }

  private startPeriodicChecks() {
    this.checkInterval = setInterval(() => {
      if (navigator.onLine) {
        this.checkBackendHealth();
      }
    }, 15000); // Check every 15s
  }

  public async checkBackendHealth() {
    if (!navigator.onLine) {
      this.setState('OFFLINE');
      return;
    }
    
    try {
      // Just hit a lightweight health endpoint or the base api url
      const res = await fetch('http://localhost:8000/api/asha/dashboard', { 
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('aarogya_token') || ''}`
        },
        signal: AbortSignal.timeout(3000) 
      });
      if (res.ok || res.status === 401) {
        this.setState('ONLINE');
      } else {
        this.setState('LIMITED');
      }
    } catch (err) {
      this.setState('LIMITED');
    }
  }

  private setState(newState: ConnectivityState) {
    if (this.state !== newState) {
      this.state = newState;
      this.notifyListeners();
    }
  }

  public getState(): ConnectivityState {
    return this.state;
  }

  public isOffline(): boolean {
    return this.state === 'OFFLINE' || this.state === 'LIMITED';
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
