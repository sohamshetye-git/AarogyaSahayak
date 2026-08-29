# Aarogya Sahayak — ASHA Offline, Referral, and Follow-up Diagnostic Report

## 1. Offline Connectivity and Synchronization Failures

**Defect:** Offline actions remain unsynchronized after connectivity returns, and frontend views do not reliably update.

**Root Causes:**
1. **Connectivity Detection Flaws:** `ConnectivityService.ts` relies primarily on `navigator.onLine` and a basic polling loop against a protected endpoint (`/api/asha/dashboard`) without differentiating between actual backend reachability (Online) vs. internet-only (Degraded). It lacks a robust state machine (`OFFLINE`, `CHECKING`, `ONLINE`, `DEGRADED`, `SYNCING`, `AUTH_REQUIRED`).
2. **Missing Sync Locks:** `AshaSyncService.ts` does not use the Web Locks API or a robust single-leader mechanism. If multiple browser tabs are open, they can race to synchronize the same pending action, leading to duplicate records in PostgreSQL.
3. **No Dependency Graph:** The sync queue processes items blindly without respecting dependencies (e.g., a Referral is synced before its parent Visit/Case is fully registered and acknowledged).
4. **Cache Invalidation:** After a successful background sync, the sync worker does not invalidate React Query keys. This forces the ASHA to manually refresh the page to see the synchronized data, masking the success of the sync.

## 2. Timeline Integrity and Duplication

**Defect:** Timeline contains repeated `Case Acknowledged` and `Referral Acknowledged` events.

**Root Causes:**
1. **Idempotency Bypass & Unconditional Auditing:** In `backend/app/routers/asha.py` (and similarly in `doctor.py`), the `acknowledge_case` endpoint checks for an idempotency key. However, if the frontend omits the key (e.g., rapid double-clicking before the first request finishes), the router proceeds to `CaseService.update_status()`. 
2. **State Machine Short-Circuiting:** `update_status` correctly realizes the case is *already* in `ASHA_ACKNOWLEDGED` and returns without raising an error. 
3. **Blind Audit Insertion:** The router then unconditionally executes `db.add(AuditLog(...))` regardless of whether a state transition actually occurred. This results in duplicate audit events appended to the timeline for every extraneous network request.

## 3. Referral and Scheduled Follow-up Propagation

**Defect:** Referral and scheduled follow-up actions do not reliably propagate to Doctor and ASHA queues.

**Root Causes:**
1. **Transaction Boundaries:** In `referral_service.py` and `case_service.py`, domain events / notifications are sometimes fired before the main database transaction is committed, or they are lost if the transaction rolls back. 
2. **Missing Authoritative Follow-up Workspace:** Follow-ups are currently treated as lightweight mock tasks rather than first-class authoritative clinical entities. There is no comprehensive individual follow-up workspace (`/asha/followups/:followupId`) capable of recording new repeat vitals separately from the original case vitals.
3. **Referral State Desynchronization:** The ASHA view does not consistently differentiate between `Sent to PHC`, `Doctor Acknowledged`, and `Doctor Review In Progress` because the frontend components lack polling/WebSocket subscriptions for real-time status updates on specific referrals.

## 4. Clinical Safety Text Boundary Violations

**Defect:** Screenshot still contains diagnosis-like wording: `Possible Pre-eclampsia`.

**Root Cause:**
1. **Hardcoded Diagnostic Terminology:** `backend/app/safety/emergency_rules.py` and `backend/app/seeds/seed_data.py` explicitly inject the text `"Pregnancy-related warning signs with elevated blood pressure (Possible Pre-eclampsia)"`. This violates the strict invariant that ASHA workers must only receive deterministic, non-diagnostic action guidance.

---
**Next Steps:** Proceeding to generate the Implementation Plan to resolve these foundational issues.
