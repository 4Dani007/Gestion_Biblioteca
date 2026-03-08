# Sistema de Gestión de Biblioteca

Backend minimalista en Flask diseñado como base para prácticas de QA, incluyendo pruebas unitarias, de integración y de sistema. El proyecto incorpora defectos intencionales para ser detectados mediante testing.

---

## Stack tecnológico

| Capa          | Tecnología        |
|---------------|-------------------|
| Lenguaje      | Python 3.11       |
| Framework     | Flask 3.x         |
| Base de datos | SQLite            |
| ORM           | SQLAlchemy 2.x    |
| Testing       | Pytest            |
| Documentación | Swagger UI (Flasgger) |

---

## Estructura del proyecto

```
library-system/
├── app/
│   ├── __init__.py          # Application factory (create_app) + Swagger
│   ├── config.py            # Configuraciones por entorno
│   ├── database.py          # Instancia de SQLAlchemy
│   ├── models.py            # Modelos ORM: User, Book, Loan, Reservation
│   ├── seeds.py             # Datos de prueba iniciales
│   ├── utils.py             # Helpers: validaciones y respuestas estándar
│   └── routes/
│       ├── auth_routes.py         # POST /api/auth/register|login
│       ├── book_routes.py         # CRUD /api/books/
│       ├── loan_routes.py         # /api/loans/borrow|return
│       ├── reservation_routes.py  # /api/reservations/
│       └── report_routes.py       # GET /api/reports/...
├── tests/
│   ├── conftest.py          # Fixtures de Pytest (app, client, db_session)
│   ├── test_unit.py         # Pruebas unitarias
│   ├── test_integration.py  # Pruebas de integración
│   ├── test_system.py       # Pruebas de sistema (flujo completo)
│   ├── test_auth.py         # Pruebas de autenticación
│   ├── test_books.py        # Pruebas de libros
│   ├── test_loans.py        # Pruebas de préstamos
│   ├── test_reservations.py # Pruebas de reservas
│   └── test_reports.py      # Pruebas de reportes
├── requirements.txt
├── run.py                   # Punto de entrada: python run.py
└── README.md
```

---

## Instalación y ejecución

### 1. Crear y activar entorno virtual

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Iniciar el servidor de desarrollo

```bash
python run.py
```

La API estará disponible en `http://localhost:5000`.

La documentación Swagger estará en `http://localhost:5000/apidocs/`.

---

## Endpoints disponibles

| Método | URL                        | Descripción                        |
|--------|----------------------------|------------------------------------|
| GET    | /                          | Índice de endpoints disponibles    |
| POST   | /api/auth/register         | Registrar nuevo usuario            |
| POST   | /api/auth/login            | Autenticar usuario                 |
| GET    | /api/books/                | Listar todos los libros            |
| GET    | /api/books/search?q=       | Buscar libros por título o autor   |
| POST   | /api/books/                | Agregar un libro                   |
| PUT    | /api/books/\<id\>          | Actualizar un libro                |
| POST   | /api/loans/borrow          | Realizar un préstamo               |
| POST   | /api/loans/return          | Devolver un libro prestado         |
| GET    | /api/reservations/         | Listar reservas                    |
| POST   | /api/reservations/         | Crear una reserva                  |
| GET    | /api/reports/loans         | Historial de préstamos             |
| GET    | /api/reports/popular-books | Libros más prestados               |

---

## Ejecutar pruebas

```bash
pytest
```

Con salida detallada:

```bash
pytest -v
```

Ejecutar solo los archivos nuevos de QA:

```bash
pytest tests/test_unit.py tests/test_integration.py tests/test_system.py -v
```

Ejecutar un grupo específico:

```bash
pytest tests/test_integration.py::TestReturnUpdatesLoanStatus -v
```

---

## Resultado esperado de las pruebas

El proyecto contiene **defectos intencionales** para ser detectados mediante testing. Al ejecutar la suite completa se espera:

```
60 passed, 9 failed
```

Los tests que fallan exponen defectos reales del sistema. Consulta los Issues del repositorio para ver el detalle de cada uno.

---

## Defectos conocidos

| Issue | Descripción | Archivo afectado |
|-------|-------------|------------------|
| #1 | Se permiten reservas duplicadas para el mismo usuario y libro | `reservation_routes.py` |
| #2 | Se puede prestar un libro con 0 copias disponibles | `loan_routes.py` |
| #3 | Devolver un libro no restaura `available_copies` | `loan_routes.py` |
| #4 | La búsqueda de libros es sensible a mayúsculas | `book_routes.py` |
| #5 | Se permiten registros con e-mail duplicado | `auth_routes.py`, `models.py` |

---

## Configuración por entorno

| Entorno       | Base de datos         | Debug |
|---------------|-----------------------|-------|
| `development` | `library_dev.db`      | Sí    |
| `testing`     | En memoria (`:memory:`) | Sí  |
| `production`  | `library.db`          | No    |

```bash
# Ejemplo: ejecutar en modo producción
FLASK_ENV=production python run.py
```

---

## Modelos de base de datos

```
User                    Book
──────────────          ──────────────────
id                      id
name                    title
email                   author
password (hash)         isbn
role                    total_copies
created_at              available_copies

Loan                    Reservation
──────────────────      ──────────────────
id                      id
user_id (FK → User)     user_id (FK → User)
book_id (FK → Book)     book_id (FK → Book)
loan_date               reservation_date
return_date             status
status
```

---

## Estrategia de pruebas

### Pruebas unitarias (`test_unit.py`)
Verifican operaciones individuales a través del cliente HTTP: crear usuario, agregar libro, buscar libro, reservar libro.

### Pruebas de integración (`test_integration.py`)
Verifican que las operaciones producen los efectos correctos en la base de datos: decrementar copias al prestar, restaurar copias al devolver, prevenir reservas duplicadas.

### Pruebas de sistema (`test_system.py`)
Simulan el flujo completo de un usuario: registro → búsqueda → reserva → préstamo → devolución.
