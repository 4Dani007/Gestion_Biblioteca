# Library Management System

A minimal Flask backend designed as a foundation for QA testing practices,
including unit tests, integration tests, and system tests.

---

## Technology Stack

| Layer       | Technology          |
|-------------|---------------------|
| Language    | Python 3.11         |
| Framework   | Flask 3.x           |
| Database    | SQLite              |
| ORM         | SQLAlchemy 2.x      |
| Test runner | Pytest              |

---

## Project Structure

```
library-system/
├── app/
│   ├── __init__.py          # Application factory (create_app)
│   ├── config.py            # Environment-specific configuration classes
│   ├── database.py          # SQLAlchemy db instance
│   ├── models.py            # ORM models: User, Book, Loan, Reservation
│   └── routes/
│       ├── auth_routes.py         # POST /api/auth/register|login|logout
│       ├── book_routes.py         # CRUD /api/books/
│       ├── loan_routes.py         # /api/loans/ + return
│       ├── reservation_routes.py  # /api/reservations/ + cancel/fulfill
│       └── report_routes.py       # GET /api/reports/...
├── tests/
│   ├── conftest.py          # Pytest fixtures (app, client, db_session)
│   ├── test_auth.py         # Auth endpoint tests
│   ├── test_books.py        # Book endpoint tests
│   ├── test_loans.py        # Loan endpoint tests
│   └── test_reservations.py # Reservation endpoint tests
├── requirements.txt
├── run.py                   # Entry point: python run.py
└── README.md
```

---

## Getting Started

### 1. Create and activate a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the development server

```bash
python run.py
```

The API will be available at `http://localhost:5000`.

---

## API Endpoints

| Method | URL                              | Description                    |
|--------|----------------------------------|--------------------------------|
| POST   | /api/auth/register               | Register a new user            |
| POST   | /api/auth/login                  | Authenticate and get a token   |
| POST   | /api/auth/logout                 | Invalidate current session     |
| GET    | /api/books/                      | List all books                 |
| POST   | /api/books/                      | Add a new book                 |
| GET    | /api/books/\<id\>                | Get a specific book            |
| PUT    | /api/books/\<id\>                | Update a book                  |
| DELETE | /api/books/\<id\>                | Delete a book                  |
| GET    | /api/loans/                      | List loans                     |
| POST   | /api/loans/                      | Borrow a book                  |
| GET    | /api/loans/\<id\>                | Get a specific loan            |
| PATCH  | /api/loans/\<id\>/return         | Return a borrowed book         |
| GET    | /api/reservations/               | List reservations              |
| POST   | /api/reservations/               | Place a reservation            |
| GET    | /api/reservations/\<id\>         | Get a specific reservation     |
| PATCH  | /api/reservations/\<id\>/cancel  | Cancel a reservation           |
| PATCH  | /api/reservations/\<id\>/fulfill | Fulfill a reservation          |
| GET    | /api/reports/overdue-loans       | Overdue loans report           |
| GET    | /api/reports/popular-books       | Most borrowed books report     |
| GET    | /api/reports/active-users        | Most active users report       |
| GET    | /api/reports/availability        | Book availability summary      |

> All endpoints currently return `501 Not Implemented` — business logic will
> be added incrementally once tests are defined.

---

## Running Tests

```bash
pytest
```

Run with verbose output:

```bash
pytest -v
```

Run a specific test file:

```bash
pytest tests/test_books.py -v
```

Run only tests that are not skipped:

```bash
pytest -v -k "not skip"
```

---

## Configuration

Three environments are available, controlled by the `FLASK_ENV` variable:

| Environment   | Database            | Debug |
|---------------|---------------------|-------|
| `development` | `library_dev.db`    | On    |
| `testing`     | In-memory (`:memory:`) | On |
| `production`  | `library.db`        | Off   |

```bash
# Example: run in production mode
FLASK_ENV=production python run.py
```

---

## Testing Strategy

### Unit Tests
Test pure functions (password hashing, validation helpers) in isolation,
without a database or HTTP server.

### Integration Tests
Use the Flask test client and an in-memory SQLite database to test
request/response contracts and ORM interactions end-to-end.

### System Tests
Will cover full user workflows (e.g., register → login → borrow book →
return book) against a running server instance.

---

## Database Models

```
User          Book
────────      ────────
id            id
username      title
email         author
password      isbn
role          total_copies
created_at    available_copies
              created_at

Loan                    Reservation
────────────────        ────────────────
id                      id
user_id (FK → User)     user_id (FK → User)
book_id (FK → Book)     book_id (FK → Book)
loaned_at               reserved_at
due_date                expires_at
returned_at             status
status
```
