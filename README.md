# HPN Gym Manager

A professional-grade Flask application scaffold for managing gym operations, following application factory and blueprint best practices.

## Project Structure

```
HPN Gym Manager/
├── .env.example
├── app
│   ├── __init__.py
│   ├── blueprints
│   │   ├── __init__.py
│   │   ├── admin
│   │   │   └── __init__.py
│   │   ├── auth
│   │   │   └── __init__.py
│   │   ├── cashier
│   │   │   └── __init__.py
│   │   ├── reception
│   │   │   └── __init__.py
│   │   └── trainer
│   │       └── __init__.py
│   ├── extensions.py
│   ├── models
│   │   └── __init__.py
│   ├── static
│   │   ├── css
│   │   │   └── .gitkeep
│   │   ├── images
│   │   │   └── .gitkeep
│   │   └── js
│   │       └── .gitkeep
│   └── templates
│       └── base.html
├── config.py
├── migrations
│   └── .gitkeep
├── requirements.txt
├── tests
│   └── .gitkeep
└── wsgi.py
```

## Getting Started

1. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Copy `.env.example` to `.env` and update your database and mail credentials.
3. Run the development server:
   ```bash
   flask --app wsgi run --debug
   ```

## Notes

* The project follows the application factory pattern with modular blueprints for `auth`, `reception`, `trainer`, `cashier`, and `admin` domains.
* No business logic has been implemented yet; this scaffold focuses on structure and dependencies only.
