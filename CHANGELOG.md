# Changelog

## v0.1.0 — 2026-10-21

- Added the cross-platform Python setup helper.
- Prompts for business name, address, email, GST state code, GSTIN and base URL.
- Prompts for Razorpay Key ID, Key Secret and webhook secret.
- Generates `ADMIN_TOKEN` and `RAZORPAY_WEBHOOK_SECRET` when needed.
- Creates `.venv`, installs dependencies, runs the 45-test suite, prints the start command and admin URL.
- Added the buyer installation guide, prerequisites, troubleshooting and security notes.
- Tested on Linux: 45 tests passed.
- Windows and macOS code paths are standard-library only but have not been run on those systems yet.
- Not yet a signed executable and not yet included in the Gumroad zip.
