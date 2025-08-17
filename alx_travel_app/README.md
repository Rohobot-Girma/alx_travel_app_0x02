# ALX Travel App 0x00

This project models travel listings, bookings, and reviews in Django.

## Models
- **Listing**: Travel destination with price
- **Booking**: Reservations by users
- **Review**: User feedback on listings

## API Endpoints

- `GET /api/listings/`
- `POST /api/listings/`
- `GET /api/bookings/`
- `POST /api/bookings/`
- ...

## API Documentation

- Swagger UI: [http://localhost:8000/swagger/](http://localhost:8000/swagger/)

## Seed the Database
To populate the database with sample data:

```bash
python manage.py seed
```

# Payments (Chapa) — alx_travel_app_0x02

This module integrates **Chapa** to accept booking payments.

## Env
CHAPA_SECRET_KEY=CHASECK_TEST_xxx
CHAPA_BASE_URL=https://api.chapa.co
SITE_BASE_URL=https://your-backend.example.com
CHAPA_RETURN_URL=https://your-frontend.com/payment/return
CHAPA_CALLBACK_PATH=/api/payments/callback/


## Endpoints
- `POST /api/payments/initiate/` → returns `{ tx_ref, checkout_url }`
- `GET  /api/payments/callback/`  → Chapa callback (triggers server-side verify)
- `GET  /api/payments/verify/?tx_ref=...` → manual verify/check

## Flow
1. Create booking → call `initiate` with booking + customer info.
2. Redirect user to `checkout_url`.
3. On completion, Chapa redirects to `CHAPA_RETURN_URL` and calls `CHAPA_CALLBACK_PATH`.  
4. Server verifies via `GET /v1/transaction/verify/<tx_ref>` and updates `Payment.status`.

## Model
- `Payment`: `booking`, `amount`, `currency`, `tx_ref`, `chapa_ref_id`, `checkout_url`, `status`, `init_response`, `verify_response`.

## Email
- On first transition to `success`, we send a confirmation email via Celery: `listings.tasks.send_payment_success_email`.

## Testing
- Use test secret key and Chapa sandbox.
- Save:
  - `initiate` JSON, `verify` JSON
  - Admin screenshots for `Payment` (pending → success)

## References
- Chapa Accept Payments (Initialize + fields): developer.chapa.co → Integrations → Accept Payment  
- Chapa Verify Payments: developer.chapa.co → Integrations → Verify Payment
