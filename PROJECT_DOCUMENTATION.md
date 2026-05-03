# TPS-G Key Person Development System
## Project Documentation & Analysis Report

**Created:** 2026-05-01
**Last Updated:** 2026-05-01
**Version:** 1.5.0

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Tech Stack](#2-tech-stack)
3. [Project Structure](#3-project-structure)
4. [MVC Architecture](#4-mvc-architecture)
5. [Database Schema](#5-database-schema)
6. [User Roles & Workflows](#6-user-roles--workflows)
7. [CRUD Matrix](#7-crud-matrix)
8. [Gap Analysis & Issues](#8-gap-analysis--issues)
9. [Implementation Roadmap](#9-implementation-roadmap)
10. [UI/UX Pattern Analysis](#10-uux-pattern-analysis)
11. [Security Analysis](#11-security-analysis)
12. [Recommended Improvements](#12-recommended-improvements)

---

## 1. Project Overview

**Project Name:** TPS-G Key Person Development System
**Organization:** TMMIN (PT Toyota Motor Manufacturing Indonesia)
**Purpose:** Digitalization of the Toyota Production System development program, tracking employee progress through TPS levels (Basic → SW → Step Up → Advance → KP 3 → KP 4), managing workshops, evaluations, and training.

### Core Modules:
- Employee Management with Excel Import
- Participant Portal with TPS Level Roadmap
- OMDD Assessor Portal with Workshop Evaluation
- Management Dashboard with Analytics & KPI
- News & Announcement System
- Learning Module System
- PDF Export for Reports

---

## 2. Tech Stack

| Layer | Technology | Version |
|-------|------------|---------|
| Backend | Python Flask | 3.1.3 |
| ORM | Flask-SQLAlchemy | - |
| Auth | Flask-Login | - |
| Database | MySQL (pymysql) | - |
| Frontend | Jinja2 Templates | - |
| Charts | Chart.js | 3.x |
| PDF Export | FastAPI | (separate service) |
| Excel Import | Pandas | - |
| Python | Python | 3.13 |

---

## 3. Project Structure

```
project_tps/
├── app.py                      # Flask app entry point
├── config.py                   # Configuration (DB, App settings)
├── migrate.py                  # Database migration utilities
├── create_tables.py            # Table creation script
├── pdf_service.py              # FastAPI PDF export service
├── requirements.txt            # Python dependencies
├── .env                         # Environment variables
│
├── app/
│   ├── __init__.py             # App factory (create_app)
│   ├── gabung_kode.py           # Utility scripts
│   │
│   ├── models/                  # DATA LAYER (M)
│   │   ├── __init__.py
│   │   ├── user.py              # User (auth + roles)
│   │   ├── employee.py          # Employee, Plant, Division, Department,
│   │   │                        # WorkshopActivity, WorkshopEvaluation, BatchStat
│   │   ├── development.py       # Training, Activity, News
│   │   ├── module.py            # LearningModule
│   │   └── audit.py             # AuditLog (CRUD audit trail)
│   │
│   ├── services/               # SERVICE LAYER (Business Logic)
│   │   ├── __init__.py
│   │   ├── employee_service.py  # Employee & Organization CRUD
│   │   ├── news_service.py      # News CRUD
│   │   ├── training_service.py  # Training CRUD
│   │   └── audit_service.py     # Audit logging
│   │
│   ├── forms/                  # FORM LAYER (Validation)
│   │   ├── __init__.py
│   │   ├── news_form.py         # News WTForms validation
│   │   └── training_form.py     # Training WTForms validation
│   │
│   ├── routes/                  # CONTROLLER LAYER (C)
│   │   ├── __init__.py
│   │   ├── auth.py              # Authentication (login, register, logout)
│   │   ├── participant.py       # Participant portal
│   │   ├── omdd.py              # OMDD Assessor portal
│   │   ├── tpsg.py              # TPSG Admin portal
│   │   ├── management.py        # Management dashboard
│   │   ├── bod.py               # Board of Directors dashboard
│   │   └── division_head.py     # Division Head dashboard
│   │
│   ├── decorators.py            # Role-based access decorators
│   │
│   └── templates/               # VIEW LAYER (V)
│       ├── base.html            # Main layout (dark cyber theme)
│       ├── macros.html          # Jinja2 reusable macros
│       ├── omdd/
│       │   └── base.html
│       ├── auth/                # login, register, change_password
│       ├── participant/         # dashboard, activity, modules, directory, training
│       ├── omdd/                # dashboard, detail, assess, participants, etc.
│       ├── tpsg/                # dashboard, employees, import_excel, etc.
│       ├── management/           # dashboard, utilized_kp, tps_advance, etc.
│       ├── bod/                  # Executive dashboard
│       ├── division_head/        # Division head dashboard
│       └── errors/               # 403, 404, 429, 500 error pages
│
└── static/
    ├── uploads/
    │   ├── photos/             # Employee photos
    │   ├── certificates/      # Employee certificates
    │   └── modules/           # Learning module files
    ├── img/                    # Dashboard images
    └── css/                    # (empty - no custom CSS files)
```

---

## 4. MVC Architecture

### Current MVC Pattern

```
┌─────────────────────────────────────────────────────────────┐
│                    CONTROLLER (Routes)                      │
│  app/routes/{auth,participant,omdd,tpsg,management}.py      │
│                                                              │
│  Responsibilities:                                          │
│  - Handle HTTP request/response                             │
│  - Query database via Models                                │
│  - Apply business logic                                     │
│  - Render templates                                         │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                       MODEL (Data Layer)                     │
│  app/models/{user,employee,development,module}.py            │
│                                                              │
│  Responsibilities:                                          │
│  - Define database schema (SQLAlchemy)                      │
│  - Simple property getters                                  │
│  - Relationship definitions                                 │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                       VIEW (Templates)                       │
│  app/templates/{auth,participant,omdd,tpsg,management}/     │
│                                                              │
│  Responsibilities:                                          │
│  - HTML rendering with Jinja2                               │
│  - Display data from controller                            │
│  - Form submission to controller                            │
└─────────────────────────────────────────────────────────────┘
```

### Role-Based Access Control

| Blueprint | URL Prefix | Roles |
|-----------|-----------|-------|
| `auth` | `/auth` | All users |
| `participant` | `/participant` | `participant` |
| `omdd` | `/omdd` | `omdd` |
| `tpsg` | `/tpsg` | `tpsg`, `admin` |
| `management` | `/management` | `management`, `bod` |

### Decorators Used
- `@login_required` - Authentication required
- `@management_required` - Management role check
- `@tpsg_required` - TPSG/Admin role check
- Inline role checks in OMDD routes

---

## 5. Database Schema

### Entity Relationship Diagram

```
┌──────────────┐       ┌──────────────┐
│    users     │       │    plants    │
├──────────────┤       ├──────────────┤
│ id (PK)      │       │ id (PK)      │
│ username     │       │ name         │
│ password_hash│       └───────┬──────┘
│ role         │               │
│ is_first_login       ┌──────▼──────┐
│ employee_id (FK)────►│  employees  │
└──────────────┘       ├──────────────┤
                       │ id (PK)      │
                       │ name         │
                       │ username(NIK)│
                       │ birth_date   │
                       │ position     │
                       │ photo        │
                       │ certificate  │
                       │ current_tps_level │
                       │ previous_tps_level │
                       │ tahun_lulus_terakhir │
                       │ tahun_lulus_saiki ini │
                       │ last_activity_theme │
                       │ last_activity_type │
                       │ batch         │
                       │ registration_year │
                       │ status        │
                       │ plant_id (FK) │◄────────┐
                       │ division_id(FK)│        │
                       │ department_id(FK)       │
                       └───────┬──────┘        │
                               │               │
              ┌────────────────┼───────────────┘
              │               │
     ┌────────▼────────┐ ┌────▼────────────┐
     │ divisions        │ │ departments      │
     ├────────┤         │ ├─────────────────┤
     │ id (PK)│         │ │ id (PK)         │
     │ name   │         │ │ name            │
     └────────┘         │ │ division_id(FK) │
                        │ └─────────────────┘
                        │
     ┌──────────────────▼──────────────────┐
     │       workshop_activities          │
     ├───────────────────────────────────┤
     │ id (PK)                           │
     │ employee_id (FK)                  │
     │ theme_title                       │
     │ participant_file                  │
     │ submitted_at                      │
     │ status                            │
     │ score                             │
     │ feedback                          │
     └───────────────────────────────────┘

     ┌──────────────────▼──────────────────┐
     │       workshop_evaluations        │
     ├───────────────────────────────────┤
     │ id (PK)                           │
     │ employee_id (FK)                  │
     │ ws_1 to ws_7 (scores)             │
     │ final_decision                    │
     │ notes                             │
     │ evaluated_by                       │
     │ evaluated_at                      │
     └───────────────────────────────────┘

     ┌──────────────────▼──────────────────┐
     │           activities               │
     ├───────────────────────────────────┤
     │ id (PK)                           │
     │ employee_id (FK)                  │
     │ theme_title                       │
     │ status                            │
     │ progress_percentage               │
     │ file_path                         │
     │ score                             │
     │ feedback                          │
     │ submitted_at                      │
     └───────────────────────────────────┘

     ┌──────────────────▼──────────────────┐
     │          learning_modules          │
     ├───────────────────────────────────┤
     │ id (PK)                           │
     │ title                             │
     │ description                       │
     │ tps_level                         │
     │ file_name                         │
     │ created_at                        │
     └───────────────────────────────────┘

     ┌──────────────────▼──────────────────┐
     │             news                    │
     ├───────────────────────────────────┤
     │ id (PK)                           │
     │ title                             │
     │ category                          │
     │ content                           │
     │ target_type                       │
     │ target_users                      │
     │ created_at                        │
     │ updated_at                        │
     └───────────────────────────────────┘

     ┌──────────────────▼──────────────────┐
     │           batch_stats              │
     ├───────────────────────────────────┤
     │ id (PK)                           │
     │ batch_name                        │
     │ participant_count                 │
     │ kp3_count                        │
     │ kp4_count                         │
     │ kp3_percent                       │
     │ kp4_percent                       │
     └───────────────────────────────────┘
```

---

## 6. User Roles & Workflows

### Role Definitions

| Role | Description | Access Level |
|------|-------------|-------------|
| `tpsg` | TPSG Admin | Full system administration |
| `admin` | Super Admin | Full system administration |
| `omdd` | OMDD Assessor | Assessment & evaluation tools |
| `participant` | Employee | Training & activity submission |
| `management` | Management | Executive dashboards & analytics |
| `bod` | Board of Directors | Executive view (not implemented) |
| `division_head` | Division Head | Division-specific view (not implemented) |

### User Journey Flows

#### Participant Flow
```
1. Register (NIK + Password)
         ↓
2. Login → Role-based redirect
         ↓
3. Dashboard (TPS Roadmap + News Ticker)
         ↓
4. View Announcements & Training Schedules
         ↓
5. Upload Workshop Activity/Theme
         ↓
6. View OMDD Evaluation Results (Spider Chart)
         ↓
7. Update Profile Information
```

#### OMDD Assessor Flow
```
1. Login → OMDD Dashboard
         ↓
2. View Employee Statistics
         ↓
3. Access Participant List/Directory
         ↓
4. View Participant Details & Activity Logs
         ↓
5. Evaluate Activities (Score + Feedback)
         ↓
6. Assess/Upgrade Employee TPS Level
         ↓
7. Submit Workshop Evaluations (Spider Chart)
```

#### TPSG Admin Flow
```
1. Login → TPSG Command Center
         ↓
2. Import Employee Data (Excel)
         ↓
3. Manage Announcements (Broadcast)
         ↓
4. View/Manage Employee Records
         ↓
5. Manage Batch Statistics
         ↓
6. Bulk Delete/Reset Employee Data
```

#### Management Flow
```
1. Login → Executive Intelligence Center
         ↓
2. View Utilized KP 3 & 4 Analytics
         ↓
3. View TPS Advance & Jishuken Office Stats
         ↓
4. Click-through to Participant Details
         ↓
5. Export KPI Projection Charts (PDF)
```

---

## 7. CRUD Matrix

```
Legend: ✅ = Complete   🔶 = Partial   ❌ = Not Available

FEATURE                  │ CREATE │ READ │ UPDATE │ DELETE │ NOTES
────────────────────────┼────────┼──────┼────────┼────────┼─────────────────────
Employee Management      │  ✅    │  ✅  │  🔶    │  🔶    │ Bulk delete only
User/Auth                │  ✅    │  ✅  │  🔶    │  ❌    │ No user delete
Workshop Activity        │  ✅    │  ✅  │  ✅    │  ❌    │ No delete
Workshop Evaluation      │  ✅    │  ✅  │  ✅    │  ❌    │ No delete
News/Announcements        │  ✅    │  ✅  │  ❌    │  ✅    │ UPDATE missing
Learning Modules         │  ✅    │  ✅  │  ❌    │  ❌    │ Full CRUD missing
Training Schedules       │  ✅    │  ✅  │  ❌    │  ❌    │ Full CRUD missing
Batch Statistics         │  ✅    │  ✅  │  🔶    │  ❌    │ Partial manage
Employee Photo Upload    │  ✅    │  ✅  │  🔶    │  ❌    │ Via detail_emp
Employee Certificate      │  ✅    │  ✅  │  🔶    │  ❌    │ Via detail_emp
Profile Update           │  N/A   │  ✅  │  ✅    │  N/A   │ ✅ Complete
```

---

## 8. Gap Analysis & Issues

### Critical Issues (Fix Immediately)

| # | Issue | Location | Severity | Impact | Status |
|---|-------|----------|----------|--------|--------|
| 1 | No CSRF Protection | All POST forms | 🔴 HIGH | CSRF vulnerability | ✅ Fixed |
| 2 | SECRET_KEY hardcoded | `app/__init__.py`, `config.py` | 🔴 HIGH | Session hijacking risk | ✅ Fixed |
| 3 | `this_year = 2026` hardcoded | Multiple files | 🔴 HIGH | System breaks in 2027 | ✅ Fixed |
| 4 | No input validation | All route handlers | 🔴 HIGH | SQL Injection / XSS risk | ✅ Fixed (WTForms) |
| 5 | Default password `tmmin123` | `app.py`, `create_tables.py` | 🔴 HIGH | Security breach vector | ✅ Fixed |

### Medium Issues (Fix Within 1 Week)

| # | Issue | Location | Severity | Impact | Status |
|---|-------|----------|----------|--------|--------|
| 6 | No complete CRUD | News, Modules, Training | 🟡 MED | Incomplete features | ✅ Fixed |
| 7 | No Flask-Migrate | Manual `migrate.py` | 🟡 MED | Schema change risk | ✅ Fixed |
| 8 | No unit tests | No `tests/` folder | 🟡 MED | Refactoring risk | ✅ Added |
| 9 | `datetime.utcnow()` deprecated | Routes | 🟡 MED | Python 3.12+ warning | ✅ Fixed |
| 10 | Role `bod` & `division_head` unused | `models/user.py` | 🟡 MED | Dead code | ✅ Implemented |
| 11 | Template duplication high | Dashboard templates | 🟡 MED | Hard maintenance | ✅ Jinja2 macros added |
| 12 | PDF service separate deployment | `pdf_service.py` | 🟡 MED | Operational complexity | 🔶 Pending |

### Low Issues (Fix Within 1 Month)

| # | Issue | Location | Severity | Impact | Status |
|---|-------|----------|----------|--------|--------|
| 13 | No API versioning | Routes | 🟢 LOW | Mobile app future | 🔶 Pending |
| 14 | No audit trail | CRUD operations | 🟢 LOW | No change tracking | ✅ Fixed |
| 15 | No cache strategy | DB queries | 🟢 LOW | Performance degradation | 🔶 Pending |
| 16 | No rate limiting | Auth routes | 🟢 LOW | Brute force vulnerability | ✅ Fixed |
| 17 | No static file versioning | `static/` | 🟢 LOW | Cache busting missing | 🔶 Pending |
| 18 | No type hints | Python files | 🟢 LOW | Code quality | 🔶 Pending |
| 19 | No service layer | Routes | 🟢 LOW | Business logic mixed | ✅ Fixed |
| 20 | No repository pattern | Routes | 🟢 LOW | Query logic scattered | 🔶 Pending |

---

## 9. Implementation Roadmap

### Current Status by Phase

```
PHASE 1 ✅ (Complete)      → Core Auth & Multi-Role Login
PHASE 2 ✅ (Complete)       → Employee Management + Excel Import
PHASE 3 ✅ (Complete)       → Participant Portal & Roadmap Progress
PHASE 4 ✅ (Complete)       → OMDD Assessor & Evaluation
PHASE 5 ✅ (Complete)        → Management Dashboard & Analytics
PHASE 6 🔶 (Partial)         → PDF Export (separate FastAPI service, runs on port 8000)
PHASE 7 ❌ (Not Started)    → API Layer & Mobile Readiness
PHASE 8 ❌ (Not Started)     → Real-time Notification System
PHASE 9 ✅ (Complete)        → Audit Trail & Logging + Viewer UI
PHASE 10 ❌ (Not Started)    → Advanced Analytics & BI Integration
```

### 4-Week Implementation Plan

#### Week 1: Security & Stability
- [ ] Install Flask-WTF for CSRF Protection
- [ ] Move SECRET_KEY to `.env`
- [ ] Replace `datetime.utcnow()` → `datetime.now(timezone.utc)`
- [ ] Replace `this_year = 2026` → `date.today().year`
- [ ] Add basic input validation

#### Week 2: Complete CRUD Operations
- [ ] News Management: Add Update + Delete
- [ ] Learning Modules: Add Update + Delete
- [ ] Training Schedule: Full CRUD
- [ ] User Management: Add Delete user
- [ ] Consistent error messages

#### Week 3: Improve MVC Structure
- [ ] Service layer for business logic
- [ ] Repository pattern for data access
- [ ] Flask-Migrate integration
- [ ] Centralized error handlers
- [ ] Add type hints to all Python files

#### Week 4: UI/UX Improvements
- [ ] Jinja2 macros for reusable components
- [ ] Tailwind CSS integration
- [ ] Skeleton loading states
- [ ] Empty state UIs
- [ ] Confirmation dialogs for destructive actions
- [ ] Consistent form validation feedback

---

## 10. UI/UX Pattern Analysis

### Design System

| Element | Value |
|---------|-------|
| Theme | Dark Cyber / Glassmorphism |
| Primary Background | `#04070d`, `#0b1019` |
| Accent Colors | Cyan `#00d2ff`, Green `#39ff14`, Pink `#ff00a0` |
| Typography | Oswald (headings), Inter (body), Poppins (UI) |
| Icons | Font Awesome 6.4 |
| Charts | Chart.js 3.x |

### Current UI Patterns (What's Working)

```
✅ Dark cyber theme - modern and corporate feel
✅ Glassmorphism panels with blur effects
✅ Chart.js visualizations (radar, doughnut, bar, line)
✅ Role-based sidebar navigation
✅ Consistent base.html template
✅ Responsive design with flexbox/grid
✅ News ticker animation
✅ Modal overlays for edit forms
✅ Icon system consistent (Font Awesome)
```

### UI Patterns Needing Improvement

```
⚠️ HTML duplication high (no Jinja2 macros)
⚠️ No CSS framework (plain CSS) - consider Tailwind/Bootstrap
⚠️ No frontend build tool (Vite/ESBuild)
⚠️ Chart.js loaded on every page
⚠️ No loading states / skeleton screens
⚠️ No form error messages consistent
⚠️ No empty state UI (blank pages)
⚠️ No confirmation dialog for destructive actions
```

---

## 11. Security Analysis

### Current Security Measures

```
✅ Password hashing (werkzeug.security)
✅ Session-based authentication (Flask-Login)
✅ Role-based access control decorators
✅ Database credentials in .env
✅ CSRF Protection on all forms (Flask-WTF)
✅ Rate limiting on auth routes (Flask-Limiter)
✅ Audit logging for all CRUD operations
✅ Centralized error handlers (404, 403, 429, 500)
```

### Missing Security Measures

```
❌ No input sanitization (XSS risk) - TODO: add bleach/sanitize
❌ No SQL parameterization check - TODO: review queries
❌ No brute force protection - ✅ Rate limiting added
❌ Default passwords in code - ✅ Moved to .env
❌ No audit logging - ✅ Audit trail added
```

---

## 12. Recommended Improvements

### Immediate (This Week)

```python
# 1. Add to requirements.txt:
Flask-WTF>=1.2.0
python-dotenv>=1.0.0

# 2. Update .env:
SECRET_KEY=your-super-secret-key-here

# 3. Update config.py:
import os
from dotenv import load_dotenv
load_dotenv()
SECRET_KEY = os.getenv('SECRET_KEY')

# 4. Update app/__init__.py:
from flask_wtf.csrf import CSRFProtect
csrf = CSRFProtect()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    csrf.init_app(app)
    # ... rest of setup

# 5. Add to all forms:
<input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>

# 6. Replace datetime:
# Before: datetime.utcnow()
# After: datetime.now(timezone.utc)

# 7. Replace hardcoded year:
# Before: this_year = 2026
# After: from datetime import date; this_year = date.today().year
```

### Short-term (2 Weeks)

```
1. Add service layer structure:
   app/services/
   ├── __init__.py
   ├── auth_service.py
   ├── employee_service.py
   └── evaluation_service.py

2. Add repository layer:
   app/repositories/
   ├── __init__.py
   ├── employee_repo.py
   └── activity_repo.py

3. Complete CRUD for all entities:
   - News: Update + Delete
   - Modules: Update + Delete
   - Training: Full CRUD

4. Add Flask-Migrate:
   flask db init
   flask db migrate
   flask db upgrade
```

### Medium-term (1 Month)

```
1. Add unit tests:
   tests/
   ├── __init__.py
   ├── conftest.py
   ├── test_auth.py
   ├── test_employee.py
   └── test_routes.py

2. Add centralized error handling:
   @app.errorhandler(404)
   @app.errorhandler(500)
   @app.errorhandler(403)

3. Add rate limiting:
   from flask_limiter import Limiter
   limiter = Limiter(app, default_limits=["100 per day"])

4. Add audit logging:
   import logging
   audit_logger = logging.getLogger('audit')
```

### Long-term (Future Phases)

```
1. API Layer:
   - RESTful API with /api/v1/ prefix
   - JWT authentication for mobile
   - OpenAPI documentation

2. Real-time Features:
   - WebSocket for live updates
   - Push notifications
   - Activity stream

3. Advanced Analytics:
   - Trend analysis
   - Predictive KPI modeling
   - Export to BI tools

4. Audit Trail:
   - Track all CRUD operations
   - User action history
   - Change logs
```

---

## Revision History

| 2026-05-01 | 1.4.0 | Claude Code | Audit Trail Viewer UI (pagination, filtering, CSV export, cleanup), Audit menu in TPSG sidebar |
| 2026-05-01 | 1.5.0 | Claude Code | XSS sanitization (bleach), integrated in NewsService/TrainingService/EmployeeService |

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2026-05-01 | 1.0.0 | Claude Code | Initial documentation created |
| 2026-05-01 | 1.1.0 | Claude Code | Security + CRUD improvements |
| 2026-05-01 | 1.2.0 | Claude Code | Service layer, WTForms, unit tests |
| 2026-05-01 | 1.3.0 | Claude Code | Audit trail, rate limiting, Jinja2 macros |
| 2026-05-01 | 1.4.0 | Claude Code | Audit Trail Viewer UI with cleanup, CSV export |
| 2026-05-01 | 1.5.0 | Claude Code | XSS sanitization with bleach, input validation in services |

---

*Document generated as project history and reference for TPS-G Key Person Development System*
