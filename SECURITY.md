# Security

## Never share these

- `RAZORPAY_KEY_SECRET`
- `RAZORPAY_WEBHOOK_SECRET`
- `ADMIN_TOKEN`
- your `.env` file
- customer payment data

The installer writes keys only to the local `.env`. It does not send them anywhere.

## If a key leaks

1. Rotate the key in the Razorpay Dashboard immediately.
2. Generate a new webhook secret and update the Razorpay webhook.
3. Generate a new `ADMIN_TOKEN` in `.env` and restart the app.
4. Check the Razorpay dashboard for unexpected payments or refunds.

## Reporting a vulnerability

Use the support email on your Gumroad receipt. Do not open a public issue with exploit details or secrets. GitHub Issues are disabled for this repository.

## Scope

This repository contains the setup helper and documentation. The paid RupeePort kit is downloaded from Gumroad and is licensed separately.
