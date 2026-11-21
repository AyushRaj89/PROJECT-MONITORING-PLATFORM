# Integrated Project Monitoring Platform

One Django project (created with `django-admin startproject monitoring_platform`) with four apps
created inside it using `python manage.py startapp`. Templates live inside each app, as in class.

The **Python code is complete**. The **HTML/CSS/JS** is yours: every template file already exists and
starts with a comment listing the context variables and URL names it can use.
# ProjectPulse: Integrated Project Monitoring Platform

A web-based project monitoring platform built with **Django** for the course *INT253: Web Development in Python using Django*. Teams can plan projects, assign tasks, track milestones, report issues, post progress updates and see how every project is doing on one dashboard.

## Features

- **Dashboard** with active projects, overdue tasks, open issues, a task-status bar, a projects-by-status donut chart, upcoming milestones and latest updates
- **Projects** in card or table view, with search and filters, health status (on track, at risk, off track), budget tracking and a progress bar
- **Tasks** with priority, assignee, due date, comments and filters, plus a **drag-and-drop board** on "My tasks"
- **Milestones, progress updates and issues** for each project
- **Yearly report** of tasks completed per month, and **CSV export** of a project's tasks
- **Role-based access**: Admin, Project Manager, Team Member and Client Viewer
- Custom error pages (400, 403, 404, 500), flash messages, and a responsive layout that works on phones

## Tech stack

- Python 3 and Django 5
- SQLite by default (PostgreSQL supported through environment variables)
- Plain HTML templates, CSS and JavaScript, with no frontend framework

## Project structure

```
monitoring_platform/
├── manage.py
├── requirements.txt
├── monitoring_platform/   settings, root urls, error handlers, context processor
├── accounts/              register, login/logout, profile, roles, user management
├── projects/              projects, team members, milestones
├── tasks/                 tasks, comments, filters, "my tasks" board
└── monitoring/            dashboard, progress updates, issues, reports
    ├── templates/base.html    shared layout (sidebar, top bar, messages)
    └── static/                css/style.css, js/main.js
```

Each app keeps its own templates in `<app>/templates/<app>/`.

## Getting started

```bash
git clone <your-repo-url>
cd monitoring_platform

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python manage.py migrate
python manage.py setup_roles       # creates the role groups and permissions
python manage.py runserver
```

Open http://127.0.0.1:8000/

Run the tests with `python manage.py test`.

## Roles

| Role | Can do |
|---|---|
| Admin | Everything, including changing user roles at `/accounts/users/` |
| Project Manager | Create projects and manage their own (members, milestones, tasks) |
| Team Member | Work in projects they belong to: tasks, comments, updates, issues |
| Client Viewer | Read-only access to projects they belong to |

New sign-ups become Team Members. A project is visible only to its manager, its members and admins.

## Configuration

Settings are read from environment variables. The defaults suit local development.

| Variable | Purpose | Default |
|---|---|---|
| `DJANGO_SECRET_KEY` | Django secret key. Set your own value when deploying. | development placeholder |
| `DJANGO_DEBUG` | Set to `False` in production | `True` |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated host names | `localhost,127.0.0.1` |
| `DB_ENGINE` | `sqlite` or `postgres` | `sqlite` |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | PostgreSQL connection (needs `psycopg[binary]`) | |

Never commit a `.env` file or real credentials.

## Django concepts covered

| Unit | Where to look |
|---|---|
| I: project, apps, `manage.py` | project layout, `settings.py`, `INSTALLED_APPS` |
| II: views, URL parameters, regex URLs, HTTP methods, error handling | each `views.py` and `urls.py`; `re_path` in `monitoring/urls.py`; `monitoring_platform/views.py` |
| III: templates, debugging, testing | `<app>/templates`, `base.html`, `tests.py` in each app |
| IV: forms, GET/POST, CSRF, validation, POST-redirect-GET | each `forms.py`, `clean_<field>` methods |
| V: models, migrations, ORM, admin, groups and permissions | each `models.py` and `admin.py`, `setup_roles` command |
| VI: cookies, sessions, authentication | `recent_projects` (session), `view_mode` (cookie), `@login_required`, `@permission_required` |

## Author

Ayush, INT253, Web Development in Python using Django.
```
monitoring_platform/                 <- project root (open this folder in VS Code)
├── manage.py
├── requirements.txt
├── monitoring_platform/             project package: settings.py, urls.py, wsgi.py, asgi.py,
│                                    views.py (error pages), context_processors.py
├── accounts/                        register, login/logout, profile, roles, user management
│   └── templates/accounts/          login, register, profile, password_change(+done), user_list
├── projects/                        projects, team members, milestones
│   └── templates/projects/          project_list, project_detail, project_form, ...
├── tasks/                           tasks, comments, filters, "my tasks"
│   └── templates/tasks/             task_list, task_detail, task_form, my_tasks, ...
└── monitoring/                      dashboard, progress updates, issues, reports, CSV, JSON
    ├── templates/base.html          shared layout - every page extends it
    ├── templates/errors/            400, 403, 404, 500
    ├── templates/monitoring/        dashboard, issue_list, issue_form, update_form, year_report
    └── static/                      css/style.css, js/main.js, images/
```

Each app has the usual files: `models.py`, `views.py`, `urls.py`, `forms.py`, `admin.py`, `tests.py`.
The folder must be spelled `templates` (not "templetes") or Django will not find your pages.

## Run it

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py setup_roles       # creates the 3 role groups + permissions
python manage.py seed_demo         # optional demo data
python manage.py runserver         # http://127.0.0.1:8000/
python manage.py test              # 52 tests
```

Demo logins (after `seed_demo`): `admin / admin12345`, and `manager1, manager2, member1, member2, member3, viewer1` with password `demo12345`.
Django admin: http://127.0.0.1:8000/admin/ (log in as `admin`).

## Frontend

Pages live in each app's `templates/` folder and extend `monitoring/templates/base.html` (sidebar, top bar, flash toasts, icon sprite). Styling is one file, `monitoring/static/css/style.css`; behaviour is `monitoring/static/js/main.js` (no libraries): dashboard donut and bar charts, drag-and-drop task board on My tasks, mobile menu. The brand name "ProjectPulse" is a placeholder. Change it in `base.html`. The Manrope font loads from Google Fonts and falls back to the system font offline.


| Role | Can do |
|---|---|
| Admin (superuser) | everything; changes roles at `/accounts/users/` |
| Project Manager | create projects; manage their own projects (members, milestones, tasks) |
| Team Member | work in projects they belong to: tasks, comments, updates, issues |
| Client Viewer | read-only in projects they belong to |

New sign-ups become Team Members. A project is visible only to its manager, its members and admins (others get 404).

## Pages and URLs

| URL | name | Template |
|---|---|---|
| `/` | `monitoring:dashboard` | monitoring/dashboard.html |
| `/accounts/login/` `/logout/` `/register/` `/profile/` | `accounts:*` | accounts/*.html |
| `/accounts/password-change/` (+ `done/`) | `accounts:password_change` | accounts/password_change*.html |
| `/accounts/users/` (admin) | `accounts:user_list` | accounts/user_list.html |
| `/projects/` | `projects:list` | projects/project_list.html |
| `/projects/new/` `<id>/` `<id>/edit/` `<id>/delete/` | `projects:create/detail/update/delete` | projects/project_*.html |
| `/projects/<id>/members/add/` | `projects:member_add` | projects/member_form.html |
| `/projects/<id>/milestones/new/` | `projects:milestone_create` | projects/milestone_form.html |
| `/tasks/` `/tasks/mine/` `/tasks/<id>/` | `tasks:list/mine/detail` | tasks/*.html |
| `/tasks/new/<project_id>/` `<id>/edit/` `<id>/delete/` | `tasks:create/update/delete` | tasks/task_form.html ... |
| `/projects/<id>/updates/new/` | `monitoring:update_create` | monitoring/update_form.html |
| `/issues/` `/projects/<id>/issues/new/` | `monitoring:issue_list/issue_create` | monitoring/issue_*.html |
| `/reports/2026/` | `monitoring:year_report` | monitoring/year_report.html |
| `/projects/<id>/tasks.csv` | `monitoring:tasks_csv` | (file download) |
| `/api/dashboard/` `/api/projects/<id>/` | `monitoring:dashboard_data / project_data` | (JSON for charts) |

## Notes for writing the templates

- All POST forms need the csrf token tag. Logout must be a small POST form (Django 5), not a link.
- `base.html` is the layout; every page extends it. Show `messages` there once (success / error flashes).
- Every template gets `user`, `user_role`, `is_manager`, `is_viewer` and `messages` automatically.
- Add/edit pages receive a Django `form`; render fields and `field.errors` yourself or with `form.as_p`.
- Error pages `errors/400, 403, 404, 500.html` are used only when `DJANGO_DEBUG=False`.

## Database

SQLite by default (`db.sqlite3` is created next to `manage.py` by `migrate`). For PostgreSQL set `DB_ENGINE=postgres`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` and install `psycopg[binary]`.
