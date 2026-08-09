# DadsBooks - Book Inventory System

A full-stack Django application for maintaining and browsing a personal book
inventory. Administrators can register books by ISBN, manage stock, and update
availability, while visitors can search and browse the public catalogue.

## Live demo

[Open Graaskjegg Boker](https://tystrodev.pythonanywhere.com/shop/)

The inventory and ISBN-management workflows require an administrator account
and are intentionally not exposed in the public demo.

## Features

- Public, paginated book catalogue
- Search by title and author
- Detailed book pages with ISBN and availability
- ISBNDB integration for automatic book metadata
- Google Books rating lookup
- Duplicate ISBN detection and quantity updates
- Add, edit, remove, and update inventory
- Stock status, pricing, and availability management
- Protected administrator workflows
- Mobile-friendly ISBN registration and lookup

## Technology

- Python and Django
- Django ORM and SQLite
- ISBNDB and Google Books API integrations
- HTML, CSS, and JavaScript
- PythonAnywhere

## Data workflow

```text
ISBN input
    -> existing-book lookup in SQLite
    -> ISBNDB metadata request when the book is new
    -> administrator confirmation
    -> validation through a Django ModelForm
    -> persistence through Django ORM
    -> public catalogue and inventory views
```

## Local setup

1. Clone the repository:

   ```bash
   git clone https://github.com/Tystr12/dadsbooks2.git
   cd dadsbooks2
   ```

2. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   ```

   ```bash
   # macOS/Linux
   source .venv/bin/activate

   # Windows PowerShell
   .venv\Scripts\Activate.ps1
   ```

3. Install the dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Copy `.env.example` to `.env` and replace the development values. An
   ISBNDB API key is required only for ISBN metadata lookups.

5. Run the migrations and start the development server:

   ```bash
   cd dadsbooks
   python manage.py migrate
   python manage.py runserver
   ```

6. Create a local administrator to use the protected inventory features:

   ```bash
   python manage.py createsuperuser
   ```

## Tests

From the `dadsbooks` directory:

```bash
python manage.py test
```

## Purpose

The project was created to explore relational data modelling, external API
integrations, inventory workflows, authentication, and deployment of a Django
application.
