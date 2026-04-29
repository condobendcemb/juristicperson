# Juristic Person Management System

A comprehensive web application for juristic persons and apartment management, built with Flask and PostgreSQL.

## Features

- **Room Management:** Track rooms, buildings, floors, and resident history.
- **Income & Pricing:** Flexible configuration for service fees, water rates, and utility charges.
- **Periodic Recording:** Streamlined entry for monthly meter readings (Water/Electricity) with real-time validation.
- **Automated Invoicing:** Generate professional invoices with automated VAT and service fee calculations.
- **Receipt Management:** Process payments, generate receipts, and track unpaid balances.
- **Professional Printing:** Support for multiple paper sizes:
    - Standard A4
    - A5 (Portrait/Landscape)
    - Continuous Dot Matrix Paper (9x11", 9.5x11", 9x5.5")
- **RBAC:** Role-based access control for administrators and managers.

## Tech Stack
- **Backend:** Flask, Flask-SQLAlchemy (PostgreSQL)
- **Frontend:** Bootstrap 5, HTMX, SweetAlert2, FontAwesome
- **Deployment:** Docker & Docker Compose

## Getting Started

### Prerequisites
- Docker and Docker Compose

### Running Locally
1. Clone the repository
2. Start the services:
   ```bash
   docker-compose up -d
   ```
3. Initialize the database (if needed):
   Access the container and run migration or direct init logic.

## Project Structure
- `app.py`: Main Flask application and routes.
- `models.py`: SQLAlchemy database models.
- `templates/`: Jinja2 templates for UI and printable documents.
- `docker-compose.yml`: Infrastructure configuration.

---
*Developed for efficient juristic person operations.*

# --- github
git add . 
git commit -m "update logs"
git push