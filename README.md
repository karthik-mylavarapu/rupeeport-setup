# RupeePort setup

Cross-platform setup helper and buyer documentation for **RupeePort**, the Razorpay + UPI starter kit for FastAPI.

- **Buy RupeePort:** [Solo — ₹1,499](https://templatecraft1988.gumroad.com/l/rupeeport) · [Team — ₹7,999](https://templatecraft1988.gumroad.com/l/rupeeport-team)
- **Full install guide:** [INSTALL.md](INSTALL.md)
- **Installer:** [installer/rupeeport_setup.py](installer/rupeeport_setup.py)

> This repository contains the **setup helper and documentation only**. It does **not** contain the paid RupeePort source. The kit is downloaded from Gumroad and remains private.

## What this is

A single Python installer that works on Windows, macOS and Linux. It:

1. checks Python 3.10+
2. creates `.venv`
3. installs the kit's dependencies
4. creates `.env` from `.env.example`
5. prompts for the buyer's business details and Razorpay keys
6. generates the admin token and webhook secret
7. runs the 45 automated tests
8. prints the start command and admin URL

It does **not** create a Razorpay account, register a webhook, configure a domain, deploy the app or file GST.

## Prerequisites

| Requirement | Details |
|---|---|
| Python | 3.10+; 3.12 recommended |
| OS | Windows 10/11, macOS 12+, or modern Linux |
| Internet | Needed for the first `pip install` |
| Razorpay account | Test Mode first; KYC for live |
| Razorpay keys | Key ID and Key Secret from Dashboard → Account & Settings → API Keys |
| Business details | Name, address, email, GST state code |
| GSTIN | Optional; blank means Bill of Supply |
| Domain + HTTPS | Live webhooks only; not needed for local testing |
| Text editor | To edit `.env` and `app/products.py` |

You can run the 45 tests with **no Razorpay account and no keys**. Checkout only works after you add Test Mode keys.

## Quick start

1. Download the kit from Gumroad and unzip it.
2. Download [`installer/rupeeport_setup.py`](installer/rupeeport_setup.py).
3. Open a terminal in the unzipped kit folder.
4. Run the installer.

**Windows:**

```powershell
py -3 rupeeport_setup.py --project-dir C:\path\to\rzp-kit
```

**macOS / Linux:**

```bash
python3 rupeeport_setup.py --project-dir /path/to/rzp-kit
```

Replace the path with the folder that contains `app/main.py`.

The installer prompts for:

| Prompt | What to paste |
|---|---|
| Business name / address / email | Your invoice details |
| GST state code | Two digits, e.g. `36` for Telangana |
| GSTIN | 15 characters, or Enter if not registered |
| Public base URL | `http://localhost:8000` for local, HTTPS domain for live |
| Razorpay Key ID | `rzp_test_...` |
| Razorpay Key Secret | Hidden while pasting |
| Razorpay Webhook Secret | Paste one, or Enter to generate |

The admin token is generated automatically; you do not need to provide one.

## Start the app

**Windows:**

```powershell
.venv\Scripts\python -m uvicorn app.main:app --reload
```

**macOS / Linux:**

```bash
.venv/bin/python -m uvicorn app.main:app --reload
```

Open `http://localhost:8000`. The admin URL is printed by the installer.

## Status

- Tested on **Linux** against the buyer kit: **45 tests passed**.
- Windows and macOS paths use only the Python standard library, but have not been run on those systems here.
- This is a Python script, not a signed `.exe`. Windows/macOS may show security warnings for unsigned packaged binaries; this repository does not ship one.
- The installer is **not yet inside the Gumroad zip**. Download it from this repo and use `--project-dir`.

## Support

Use the support email on your Gumroad receipt. GitHub Issues are disabled so support stays in one place.

When asking for help, send:

- OS and version
- Python version
- exact command
- full error text
- terminal screenshot with keys redacted

Never send `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET`, `ADMIN_TOKEN`, `.env` or customer payment data.

## Security

See [SECURITY.md](SECURITY.md). Never commit `.env` or share keys.

## Licence

The setup helper and documentation are provided for installing a legitimately purchased copy of RupeePort. The RupeePort kit itself is licensed separately under the `LICENSE.txt` inside the purchased kit. See [LICENSE](LICENSE).
