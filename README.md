# Vidoora – Photography & Videography Booking Platform

A starter Flask application for connecting customers with photographers and videographers for weddings, receptions, engagements, birthdays, anniversaries, pre-wedding shoots and other events.

## MVP features
- Customer and service-provider registration
- Password hashing and login/logout
- Provider profiles with city, services and starting price
- Search providers by city and service keyword
- Customers send booking requests with event type, date, location and budget
- Providers accept or decline booking enquiries
- Customer/provider dashboards
- SQLite database for local development

## Requirements
- Python 3.10+
- pip

## Run locally (Mac/Linux)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-prod.txt
flask --app app init-db
flask --app app run --debug
```
Open http://127.0.0.1:5000

On Windows, activate with:
```powershell
.venv\Scripts\activate
```

## Docker
```bash
docker build -t vidoora:dev .
docker run --rm -p 5000:5000 -e SECRET_KEY="replace-this" vidoora:dev
```
The Docker image uses Gunicorn. For a persistent database, mount a volume and configure `DATABASE_URL`; the default SQLite database is intended for local learning only.

## Suggested next milestones for the DevOps project
1. Add automated tests with pytest.
2. Add Jenkinsfile stages: checkout, install dependencies, lint, test.
3. Add SonarQube analysis and Trivy image scan.
4. Build and push the image to AWS ECR.
5. Deploy to Kubernetes/EKS using manifests or Helm.
6. Add production database, object storage for portfolios, provider verification, notifications and payment integration.

## Important production gaps
This is a learning MVP, not a production-ready marketplace. Before real customers use it, add CSRF protection, rate limiting, email verification, password reset, secure session/cookie settings, provider moderation/verification, privacy controls, audit logging, robust validation, tests, database migrations, backups and payment-provider integration. Do not collect or store card details yourself. Add booking cancellation/refund policies and clear terms before accepting real bookings.
