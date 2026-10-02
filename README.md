# Reports Application

Employee Reports application.

This repository currently contains the application foundation, the database
layer, the REST API and the first functional React UI:

* **Backend** — Django + Django REST Framework, using PostgreSQL
* **Frontend** — React, built with Vite

The backend exposes CRUD APIs for `Employee`, `Project`, `MonthlyReport` and
`ReportItem`. The React frontend provides a monthly report form (create and
edit), a report list and a read-only detail view.

No RAG, no agents, no MCP, no Kubernetes, and no Docker are part of this step.
The API itself is unauthenticated. The "Generate Summary with AI" button asks an
LLM for a draft of the monthly summary, which the employee can then edit before
submitting the report. The "Manager Reports" page lets a manager load the
submitted reports for a selected month/year and generate a single collective
monthly team report from them.

## Data model

```text
MonthlyReport 1 ---- * ReportItem

Employee (standalone directory, not related to reports)
Project  (standalone directory, not related to reports)
```

| Model | Notes |
| --- | --- |
| `Employee` | standalone `name`, unique `email` record |
| `Project` | standalone `name`, `business_group` record |
| `MonthlyReport` | `employee_name`, `project_name`, `business_group` (free text), `month` (1–12), `year`, optional `summary` |
| `ReportItem` | `report`, `item_type` (TASK/ACHIEVEMENT/COURSE/HOLIDAY/IDEA), `content` |

A `MonthlyReport` is unique per
`employee_name + project_name + business_group + month + year`, enforced by a
database `UniqueConstraint`. `month` is additionally constrained to 1–12 by a
`CheckConstraint`, so invalid data is rejected even if it bypasses Python
validation.

## Project structure

```text
reports-genai/
├── backend/          # Django project (config) + reports app
├── frontend/         # React app (Vite)
├── README.md
└── .gitignore
```

## Local URLs

```text
Frontend:  http://localhost:5173
Backend:   http://localhost:8000
Health API: http://localhost:8000/api/health/
Django admin: http://localhost:8000/admin/
```

## Prerequisites

* Python 3.12+
* Node.js 20+
* PostgreSQL 14+ running locally

## Backend

### 1. Create a virtual environment

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure the environment

```bash
cp .env.example .env
```

Then edit `.env` to match your local database. The defaults expect a database
named `reports_db` owned by the user `reports_user`:

```text
POSTGRES_DB=reports_db
POSTGRES_USER=reports_user
POSTGRES_PASSWORD=your-password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

If you have not created the database yet, use the `psql` prompt:

```bash
psql -U postgres
```

```sql
CREATE ROLE reports_user WITH LOGIN PASSWORD 'your-password' CREATEDB;
CREATE DATABASE reports_db OWNER reports_user;
```

`CREATEDB` is required because the Django test runner creates a temporary
database when running tests.

### 4. Run migrations

```bash
python manage.py migrate
```

### 5. Start Django

```bash
python manage.py runserver
```

The API is then available at http://localhost:8000.

### 6. Inspect data with the Django admin

The admin site is the only place the models are currently exposed, since no REST
API exists for them yet. Create a login user once:

```bash
python manage.py createsuperuser
```

Then open http://localhost:8000/admin/ to browse employees, projects, monthly
reports and report items.

### Tests

```bash
python manage.py test
```

## Frontend

### 1. Install dependencies

```bash
cd frontend
npm install
```

### 2. Configure the environment

```bash
cp .env.example .env
```

```text
VITE_API_BASE_URL=http://localhost:8000
```

### 3. Start Vite

```bash
npm run dev
```

The app is then available at http://localhost:5173. It offers three views:

* **Create Report** — enter a report with free-text Employee Name, Project Name
  and Business Group, a month/year, tasks/achievements/courses/holidays/ideas,
  an optional manual summary, and save.
* **My Reports** — table of existing reports with View, Edit and Delete actions.
* **Manager Reports** — load the reports submitted for a selected month/year and
  generate a collective monthly team report with the LLM.
* **View** — a read-only rendering of a report with its items grouped by type.

The "Generate Summary with AI" button drafts the summary from the current,
unsaved form data. Generation only produces a draft; nothing is stored until the
employee clicks **Save Report**. If a summary already exists the browser asks for
confirmation before replacing it.

## Manager monthly team report

The **Manager Reports** view is a separate page for viewing the team's submitted
reports and generating a collective monthly report:

1. pick a Month and Year, then click **Load Reports** — the submitted employee
   reports for that month/year are fetched from PostgreSQL and shown in a table
   (Employee, Project, Business Group; each row can be expanded to inspect the
   underlying report details),
2. click **Generate Monthly Team Report** — the backend builds a prompt from
   those stored reports only (data comes from the database, never invented) and
   asks the LLM for a professional team report covering the whole month,
3. the generated team report is displayed on the page.

The two steps are separate: generation uses only the reports already loaded from
the database for the selected month/year. The manager report is generation-only
— it is never auto-saved and changes no employee data. If no reports exist for
the selected month/year the page says so and the LLM is not called.

## Manager quarterly team report

The **Manager Reports** view also has a **Quarterly** tab. It works the same
way as the monthly flow but aggregates exactly three months of a selected year:

```text
Q1 → January, February, March    Q2 → April, May, June
Q3 → July, August, September     Q4 → October, November, December
```

1. pick a Year and Quarter, then click **Load Reports** — the submitted
   employee reports for that quarter's three months are fetched from PostgreSQL
   and shown in a table (Month, Employee, Project, Business Group, Summary; each
   row can be expanded to inspect the underlying report details),
2. click **Generate Quarterly Team Report** — the backend builds a quarterly
   prompt from those stored reports only (data comes from the database, never
   invented) and asks the LLM for a professional quarterly management report,
3. the generated quarterly report is displayed on the page.

Generation-only, like the monthly flow: nothing is auto-saved, only reports of
the selected quarter/year are used, and the LLM is not called when the quarter
has no reports.

## AI summary generation

The "Generate Summary with AI" button in the Create Report form:

1. sends the current (unsaved) form fields and item lists to
   `POST /api/reports/generate-summary/`,
2. the backend builds a prompt from that data only (no invented facts) and asks
   the LLM for a concise professional summary,
3. the generated text is placed in the Summary textarea, where the employee can
   edit it,
4. clicking **Save Report** persists the final summary and all items through the
   normal report endpoints.

Generation never writes to the database, and a failure keeps every field as the
user entered them.

### Configuring the LLM

The backend reads these environment variables (see `backend/.env.example`):

| Variable | Default | Description |
| --- | --- | --- |
| `LLM_API_KEY` | (empty) | API key for the LLM provider |
| `LLM_MODEL` | (empty) | Model name sent to the provider |
| `LLM_BASE_URL` | `https://api.openai.com/v1` | Base URL of an OpenAI-compatible chat completions API |
| `LLM_TIMEOUT` | `60` | Request timeout in seconds |

Set `LLM_BASE_URL` to any OpenAI-compatible endpoint (for example an Ollama
`/v1` server) to run locally without an API key. Never commit a real API key.

### Tests

```bash
npm test
```

### Build

```bash
npm run build
```

## API

All endpoints live under `/api/` and are unauthenticated. Responses are JSON.
There is no interactive API browser configured.

### Endpoints

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/health/` | Liveness check |
| `GET` | `/api/` | List of registered endpoints |
| `GET` | `/api/employees/` | List employees |
| `POST` | `/api/employees/` | Create an employee |
| `GET` | `/api/employees/<id>/` | Retrieve an employee |
| `PUT` `PATCH` | `/api/employees/<id>/` | Replace / partially update an employee |
| `DELETE` | `/api/employees/<id>/` | Delete an employee |
| `GET` | `/api/projects/` | List projects |
| `POST` | `/api/projects/` | Create a project |
| `GET` | `/api/projects/<id>/` | Retrieve a project |
| `PUT` `PATCH` | `/api/projects/<id>/` | Replace / partially update a project |
| `DELETE` | `/api/projects/<id>/` | Delete a project |
| `GET` | `/api/reports/` | List monthly reports (filterable) |
| `POST` | `/api/reports/` | Create a monthly report |
| `GET` | `/api/reports/<id>/` | Retrieve a report with items grouped by type |
| `PUT` `PATCH` | `/api/reports/<id>/` | Replace / partially update a report |
| `DELETE` | `/api/reports/<id>/` | Delete a report (and its items) |
| `GET` | `/api/reports/<id>/items/` | List the items of one report |
| `POST` | `/api/reports/<id>/items/` | Add an item to a report |
| `POST` | `/api/reports/generate-summary/` | Generate an AI summary draft (no persistence) |
| `POST` | `/api/manager-reports/monthly/generate/` | Generate an AI monthly team report (generation-only) |
| `POST` | `/api/manager-reports/quarterly/generate/` | Generate an AI quarterly team report (generation-only) |
| `PATCH` | `/api/report-items/<id>/` | Update an item |
| `DELETE` | `/api/report-items/<id>/` | Delete an item |

`PUT` requires every writable field; use `PATCH` to change a single field.

### Filtering reports

`GET /api/reports/` accepts `employee_name`, `project_name`, `business_group`,
`month` and `year` as query parameters, and they can be combined:

```text
/api/reports/?employee_name=Richa
/api/reports/?project_name=AI Automation
/api/reports/?business_group=Data Center
/api/reports/?month=9&year=2026
/api/reports/?employee_name=Richa&month=9&year=2026
```

### Example requests

```bash
# Create an employee
curl -X POST http://localhost:8000/api/employees/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Ada Lovelace", "email": "ada@example.com"}'

# Create a project
curl -X POST http://localhost:8000/api/projects/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Apollo", "business_group": "Engineering"}'

# Create a monthly report
curl -X POST http://localhost:8000/api/reports/ \
  -H "Content-Type: application/json" \
  -d '{"employee_name": "Richa Verma", "project_name": "AI Automation", "business_group": "Data Center", "month": 9, "year": 2026, "summary": "September summary"}'

# Add an item to that report
curl -X POST http://localhost:8000/api/reports/1/items/ \
  -H "Content-Type: application/json" \
  -d '{"item_type": "TASK", "content": "Completed API implementation"}'
```

`item_type` must be one of `TASK`, `ACHIEVEMENT`, `COURSE`, `HOLIDAY`, `IDEA`.

### Generating a summary

```bash
curl -X POST http://localhost:8000/api/reports/generate-summary/ \
  -H "Content-Type: application/json" \
  -d '{
    "employee_name": "Richa Verma",
    "project_name": "AI Automation",
    "business_group": "Data Center",
    "month": 9,
    "year": 2026,
    "tasks": ["Completed API implementation", "Shipped the auth module"],
    "achievements": [],
    "courses": ["Advanced PostgreSQL"],
    "planned_holidays": [],
    "ideas": ["Automate CI checks"]
  }'
```

Response (a draft the employee can edit):

```json
{
  "summary": "Completed the core API work and shipped the auth module, while deepening PostgreSQL skills and proposing CI automation."
}
```

The endpoint only returns a draft and never creates or changes any records. The
final summary is stored later via `POST /api/reports/`.

### Generating a team report

`POST /api/manager-reports/monthly/generate/` takes a `month` (1–12) and `year`
(≥ 1970), loads the submitted employee reports for that month/year from
PostgreSQL and asks the LLM for a collective team report:

```bash
curl -X POST http://localhost:8000/api/manager-reports/monthly/generate/ \
  -H "Content-Type: application/json" \
  -d '{"month": 9, "year": 2026}'
```

Response (a report the manager can read; it is never stored):

```json
{
  "month": 9,
  "year": 2026,
  "reports_count": 2,
  "report": "During September 2026, the team shipped the AI Platform auth work..."
}
```

The prompt is built only from the stored reports of the selected month/year —
the LLM is never asked to query the database or invent data. If no reports exist
for the month/year, the endpoint returns `reports_count: 0` with an empty
`report` and does not call the LLM. Invalid `month`/`year` values are rejected
with `400`.

### Generating a quarterly team report

`POST /api/manager-reports/quarterly/generate/` takes a `quarter` (1–4) and
`year` (≥ 1970), maps the quarter to its three months, loads the submitted
employee reports for those months from PostgreSQL and asks the LLM for a
collective quarterly team report:

```bash
curl -X POST http://localhost:8000/api/manager-reports/quarterly/generate/ \
  -H "Content-Type: application/json" \
  -d '{"quarter": 3, "year": 2026}'
```

Response (a report the manager can read; it is never stored):

```json
{
  "year": 2026,
  "quarter": 3,
  "months": [7, 8, 9],
  "report_count": 2,
  "report": "During Q3 2026, the team shipped the AI Platform auth work..."
}
```

The prompt is built only from the stored reports in the selected quarter/year
and reuses the same `LLMService`. Quarter-to-month mapping is `1→[1,2,3]`,
`2→[4,5,6]`, `3→[7,8,9]`, `4→[10,11,12]`. If no reports exist for the quarter,
the endpoint returns `{"detail": "No employee reports found for Q3 2026."}` and
does not call the LLM. Invalid `quarter`/`year` values are rejected with `400`.

### Report detail response

`GET /api/reports/<id>/` returns the report with its items already grouped by
type, so the frontend does not have to sort them:

```json
{
  "id": 1,
  "employee_name": "Richa Verma",
  "project_name": "AI Automation",
  "business_group": "Data Center",
  "month": 9,
  "year": 2026,
  "summary": "September summary",
  "items": {
    "TASK": [{ "id": 1, "item_type": "TASK", "content": "Completed API implementation" }],
    "ACHIEVEMENT": [],
    "COURSE": [],
    "HOLIDAY": [],
    "IDEA": []
  },
  "created_at": "2026-09-28T18:43:07.479457Z",
  "updated_at": "2026-09-28T18:43:07.479481Z"
}
```

Employee name, project name and business group are free-text values entered by
the user; reports no longer link to database `Employee` or `Project` records.

List and create/update responses use the same fields but return `items` as a
flat list. The list response also includes `employee_name`, `project_name` and
`business_group` so the frontend can render tables without extra requests.

### Errors

| Status | When |
| --- | --- |
| `200` `201` `204` | Success (`204` for delete) |
| `400` | Validation error |
| `404` | Object does not exist |
| `405` | Method not allowed on that endpoint |
| `502` | The LLM call failed or returned nothing usable |
| `503` | LLM generation is not configured (missing `LLM_MODEL`/`LLM_API_KEY`) |

Validation errors identify the offending field:

```json
{
  "month": ["Ensure this value is less than or equal to 12."]
}
```

Submitting the same `employee_name + project_name + business_group + month + year`
twice returns:

```json
{
  "non_field_errors": ["The fields employee_name, project_name, business_group, month, year must make a unique set."]
}
```
