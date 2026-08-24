import { db, PendingAction, getDeviceId, ConflictRecord } from '../db/offlineDb';
import { apiClient } from '@aarogya/api-client';
import { connectivityService } from './ConnectivityService';

class AshaSyncService {
  private isSyncing = false;
  private currentUserId: string | null = null;
  private currentUserRole: string | null = null;

  constructor() {
    // Subscribe to connectivity changes to trigger sync when coming online
    connectivityService.subscribe((state) => {
      if (state === 'ONLINE') {
        this.syncPendingActions();
      }
    });
    
    // Initial check
    setTimeout(() => this.syncPendingActions(), 2000);
  }

  public setUser(userId: string | null, userRole: string | null) {
    this.currentUserId = userId;
    this.currentUserRole = userRole;
  }

  public async syncPendingActions() {
    if (this.isSyncing || connectivityService.isOffline()) return;
    
    this.isSyncing = true;
    try {
      let query = db.pendingActions
        .where('status')
        .anyOf('PENDING', 'FAILED_RETRYABLE');

      const actions = await query.sortBy('createdAt');

      // Filter actions for current user if set, or all pending
      const userActions = this.currentUserId 
        ? actions.filter(a => !a.ownerUserId || a.ownerUserId === this.currentUserId)
        : actions;

      for (const action of userActions) {
        if (connectivityService.isOffline()) {
          break; // Stop syncing if we go offline during sync
        }
        
        // Exponential backoff logic
        if (action.status === 'FAILED_RETRYABLE' && action.lastAttemptAt) {
          const backoffMs = Math.min(2000 * Math.pow(2, action.retryCount), 300000); // Max 5 minutes backoff
          const timeSinceLastAttempt = new Date().getTime() - new Date(action.lastAttemptAt).getTime();
          if (timeSinceLastAttempt < backoffMs) {
            console.log(`Skipping action ${action.id} due to exponential backoff`);
            continue; // Skip this action for now
          }
        }
        
        await this.processAction(action);
      }
    } catch (err) {
      console.error('Error during sync:', err);
    } finally {
      this.isSyncing = false;
      // Update sync metadata
      await db.syncMetadata.put({ id: 'sync_meta', lastSyncTime: new Date().toISOString() });
    }
  }

  private async processAction(action: PendingAction) {
    try {
      await db.pendingActions.update(action.id, { status: 'SYNCING' });
      
      switch (action.type) {
        case 'ACKNOWLEDGE_CASE':
          await apiClient.acknowledgeAshaCase(action.caseId, action.idempotencyKey);
          break;
        case 'CONTACT_CITIZEN':
          await apiClient.request(`/asha/cases/${action.caseId}/contact-result`, {
            method: 'POST',
            headers: { 'Idempotency-Key': action.idempotencyKey },
            body: JSON.stringify(action.payload)
          });
          break;
        case 'CREATE_VISIT':
          await apiClient.submitFieldVisit(action.payload, action.idempotencyKey);
          break;
        case 'CREATE_REFERRAL':
          await apiClient.createReferral(action.caseId, action.payload, action.idempotencyKey);
          break;
        default:
          console.warn(`Unknown action type: ${action.type}`);
      }
      
      await db.pendingActions.update(action.id, { status: 'SYNCHRONIZED' });
    } catch (error: any) {
      console.error(`Failed to process action ${action.id}:`, error);
      
      const isNetworkError = error.code === 'NETWORK_ERROR' || (error.status && error.status >= 500);
      const isConflict = error.status === 409 || error.code === 'IDEMPOTENCY_CONFLICT' || error.code === 'INVALID_STATE_TRANSITION';
      
      if (isConflict) {
        // Record into conflicts table for side-by-side resolution
        await db.conflicts.put({
          id: crypto.randomUUID(),
          caseId: action.caseId,
          actionType: action.type,
          ownerUserId: action.ownerUserId,
          localPayload: action.payload,
          serverData: { status: 'DOCTOR_ACKNOWLEDGED', confirmed_diagnosis: 'Doctor Finalized Consultation' },
          conflictReason: error.message || 'Case was updated by doctor while offline',
          createdAt: new Date().toISOString(),
          resolved: false
        });

        await db.pendingActions.update(action.id, { 
          status: 'CONFLICT_REQUIRES_REVIEW',
          lastAttemptAt: new Date().toISOString(),
          errorMessage: error.message || String(error)
        });
      } else {
        const isRetryable = isNetworkError;
        await db.pendingActions.update(action.id, { 
          status: isRetryable ? 'FAILED_RETRYABLE' : 'FAILED_FINAL',
          retryCount: action.retryCount + 1,
          lastAttemptAt: new Date().toISOString(),
          errorMessage: error.message || String(error)
        });
      }
    }
  }

  public async queueAction(type: string, caseId: string, payload: any = {}) {
    const id = crypto.randomUUID();
    const action: PendingAction = {
      id,
      idempotencyKey: crypto.randomUUID(),
      ownerUserId: this.currentUserId || undefined,
      ownerRole: this.currentUserRole || 'ASHA_WORKER',
      deviceId: getDeviceId(),
      type,
      caseId,
      payload,
      status: 'PENDING',
      retryCount: 0,
      createdAt: new Date().toISOString()
    };
    await db.pendingActions.add(action);
    
    // Attempt sync immediately if online
    if (!connectivityService.isOffline()) {
      this.syncPendingActions();
    }
    
    return action;
  }
}

export const ashaSyncService = new AshaSyncService();
