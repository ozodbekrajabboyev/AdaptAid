# System diagrams

All diagrams are Mermaid; GitHub, VS Code and https://mermaid.live render them, and they can be exported as PNG/SVG for the report.

## 1. Architecture

```mermaid
flowchart TB
    subgraph Users
      S[Student] --- T[Teacher] --- A[Administrator]
    end
    subgraph Web["Web app (Next.js 16, React 19)"]
      UI[Student, teacher and admin pages]
      PX["/api/* same-origin proxy (route handler)"]
    end
    subgraph API["API (FastAPI)"]
      R[Routers: auth, onboarding, quiz, recommendations, events, content, teacher, admin, study]
      SV[Services: learner model, recommend, quiz, events, study, teacher, admin]
      J[Nightly jobs: personas, risk, aid stats, CF, BKT refit]
    end
    subgraph Engine["Engine (pure Python, unit-tested)"]
      BKT[Bayesian Knowledge Tracing]
      STY[Learning-preference model]
      HYB[Hybrid scorer + MMR re-rank + explanations]
      CF[Collaborative filtering: item-kNN / ALS]
      GRP[Group suggestions]
      PRF[Personas + risk]
      SIM[Learner simulator]
    end
    DB[(PostgreSQL)]
    RS[Research scripts: ASSISTments, OULAD, simulation]
    Users --> UI --> PX --> R --> SV --> Engine
    J --> Engine
    SV --> DB
    J --> DB
    RS --> Engine
    RS -->|import-research| DB
```

## 2. Data-flow diagram, level 0 (context)

```mermaid
flowchart LR
    S([Student]) -- "answers, aid usage, ratings, questionnaire" --> P((AdaptAid))
    P -- "recommended aids with reasons, mastery, learning path" --> S
    T([Teacher]) -- "teaching aids, questions, classes" --> P
    P -- "heatmap, risk flags, class aid suggestions, aid effectiveness" --> T
    A([Administrator]) -- "accounts, study settings, job triggers" --> P
    P -- "model report, pilot export" --> A
    D[(Public datasets: ASSISTments, OULAD)] -- "offline evaluation" --> P
```

## 3. Data-flow diagram, level 1

```mermaid
flowchart TB
    S([Student]) --> P1[1.0 Onboarding: questionnaire + diagnostic]
    P1 --> D2[(Style profiles)]
    P1 --> D3[(Responses + mastery)]
    S --> P2[2.0 Use a teaching aid]
    P2 --> D4[(Aid uses + interactions)]
    S --> P3[3.0 Quick check]
    P3 -->|BKT update| D3
    P3 -->|residual gain| D4
    P3 -->|style update| D2
    D1[(Content: concepts, aids, questions)] --> P4[4.0 Recommend]
    D2 --> P4
    D3 --> P4
    D5[(Aid stats + CF model)] --> P4
    P4 --> D6[(Recommendation lists + items)]
    D6 --> S
    D4 --> P5[5.0 Nightly jobs]
    D3 --> P5
    P5 --> D5
    P5 --> D7[(Personas + risk)]
    D3 --> P6[6.0 Teacher analytics]
    D7 --> P6
    D5 --> P6
    P6 --> T([Teacher])
```

## 4. Use cases

```mermaid
flowchart LR
    S([Student]) --- U1(Register / join class)
    S --- U2(Answer preference questionnaire)
    S --- U3(Take diagnostic)
    S --- U4(View recommendations with reasons)
    S --- U5(Use a teaching aid)
    S --- U6(Take a quick check)
    S --- U7(View learning path and progress)
    S --- U8(Pilot: consent, pre/post test, survey)
    T([Teacher]) --- U9(View class heatmap and risk)
    T --- U10(Get class teaching-aid suggestions)
    T --- U11(Manage aids and questions)
    T --- U12(Create class and share code)
    A([Administrator]) --- U13(Manage users)
    A --- U14(Run jobs / view model report)
    A --- U15(Configure and export pilot study)
```

## 5. Sequence: one turn of the adaptive loop

```mermaid
sequenceDiagram
    actor S as Student
    participant W as Web app
    participant API as FastAPI
    participant E as Engine
    participant DB as PostgreSQL
    S->>W: open recommended aid
    W->>API: POST /api/events {open, item}
    API->>DB: aid_use(p_open = current mastery)
    S->>W: finish aid, rate it
    W->>API: POST /api/events {complete, rate}
    S->>W: take quick check
    W->>API: POST /api/quiz/start {check, use_id}
    API->>DB: 3 unseen check questions
    loop each answer
      W->>API: POST /answer
      API->>E: bkt.update(p, correct)
      API->>DB: response(p_before, p_after), mastery
    end
    W->>API: POST /finish
    API->>E: residual_gain(p_open, answers)
    API->>E: style.update(profile, aid style, gain)
    API->>E: policy.recommend(learner view, catalogue)
    E-->>API: ranked aids + signal parts
    API->>E: explain(item, contributions)
    API->>DB: new recommendation list (policy, arm, phase, versions)
    API-->>W: mastery before/after, gain, new list id
    W-->>S: mastery change, "see what's next"
```

## 6. Deployment

```mermaid
flowchart LR
    B[Browser] -- HTTPS 443 --> C[Caddy: TLS, compression]
    C --> W[web: Next.js standalone :3000]
    W -- "/api/* (server side)" --> API[api: FastAPI + scheduler :8000]
    API --> PG[(db: PostgreSQL 17, volume pgdata)]
```
