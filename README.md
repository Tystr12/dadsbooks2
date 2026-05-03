# 📚 DadsBooks – Bookstore Inventory System

A fullstack bookstore and inventory management system built with Django.  
This project allows admins to manage book inventory while providing a simple frontend for browsing available books.

---

## 🚀 Tech Stack

- **Backend:** Python, Django
- **Database:** SQLite
- **Hosting:** PythonAnywhere
- **API Integration:** ISBN database API

---

## ✨ Features

### 📖 Inventory Management
- Add, update, and remove books
- Track stock levels
- Manage pricing

### 🔎 ISBN API Integration
- Automatically fetch book details using ISBN
- Reduces manual data entry
- Ensures accurate book metadata

### 🔐 Admin System
- Secure login for administrators
- Full CRUD functionality for books

### 🛒 Shop Frontend
- Browse available books
- View prices and availability
- Clean and simple UI

---

## 🧠 What I Learned

- Building fullstack applications with Django
- Working with external APIs (ISBN lookup)
- Structuring models, views, and templates
- Deploying a Django app to PythonAnywhere
- Handling authentication and admin workflows

---

## 📦 Installation (Local Setup)

```bash
# Clone the repository
git clone https://github.com/yourusername/dadsbooks.git

# Navigate into project
cd dadsbooks

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Linux/Mac
# venv\Scripts\activate   # On Windows

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Start server
python manage.py runserver

```
---
## 🌐 Usage

Once the development server is running, you can access the app at:

- **Homepage (admin dashboard):**  
  http://localhost:8000/
  
  If logged in as superuser go to dashboard, if not login page.

- **Admin / Dashboard:**  
  http://localhost:8000/dashboard/

- **Django Admin Panel:**  
  http://localhost:8000/admin/

- **Shop page (NOT FINISHED)**  
  http://localhost:8000/shop/

> Note: Make sure to create a superuser to access admin features:
> ```bash
> python manage.py createsuperuser
> ```