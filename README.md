# 💧 AquaFlow — Water Jar Supply Management System

A complete, production-ready web application to manage your 20-litre water jar delivery business.

---

## ✅ Features

| Module | Features |
|--------|----------|
| **Authentication** | Secure login, session management, password change |
| **Dashboard** | KPI cards, delivery chart, revenue chart, alerts |
| **Customers** | Add/Edit/Delete, search, filter, ledger, status |
| **Deliveries** | Daily entry, bulk entry, history, CSV export |
| **Billing** | Auto invoice generation, PDF download/print |
| **Payments** | Record payments (cash/UPI/bank/cheque), status tracking |
| **Reports** | Jar status, outstanding dues, monthly summary, collections |
| **Settings** | Business info, jar rate, GST, warning threshold |

---

## 🖥️ Tech Stack

- **Backend:** Python 3.x + Flask + SQLAlchemy
- **Frontend:** Bootstrap 5 + Chart.js
- **Database:** SQLite (production-ready for PostgreSQL migration)
- **PDF:** ReportLab
- **Auth:** Flask-Login

---

## 🚀 Quick Start (Local)

### 1. Install dependencies
```bash
cd water_jar_system
pip install -r requirements.txt
```

### 2. Run the application
```bash
python run.py
```

### 3. Open your browser
```
http://localhost:5000
```

### 4. Login
- **Username:** `admin`
- **Password:** `admin123`
- ⚠️ Change this password immediately via Settings → Change Password

### 5. (Optional) Load demo data
```bash
python seed_demo.py
```

---

## 📁 Project Structure

```
water_jar_system/
├── run.py                      # Entry point
├── config.py                   # App configuration
├── requirements.txt
├── seed_demo.py                # Demo data seeder
│
├── app/
│   ├── __init__.py             # App factory
│   ├── blueprints/
│   │   ├── auth.py             # Login / Logout
│   │   ├── dashboard.py        # Main dashboard
│   │   ├── customers.py        # Customer management
│   │   ├── deliveries.py       # Delivery entry
│   │   ├── billing.py          # Invoice generation
│   │   ├── payments.py         # Payment recording
│   │   ├── reports.py          # All reports
│   │   └── settings.py         # Business settings
│   │
│   ├── models/
│   │   ├── user.py             # Users table
│   │   ├── customer.py         # Customers table
│   │   ├── delivery.py         # Deliveries table
│   │   ├── invoice.py          # Invoices table
│   │   ├── payment.py          # Payments table
│   │   └── settings.py         # Settings table
│   │
│   ├── utils/
│   │   └── pdf_generator.py    # ReportLab PDF invoice
│   │
│   └── templates/              # Jinja2 HTML templates
│       ├── base.html           # Sidebar + topbar layout
│       ├── auth/login.html
│       ├── dashboard/index.html
│       ├── customers/          # index, form, view, ledger
│       ├── deliveries/         # index, form, bulk
│       ├── billing/            # index, generate, view, edit
│       ├── payments/           # index, form
│       ├── reports/            # jar_status, outstanding, monthly, collections
│       └── settings/index.html
```

---

## 🗄️ Database Schema

### customers
| Field | Type | Description |
|-------|------|-------------|
| id | INT | Primary key |
| company_name | VARCHAR | Business name |
| contact_person | VARCHAR | Contact name |
| mobile | VARCHAR | Mobile number |
| jar_rate | FLOAT | ₹ per jar |
| opening_jar_balance | INT | Jars at system start |
| is_active | BOOL | Active status |

### deliveries
| Field | Type | Description |
|-------|------|-------------|
| customer_id | FK | Reference to customer |
| delivery_date | DATE | Date of delivery |
| jars_delivered | INT | Full jars sent |
| jars_returned | INT | Empty jars received |

### invoices
| Field | Type | Description |
|-------|------|-------------|
| invoice_number | VARCHAR | Auto-generated (INV-2026-0001) |
| billing_month/year | INT | Billing period |
| total_jars | INT | Jars delivered in period |
| grand_total | FLOAT | Total amount |
| status | VARCHAR | unpaid / partial / paid |

### payments
| Field | Type | Description |
|-------|------|-------------|
| invoice_id | FK | Linked invoice |
| amount | FLOAT | Amount paid |
| method | VARCHAR | cash / upi / bank / cheque |

---

## ⚙️ Configuration

Edit `config.py` or set environment variables:

```bash
SECRET_KEY=your-secret-key-here
DATABASE_URL=postgresql://user:pass@host/dbname   # For PostgreSQL
```

---

## 🐘 PostgreSQL Migration

1. Install: `pip install psycopg2-binary`
2. Set `DATABASE_URL=postgresql://user:pass@host/dbname`
3. Run: `python run.py` (SQLAlchemy auto-creates tables)

---

## 🌐 Production Deployment (Linux/Ubuntu)

### With Gunicorn + Nginx

```bash
# Install gunicorn
pip install gunicorn

# Run
gunicorn -w 4 -b 0.0.0.0:5000 "run:app"
```

### Nginx config (`/etc/nginx/sites-available/aquaflow`)
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Systemd service (`/etc/systemd/system/aquaflow.service`)
```ini
[Unit]
Description=AquaFlow Water Jar Management
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/water_jar_system
ExecStart=/usr/bin/gunicorn -w 4 -b 127.0.0.1:5000 run:app
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable aquaflow
sudo systemctl start aquaflow
```

---

## 📱 Mobile Access

The app is fully responsive (Bootstrap 5). Access from any phone browser using your server's IP:

```
http://YOUR-SERVER-IP:5000
```

For local network access (same WiFi):
```
http://192.168.x.x:5000
```

---

## 🔑 Default Login

| Field | Value |
|-------|-------|
| Username | `admin` |
| Password | `admin123` |

**Change immediately via:** Settings → Change Password

---

## 📊 Business Workflow

```
1. Add Customers → Set jar rate
2. Every day → Record Deliveries (individual or bulk)
3. End of month → Generate Invoices (auto-calculated)
4. Share/print PDF → Customer pays
5. Record Payment → Invoice marked paid
6. Reports → Jar balance, outstanding dues
```

---

## 🛡️ Security Notes

- Change default `SECRET_KEY` in production
- Change admin password immediately
- Use HTTPS in production (via Let's Encrypt / Nginx SSL)
- Backup `water_jar.db` regularly

---

*Built with Flask + Bootstrap 5 + ReportLab*
