import os
from datetime import datetime, date
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, flash, session, abort
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-secret-key")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///vidoora.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="customer")  # customer/provider
    phone = db.Column(db.String(30))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    provider_profile = db.relationship("ProviderProfile", backref="user", uselist=False)
    bookings = db.relationship("Booking", backref="customer", foreign_keys="Booking.customer_id")


class ProviderProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), unique=True, nullable=False)
    business_name = db.Column(db.String(140), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    bio = db.Column(db.Text)
    starting_price = db.Column(db.Integer, nullable=False, default=5000)
    services = db.Column(db.String(300), default="Photography, Videography")
    is_approved = db.Column(db.Boolean, default=True)


class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    provider_id = db.Column(db.Integer, db.ForeignKey("provider_profile.id"), nullable=False)
    event_type = db.Column(db.String(80), nullable=False)
    event_date = db.Column(db.Date, nullable=False)
    event_city = db.Column(db.String(100), nullable=False)
    budget = db.Column(db.Integer, nullable=False)
    details = db.Column(db.Text)
    status = db.Column(db.String(20), default="Pending")  # Pending/Accepted/Declined
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    provider = db.relationship("ProviderProfile", backref="received_bookings")


def current_user():
    user_id = session.get("user_id")
    return db.session.get(User, user_id) if user_id else None


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user():
            flash("Please sign in to continue.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


@app.context_processor
def inject_user():
    return {"logged_in_user": current_user(), "today": date.today().isoformat()}


@app.route("/")
def index():
    city = request.args.get("city", "").strip()
    event = request.args.get("event", "").strip()
    query = ProviderProfile.query.filter_by(is_approved=True)
    if city:
        query = query.filter(ProviderProfile.city.ilike(f"%{city}%"))
    if event:
        query = query.filter(ProviderProfile.services.ilike(f"%{event}%"))
    providers = query.order_by(ProviderProfile.starting_price.asc()).all()
    return render_template("index.html", providers=providers, city=city, event=event)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "customer")
        phone = request.form.get("phone", "").strip()

        if not name or not email or len(password) < 8:
            flash("Enter your name and email, and use a password of at least 8 characters.", "danger")
            return render_template("register.html")
        if role not in ("customer", "provider"):
            abort(400)
        if User.query.filter_by(email=email).first():
            flash("An account with that email already exists.", "danger")
            return render_template("register.html")

        user = User(
    name=name,
    email=email,
    password_hash=generate_password_hash(
        password,
        method="pbkdf2:sha256"
    ),
    role=role,
    phone=phone
)
        db.session.add(user)
        db.session.flush()

        if role == "provider":
            business_name = request.form.get("business_name", "").strip()
            city = request.form.get("city", "").strip()
            if not business_name or not city:
                db.session.rollback()
                flash("Service providers must enter a business name and city.", "danger")
                return render_template("register.html")
            profile = ProviderProfile(
                user_id=user.id, business_name=business_name, city=city,
                bio=request.form.get("bio", "").strip(),
                starting_price=max(0, int(request.form.get("starting_price", 5000) or 5000)),
                services=request.form.get("services", "Photography, Videography").strip()
            )
            db.session.add(profile)

        db.session.commit()
        session["user_id"] = user.id
        flash("Your Vidoora account is ready.", "success")
        return redirect(url_for("dashboard"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            session.clear()
            session["user_id"] = user.id
            flash("Welcome back!", "success")
            return redirect(url_for("dashboard"))
        flash("Invalid email or password.", "danger")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been signed out.", "info")
    return redirect(url_for("index"))


@app.route("/provider/<int:provider_id>")
def provider_detail(provider_id):
    provider = db.get_or_404(ProviderProfile, provider_id)
    return render_template("provider.html", provider=provider)


@app.route("/book/<int:provider_id>", methods=["GET", "POST"])
@login_required
def book(provider_id):
    provider = db.get_or_404(ProviderProfile, provider_id)
    user = current_user()
    if user.role != "customer":
        flash("Only customer accounts can request a booking.", "warning")
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        try:
            event_date = date.fromisoformat(request.form.get("event_date", ""))
            budget = int(request.form.get("budget", "0"))
        except (ValueError, TypeError):
            flash("Please enter a valid event date and budget.", "danger")
            return render_template("book.html", provider=provider)
        if event_date < date.today() or budget <= 0:
            flash("Choose a future date and enter a budget greater than zero.", "danger")
            return render_template("book.html", provider=provider)

        booking = Booking(
            customer_id=user.id, provider_id=provider.id,
            event_type=request.form.get("event_type", "").strip(),
            event_date=event_date,
            event_city=request.form.get("event_city", "").strip(),
            budget=budget, details=request.form.get("details", "").strip()
        )
        if not booking.event_type or not booking.event_city:
            flash("Event type and event city are required.", "danger")
            return render_template("book.html", provider=provider)
        db.session.add(booking)
        db.session.commit()
        flash("Booking request sent! The provider can now review it.", "success")
        return redirect(url_for("dashboard"))
    return render_template("book.html", provider=provider)


@app.route("/dashboard")
@login_required
def dashboard():
    user = current_user()
    if user.role == "provider":
        profile = user.provider_profile
        bookings = Booking.query.filter_by(provider_id=profile.id).order_by(Booking.created_at.desc()).all()
    else:
        profile = None
        bookings = Booking.query.filter_by(customer_id=user.id).order_by(Booking.created_at.desc()).all()
    return render_template("dashboard.html", user=user, profile=profile, bookings=bookings)


@app.route("/booking/<int:booking_id>/status", methods=["POST"])
@login_required
def update_booking_status(booking_id):
    booking = db.get_or_404(Booking, booking_id)
    user = current_user()
    if user.role != "provider" or not user.provider_profile or booking.provider_id != user.provider_profile.id:
        abort(403)
    status = request.form.get("status")
    if status not in ("Accepted", "Declined"):
        abort(400)
    booking.status = status
    db.session.commit()
    flash(f"Booking {status.lower()}.", "success")
    return redirect(url_for("dashboard"))


@app.cli.command("init-db")
def init_db():
    """Create database tables."""
    db.create_all()
    print("Vidoora database tables created.")


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
