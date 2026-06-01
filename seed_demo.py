"""Seed demo data for testing"""
from app import create_app, db
from app.models.customer import Customer
from app.models.delivery import Delivery
from app.models.invoice import Invoice
from app.models.payment import Payment
from datetime import date, timedelta
import random

app = create_app('development')

with app.app_context():
    # Skip if data exists
    if Customer.query.count() > 0:
        print("Demo data already exists. Skipping.")
        exit()

    customers_data = [
        ("Sunrise Technologies", "Rajesh Kumar", "9876543210", "rajesh@sunrise.com", "Andheri West", 35.0),
        ("Green Valley Offices", "Priya Sharma", "9876543211", "priya@gvo.com", "Powai", 30.0),
        ("Metro Mall", "Amit Patel", "9876543212", "amit@metromall.com", "Thane", 28.0),
        ("Blue Star Hospital", "Dr. Neha Singh", "9876543213", "neha@bluestar.com", "Bandra", 32.0),
        ("City College", "Prof. Ramesh", "9876543214", "ramesh@citycollege.com", "Dadar", 25.0),
        ("Horizon Hotels", "Suresh Nair", "9876543215", "suresh@horizonhotels.com", "Juhu", 40.0),
        ("Pyramid Infotech", "Kavita Joshi", "9876543216", "kavita@pyramid.com", "Lower Parel", 30.0),
        ("Coastal Textiles", "Arun Desai", "9876543217", "arun@coastal.com", "Kurla", 28.0),
    ]

    customers = []
    for i, (company, contact, mobile, email, city, rate) in enumerate(customers_data):
        c = Customer(
            company_name=company, contact_person=contact, mobile=mobile,
            email=email, city=city, state="Maharashtra", jar_rate=rate,
            opening_jar_balance=random.randint(0, 5),
            address=f"{random.randint(1,200)}, Industrial Area",
        )
        db.session.add(c)
        customers.append(c)
    db.session.commit()
    print(f"Created {len(customers)} customers")

    # Create deliveries for last 60 days
    today = date.today()
    deliveries_count = 0
    for c in customers:
        for days_ago in range(60, 0, -1):
            d = today - timedelta(days=days_ago)
            if d.weekday() == 6:  # Skip Sundays
                continue
            if random.random() < 0.7:  # 70% days have delivery
                delivered = random.randint(2, 8)
                returned = random.randint(0, min(delivered, 3))
                delivery = Delivery(
                    customer_id=c.id,
                    delivery_date=d,
                    jars_delivered=delivered,
                    jars_returned=returned,
                    delivery_staff=random.choice(["Ramesh", "Sunil", "Prakash"]),
                    created_by=1,
                )
                db.session.add(delivery)
                deliveries_count += 1
    db.session.commit()
    print(f"Created {deliveries_count} delivery entries")

    # Generate invoices for last 2 months
    from sqlalchemy import func
    for month_offset in [2, 1]:
        m = today.month - month_offset
        y = today.year
        while m <= 0:
            m += 12
            y -= 1
        for c in customers:
            jars = db.session.query(func.sum(Delivery.jars_delivered)).filter(
                Delivery.customer_id == c.id,
                func.strftime('%m', Delivery.delivery_date) == f'{m:02d}',
                func.strftime('%Y', Delivery.delivery_date) == str(y)
            ).scalar() or 0
            if jars == 0:
                continue
            subtotal = jars * c.jar_rate
            inv = Invoice(
                invoice_number=Invoice.generate_invoice_number(y),
                customer_id=c.id,
                invoice_date=date(y, m, 28),
                billing_month=m,
                billing_year=y,
                total_jars=jars,
                rate_per_jar=c.jar_rate,
                subtotal=round(subtotal, 2),
                gst_percent=0,
                gst_amount=0,
                grand_total=round(subtotal, 2),
                balance_due=round(subtotal, 2),
                status='unpaid',
                created_by=1,
            )
            db.session.add(inv)
            db.session.flush()

            # Some customers have paid
            if random.random() < 0.6:
                paid = round(subtotal * random.uniform(0.5, 1.0), 2)
                p = Payment(
                    invoice_id=inv.id,
                    customer_id=c.id,
                    payment_date=date(y, m, 28) + timedelta(days=random.randint(1, 10)),
                    amount=paid,
                    method=random.choice(['cash', 'upi', 'bank']),
                    created_by=1,
                )
                db.session.add(p)
                inv.paid_amount = paid
                inv.update_status()
    db.session.commit()
    print("Created invoices and payments for last 2 months")
    print("✅ Demo data seeded successfully!")
