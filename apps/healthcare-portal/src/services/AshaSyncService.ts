import { db, PendingAction, getDeviceId } from '../db/offlineDb';
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

  public async getQueue() {
    return db.pendingActions.toArray();
  }

  public async syncPendingActions() {
    if (this.isSyncing || connectivityService.isOffline()) return;

    if (!('locks' in navigator)) {
      await this.executeSync();
      return;
    }

    // Use Web Locks API to ensure only one tab syncs
    try {
      await navigator.locks.request('asha_sync_lock', { ifAvailable: true }, async (lock) => {
        if (!lock) {
          console.log('Another tab is currently syncing.');
          return;
        }
        await this.executeSync();
      });
    } catch (err) {
      console.error('Lock request failed:', err);
      // Fallback
      await this.executeSync();
    }
  }

  private async executeSync() {
    this.isSyncing = true;
    connectivityService.setState('SYNCING');
    let hasSyncedAnything = false;
    
    try {
      let query = db.pendingActions
        .where('status')
        .anyOf('PENDING', 'FAILED_RETRYABLE');

      const actions = await query.sortBy('createdAt');

      // Filter actions for current user if set, or all pending
      let userActions = this.currentUserId 
        ? actions.filter(a => !a.ownerUserId || a.ownerUserId === this.currentUserId)
        : actions;
        
      // Basic dependency sorting: REGISTER_PATIENT -> CREATE_CASE -> ACKNOWLEDGE_CASE -> CREATE_VISIT -> CREATE_REFERRAL -> CREATE_FOLLOWUP
      const typeOrder: Record<string, number> = {
        'REGISTER_PATIENT': 0,
        'CREATE_CASE': 1,
        'ACKNOWLEDGE_CASE': 2,
        'CONTACT_CITIZEN': 3,
        'CREATE_VISIT': 4,
        'CREATE_REFERRAL': 5,
        'CREATE_FOLLOWUP': 6,
        'UPDATE_FOLLOWUP': 7
      };
      userActions.sort((a, b) => (typeOrder[a.type] || 99) - (typeOrder[b.type] || 99));

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
        
        const success = await this.processAction(action);
        if (success) {
          hasSyncedAnything = true;
        }
      }
    } catch (err) {
      console.error('Error during sync:', err);
    } finally {
      this.isSyncing = false;
      connectivityService.setState('ONLINE');
      // Update sync metadata
      await db.syncMetadata.put({ id: 'sync_meta', lastSyncTime: new Date().toISOString() });
      
      if (hasSyncedAnything) {
        // Dispatch a global event to trigger UI updates
        if (typeof window !== 'undefined') {
          window.dispatchEvent(new Event('sync_completed'));
        }
      }
    }
  }

  private async processAction(action: PendingAction): Promise<boolean> {
    try {
      await db.pendingActions.update(action.id, { status: 'SYNCING' });
      
      switch (action.type) {
        case 'REGISTER_PATIENT':
          const regRes = await apiClient.registerPatient(action.payload, action.idempotencyKey);
          if (regRes && regRes.data) {
            const serverCitizenId = regRes.data.citizen_id;
            const serverCaseId = regRes.data.case_id;

            // Map local IDs to server IDs for remaining actions in the queue
            const localId = action.caseId;
            if (localId && (serverCitizenId || serverCaseId)) {
              const pending = await db.pendingActions.toArray();
              for (const p of pending) {
                let updatedPayload = { ...p.payload };
                let payloadChanged = false;
                let updatedCaseId = p.caseId;

                if (p.caseId === localId) {
                  updatedCaseId = serverCaseId || serverCitizenId;
                }

                if (p.payload) {
                  if (p.payload.case_id === localId) {
                    updatedPayload.case_id = serverCaseId;
                    payloadChanged = true;
                  }
                  if (p.payload.citizen_id === localId) {
                    updatedPayload.citizen_id = serverCitizenId;
                    payloadChanged = true;
                  }
                  if (p.payload.caseId === localId) {
                    updatedPayload.caseId = serverCaseId;
                    payloadChanged = true;
                  }
                }

                await db.pendingActions.update(p.id, {
                  caseId: updatedCaseId,
                  payload: payloadChanged ? updatedPayload : p.payload
                });
              }
            }

            // Also delete the patient draft from IndexedDB
            await db.patientDrafts.delete(`draft_${localId}`).catch(() => {});
          }
          break;
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
        case 'CREATE_FOLLOWUP':
          await apiClient.request(`/asha/followups`, {
            method: 'POST',
            headers: { 'Idempotency-Key': action.idempotencyKey },
            body: JSON.stringify(action.payload)
          });
          break;
        case 'UPDATE_FOLLOWUP':
          const { action: followUpAction, ...restPayload } = action.payload;
          await apiClient.request(`/asha/followups/${action.payload.id}/${followUpAction}`, {
            method: 'POST',
            headers: { 'Idempotency-Key': action.idempotencyKey },
            body: JSON.stringify(restPayload)
          });
          break;
        default:
          console.warn(`Unknown action type: ${action.type}`);
      }
      
      await db.pendingActions.update(action.id, { status: 'SYNCHRONIZED' });
      return true;
    } catch (error: any) {
      console.error(`Failed to process action ${action.id}:`, error);
      
      const isNetworkError = error.code === 'NETWORK_ERROR' || (error.status && error.status >= 500);
      const isAuthError = error.status === 401 || error.status === 403;
      const isConflict = error.status === 409 || error.code === 'IDEMPOTENCY_CONFLICT' || error.code === 'INVALID_STATE_TRANSITION';
      
      if (isAuthError) {
        await db.pendingActions.update(action.id, { 
          status: 'PENDING',
          lastAttemptAt: new Date().toISOString(),
          errorMessage: 'Authentication required'
        });
        connectivityService.setState('AUTH_REQUIRED');
        return false;
      }
      
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
      return false;
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
