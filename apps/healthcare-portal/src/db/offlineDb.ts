import Dexie, { Table } from 'dexie';

export interface CachedCase {
  id: string;
  ownerUserId?: string;
  ownerRole?: string;
  deviceId?: string;
  reference: string;
  priority: string;
  status: string;
  primary_concern: string;
  citizen_name: string;
  citizen_age: number;
  citizen_phone: string;
  village_name: string;
  is_pregnant: boolean;
  gestational_weeks: number | null;
  safety_rule_triggered: boolean;
  safety_rule_reason: string | null;
  symptoms: any[];
  vitals: any[];
  created_at: string;
}

export interface VisitDraft {
  id: string;
  caseId: string;
  ownerUserId?: string;
  ownerRole?: string;
  deviceId?: string;
  data: any;
  savedAt: string;
}

export interface PendingAction {
  id: string;
  idempotencyKey: string;
  ownerUserId?: string;
  ownerRole?: string;
  deviceId?: string;
  type: string; // 'ACKNOWLEDGE_CASE', 'CONTACT_CITIZEN', 'CREATE_VISIT', 'CREATE_REFERRAL'
  caseId: string;
  payload: any;
  status: 'PENDING' | 'SYNCING' | 'SYNCHRONIZED' | 'FAILED_RETRYABLE' | 'FAILED_FINAL' | 'CONFLICT_REQUIRES_REVIEW';
  retryCount: number;
  createdAt: string;
  lastAttemptAt?: string;
  errorMessage?: string;
}

export interface ConflictRecord {
  id: string;
  caseId: string;
  actionType: string;
  ownerUserId?: string;
  localPayload: any;
  serverData: any;
  conflictReason: string;
  createdAt: string;
  resolved: boolean;
}

export interface SyncMetadata {
  id: string; // 'sync_meta'
  lastSyncTime: string;
}

export interface PatientDraft {
  id: string;
  clientRegistrationId: string;
  ownerUserId?: string;
  ownerRole?: string;
  deviceId?: string;
  currentStep: number;
  data: any;
  savedAt: string;
}

export class OfflineDatabase extends Dexie {
  cachedCases!: Table<CachedCase, string>;
  visitDrafts!: Table<VisitDraft, string>;
  patientDrafts!: Table<PatientDraft, string>;
  pendingActions!: Table<PendingAction, string>;
  conflicts!: Table<ConflictRecord, string>;
  syncMetadata!: Table<SyncMetadata, string>;

  constructor() {
    super('AarogyaSahayakDB');
    this.version(3).stores({
      cachedCases: 'id, status, ownerUserId',
      visitDrafts: 'id, caseId, ownerUserId',
      patientDrafts: 'id, clientRegistrationId, ownerUserId',
      pendingActions: 'id, type, status, ownerUserId',
      conflicts: 'id, caseId, ownerUserId, resolved',
      syncMetadata: 'id'
    });
  }
}

export const db = new OfflineDatabase();

export function getDeviceId(): string {
  let devId = localStorage.getItem('aarogya_device_id');
  if (!devId) {
    devId = 'DEV-' + crypto.randomUUID();
    localStorage.setItem('aarogya_device_id', devId);
  }
  return devId;
}
