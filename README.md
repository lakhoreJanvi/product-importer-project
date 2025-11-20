# Product Import App

A FastAPI + React application for managing products and webhooks with Celery background tasks.

## Features

- **Products**: Create, update, delete, list products.
- **Webhooks**: Add, edit, delete, and test webhooks.
- **Async Tasks**: CSV import and webhook triggers using Celery and Redis.
- **Frontend**: React-based UI for managing products and webhooks.
- **Database**: SQLAlchemy with Alembic migrations.

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy, Alembic, Celery, Redis
- **Frontend**: React, Vanilla JS
- **Database**: PostgreSQL / SQLite (depending on configuration)
- **Task Queue**: Celery + Redis
- **Deployment**: Docker + Docker Compose

## Setup

1. Clone the repository:

git clone https://github.com/username/product-import-app.git
cd product-import-app

2. Create .env file with necessary environment variables (DB URL, Redis URL, etc.)

3. Build and run with Docker:

docker-compose up --build

4. Run Alembic migrations:

docker-compose exec web alembic upgrade head

5. Open frontend at http://localhost:8000

## Usage

- Manage products and webhooks via the UI.
- Upload CSVs for bulk product import.
- Test webhooks directly from the UI.
