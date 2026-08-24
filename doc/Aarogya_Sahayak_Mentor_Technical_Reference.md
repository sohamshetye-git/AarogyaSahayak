# Aarogya Sahayak \| Mentor Technical Reference \| SIH 2026

## Tech Stack, User Flow & Data Flow

This Markdown version preserves the mentor reference document's
technical stack, architecture, user/data flows, safety flow, offline
handling, MVP scope, cost summary, impact audience, existing-solution
comparison, and accessibility sections.

## 1. Tech Stack

  -----------------------------------------------------------------------------------------------
  Area              Technology                  Role                            Status
  ----------------- --------------------------- ------------------------------- -----------------
  Mobile            React Native + Expo         Citizen/ASHA voice-first apps,  MVP
                                                alerts, case UI                 

  Local data        SQLite                      Offline cache, pending queue,   MVP
                                                sync state                      

  Edge AI           Python + TensorFlow Lite    Narrow local risk-screening     MVP if stable
                                                inference                       

  Backend           FastAPI + Python            REST APIs, validation,          MVP
                                                orchestration, data handling    

  Language          BHASHINI                    Indic speech-to-text,           Integration/MVP
                                                translation, text-to-speech     

  Foundation AI     Google Gemini               Understanding, extraction,      MVP
                                                reasoning, response generation  

  Agents            Lyzr                        Medical, Scheme and             Integration/MVP
                                                Validation/Reflection           
                                                orchestration                   

  Medical RAG       Milvus + embeddings         Semantic retrieval of approved  Integration
                                                guideline content               

  Scheme logic      Neo4j                       Eligibility/rule/relationship   Integration
                                                graph                           

  Current search    Tavily                      Current scheme/policy           Integration
                                                retrieval; prefer authoritative 
                                                sources                         

  Automation        n8n                         Escalation, alerts, follow-ups, MVP/Integration
                                                workflow triggers               

  Reporting         LaTeX                       Deterministic clinical PDF      MVP/Prototype
                                                generation                      

  External APIs     ABDM/eSanjeevani/approved   Healthcare/government           Integration
                    APIs                        interoperability                

  Hosting           Render                      MVP backend deployment          MVP
  -----------------------------------------------------------------------------------------------

## 2. Technical Architecture

``` text
Citizen App / ASHA App
        |
        v
React Native + Expo
        |
        +-- SQLite + supported TFLite
        |
        v
Connectivity Check
      /       \
 OFFLINE     ONLINE
    |           |
 Local       FastAPI
 screening      |
    |         BHASHINI
    |           |
    +-----+-----+
          |
          v
  Agent Orchestrator
      /     |      \
 Medical  Scheme  Validation
 Agent    Agent   Agent
    |        |       |
 Milvus   Neo4j    Reflection
          + Tavily
      \     |      /
          Gemini
             |
             v
      Validated output
         /        \
     Citizen       n8n
                    |
             ASHA / PHC / Doctor
                    |
                  LaTeX
                    |
                   PDF
```

## 3. User Flow

1.  Citizen speaks in a supported regional language.
2.  React Native captures voice.
3.  Connectivity is checked.
4.  **Offline:** SQLite stores the request and supported TFLite performs
    only the narrow local screening task.
5.  **Online:** FastAPI receives the request.
6.  BHASHINI performs speech-to-text and/or translation.
7.  Intent and clinical/scheme entities are extracted.
8.  Medical Agent or Scheme Agent is selected.
9.  Evidence is retrieved: Medical Agent uses Milvus; Scheme Agent uses
    Neo4j plus current authoritative search.
10. Gemini reasons over the retrieved evidence.
11. Validation/Reflection checks evidence, contradiction, confidence and
    unsafe claims.
12. A safe structured response is returned to the citizen.
13. If the case is high-risk, n8n triggers escalation.
14. ASHA / PHC / Doctor receives the case.
15. A structured clinical PDF can be generated using LaTeX.

## 4. End-to-End Data Flow

``` text
VOICE
  |
  v
React Native
  |
  v
Audio + session metadata
  |
  v
Connectivity Check
  /                    OFFLINE                ONLINE
  |                      |
SQLite + TFLite        FastAPI
local safe screening      |
  |                    BHASHINI
  |                      |
  +----------+-----------+
             |
             v
     Agent Router / Lyzr
          /         Medical Agent   Scheme Agent
      |              |
   Milvus       Neo4j / Tavily
          \        /
             v
           Gemini
             |
             v
         Validation
             |
             v
      Structured result
          /             User response  Risk event
                       |
                      n8n
                       |
               ASHA / PHC / Doctor
                       |
                    LaTeX PDF
```

## 5. Main Data Objects

  -----------------------------------------------------------------------
  Object                  Key fields              Purpose
  ----------------------- ----------------------- -----------------------
  User/Patient            ID, language,           Identify workflow and
                          session/consent state   preferences

  Voice Interaction       session ID, timestamp,  Trace interaction
                          language, audio         
                          reference               

  Clinical Entities       symptoms, vitals,       Structured clinical
                          pregnancy week, risk    information
                          flags                   

  Evidence                source, document/chunk  Support and audit AI
                          ID, retrieval metadata  response

  Scheme Query            scheme, eligibility     Scheme reasoning
                          attributes, documents   

  Risk Event              risk level, urgency,    Trigger escalation
                          reason, timestamp       

  Sync Event              local ID, server ID,    Offline-to-online
                          status, retries         synchronization

  Report                  case ID, structured     Clinical document
                          fields, generated time  output
  -----------------------------------------------------------------------

## 6. Trust & Safety Flow

``` text
User query
   |
   v
Retrieve authoritative/approved evidence
   |
   v
Agent reasoning + Gemini
   |
   v
Validation / Reflection
   |
   +-- Unsupported claim? --> revise/reject
   +-- Contradiction? ------> revise/reject
   +-- High-risk? ----------> escalate
   +-- Supported? ----------> release structured answer
   |
   v
Deterministic software performs approved actions
```

-   Medical output is screening/decision support, not autonomous
    diagnosis.
-   LLM output should not directly execute high-impact government
    transactions.
-   External API timeout/error must remain a failure state, not be
    interpreted as success.
-   Evidence/source metadata should be retained for important responses.

## 7. Offline & Failure Handling

``` text
Internet drops
    |
    v
App detects offline
    |
    v
Store request in SQLite
    |
    v
Run only the supported local TFLite task
    |
    v
Safe local guidance within model scope
    |
    v
Internet restored
    |
    v
Sync queue -> FastAPI
    |
    v
Full BHASHINI + AI + evidence workflow
    |
    v
Case status updated
```

## 8. MVP Scope

  -----------------------------------------------------------------------
  Priority                What to show            Future/integration
  ----------------------- ----------------------- -----------------------
  P0                      React Native voice      More agents and
                          flow + FastAPI +        large-scale
                          Gemini + one evidence   integrations
                          path                    

  P0                      SQLite offline queue +  Full offline
                          sync                    conversational AI

  P0                      ASHA/doctor case        Full government
                          workflow                production connectivity

  P1                      Validation/reflection   Advanced confidence
                          step                    models

  P1                      One escalation workflow Many notification
                                                  channels

  P1                      Structured clinical     Large-scale
                          report                  reporting/records

  P2                      TFLite local screening  Broader edge
                          if stable               diagnostics

  P2                      BHASHINI connected flow More Indian
                          if stable               languages/dialects
  -----------------------------------------------------------------------

## 9. MVP Cost Summary

The SIH MVP is designed to minimize incremental cost by using
open-source software and free/student tiers wherever practical. The
estimate assumes the team already has development laptops and Android
phones for testing.

  ----------------------------------------------------------------------------------
  Component          Technology        MVP purpose                 Estimated cost
  ------------------ ----------------- --------------------------- -----------------
  Mobile application React Native +    Citizen & ASHA voice-first  ₹0
                     Expo              application                 

  Local database     SQLite            Offline cache, pending      ₹0
                                       requests, sync state        

  Edge AI            Python +          Narrow offline              ₹0
                     TensorFlow Lite   risk-screening inference    

  Backend            FastAPI + Python  APIs, validation,           ₹0
                                       orchestration               

  Foundation AI      Google Gemini     Reasoning, extraction,      ₹0--₹1,000
                                       response generation         

  Agent              Lyzr Community    Medical/Scheme/Validation   ₹0
  orchestration                        agent flow                  

  Vector database    Milvus / Zilliz   Medical guideline semantic  ₹0
                     Free              retrieval                   

  Graph database     Neo4j AuraDB Free Scheme relationships and    ₹0
                                       eligibility logic           

  Web search         Tavily            Current scheme information  ₹0
                     Free/Student      retrieval                   

  Automation         n8n self-hosted   Escalation and workflow     ₹0--₹500
                                       automation                  

  Indic language     BHASHINI          Speech recognition /        ₹0--₹1,000\*
  layer                                translation / TTS           

  Clinical reporting LaTeX             Structured PDF report       ₹0
                                       generation                  

  Cloud hosting      Render            MVP backend deployment      ₹0--₹2,500

  Database/storage   Small MVP storage Application data, files,    ₹0--₹1,000
                                       backups                     

  Domain             Optional domain   Professional demo URL       ₹0--₹1,500/year

  Testing hardware   Existing          Prototype testing           ₹0 if already
                     phones/laptops                                available
  ----------------------------------------------------------------------------------

## 10. Impact Audience

  -----------------------------------------------------------------------
  Impact audience         Current challenge       Aarogya Sahayak impact
  ----------------------- ----------------------- -----------------------
  Rural & underserved     Limited digital         Voice-first access,
  citizens                literacy, language      multilingual
                          barriers, connectivity  interaction, defined
                          and difficulty          offline support and
                          navigating services.    simpler healthcare
                                                  navigation.

  Pregnant women &        Warning symptoms may    Structured symptom
  high-risk patients      not be recognized or    capture, risk-screening
                          escalated quickly.      support and priority
                                                  escalation to
                                                  healthcare workers.

  ASHA / frontline        Manual data collection, Voice-assisted capture,
  workers                 paperwork, follow-ups   structured case
                          and fragmented          records, alerts,
                          information.            follow-up workflows and
                                                  report generation.

  PHCs / healthcare       Cases may arrive with   Structured case
  facilities              incomplete or           summaries and priority
                          unstructured            signals for faster
                          information.            review.

  Doctors / healthcare    Limited context before  Structured patient
  providers               remote or in-person     information and
                          consultation.           evidence context to
                                                  support clinical
                                                  review.

  Government health       Fragmented digital      Potential
  departments             workflows and           interoperability layer
                          difficulty coordinating connecting citizen,
                          services.               frontline and provider
                                                  workflows.

  Government-scheme       Difficulty discovering  Conversational scheme
  beneficiaries           and understanding       assistance,
                          relevant schemes.       eligibility-oriented
                                                  questions and current
                                                  information retrieval.
  -----------------------------------------------------------------------

## 11. Existing / Near-existing Solutions vs Aarogya Sahayak

  ---------------------------------------------------------------------------------------------
  Existing /         What it provides      Gap relative to Aarogya      Aarogya Sahayak
  near-existing                            Sahayak                      difference
  solution                                                              
  ------------------ --------------------- ---------------------------- -----------------------
  ABDM               National              Infrastructure rather than a Adds an AI-assisted
                     digital-health        dedicated voice-first        citizen/ASHA
                     infrastructure,       frontline AI workflow.       orchestration layer
                     interoperability,                                  that can integrate with
                     registries and                                     digital-health
                     health-data exchange.                              infrastructure.

  Aarogya Setu 2.0   Personal health       Citizen                      Adds voice-first
                     records, ABHA, linked health-service/record access triage/scheme
                     records, appointments is the primary focus.        assistance and ASHA
                     and health services.                               workflow automation.

  eSanjeevani        National telemedicine Primarily                    Captures and structures
                     service connecting    consultation/telemedicine;   the case before
                     patients/facilities   it is not the complete       escalation and can
                     with doctors and      pre-consultation ASHA AI     route high-priority
                     specialists.          workflow.                    cases into provider
                                                                        workflows.

  Government scheme  Official scheme       Users often need to search,  Scheme Agent provides
  portals/services   information,          read and understand          conversational,
                     applications and      information across services. eligibility-oriented
                     eligibility                                        assistance and can
                     information.                                       retrieve current
                                                                        information.

  BHASHINI           Indian-language       Language infrastructure      Uses the language layer
                     speech, translation   alone does not provide       inside a
                     and language          healthcare triage or         healthcare-specific
                     technology            workflow orchestration.      citizen → AI → ASHA →
                     infrastructure.                                    doctor workflow.

  Generic AI /       Conversational        May not have offline         Combines retrieval,
  health chatbots    answers,              support, authoritative       specialized agents,
                     summarization and     retrieval, workflow          validation, offline
                     general assistance.   automation or controlled     capability and
                                           transaction boundaries.      deterministic
                                                                        escalation/reporting.

  Traditional ASHA   Community-level       Manual information           ASHA Copilot approach:
  workflow           health support and    collection and coordination  voice capture →
                     linkage with the      burden.                      structured case → risk
                     health system.                                     flag → escalation →
                                                                        report/follow-up.
  ---------------------------------------------------------------------------------------------

## 12. Accessibility

Accessibility is a core architectural requirement. The design targets
barriers in connectivity, language, literacy, device capability,
age/disability and distance from healthcare.

  --------------------------------------------------------------------------
  Accessibility barrier   How it affects users    Aarogya Sahayak response
  ----------------------- ----------------------- --------------------------
  Internet connectivity   Rural/remote users may  SQLite offline queue;
                          experience unreliable   synchronize when online;
                          connectivity.           narrow local TFLite
                                                  screening where
                                                  implemented.

  Digital literacy        Complex forms and menus Voice-first interaction
                          can prevent adoption.   and minimal navigation.

  Language                Users may prefer        BHASHINI-based
                          Marathi, Hindi or       speech/translation/TTS
                          another Indian          layer.
                          language.               

  Low literacy            Reading long medical    Speak instead of type;
                          instructions is         receive important guidance
                          difficult.              through audio.

  Low-end/shared devices  High-end hardware       Lightweight mobile
                          cannot be assumed.      interface, local storage
                                                  and narrowly scoped edge
                                                  models.

  Elderly users           Small controls and      Large controls, voice
                          text-heavy interfaces   interaction and simplified
                          can be difficult.       flows.

  Disability              Visual/motor            Audio-first interaction
                          limitations can create  plus accessible controls,
                          interface barriers.     text sizing and
                                                  screen-reader-compatible
                                                  UI where implemented.

  Distance from           Specialists may not be  Structured escalation
  healthcare              physically nearby.      toward ASHA/PHC/doctor and
                                                  compatible telehealth
                                                  workflows.

  Scheme access           People may not know     Conversational scheme
                          which scheme or service discovery and
                          applies to them.        eligibility-oriented
                                                  assistance.

  Frontline-worker        Manual documentation    Structured voice capture,
  workload                and follow-up consume   automated alerts,
                          time.                   follow-ups and report
                                                  generation.
  --------------------------------------------------------------------------
