# RupeePort installer

`rupeeport_setup.py` is a dependency-free Python installer. It runs before the
kit's own dependencies are installed.

## Usage

From the unzipped kit:

```bash
python3 scripts/setup.py
```

From this repository, against an unzipped kit elsewhere:

```bash
python3 rupeeport_setup.py --project-dir /path/to/rzp-kit
```

Windows:

```powershell
py -3 rupeeport_setup.py --project-dir C:\path\to\rzp-kit
```

## Flags

| Flag | Meaning |
|---|---|
| `--project-dir PATH` | Path to the unzipped kit (auto-detected when run inside it) |
| `--yes` | Non-interactive; use `.env.example` defaults and generate secrets |
| `--reconfigure` | Back up `.env` and prompt for business/Razorpay details again |
| `--skip-tests` | Install and configure without running pytest |
| `--start` | Start the development server after setup |

## What it asks for

- Business name, address and email
- GST state code and optional GSTIN
- Public base URL
- Razorpay Key ID and Key Secret
- Razorpay Webhook Secret (or generate one)

It generates the admin token itself. It never sends keys anywhere; they are
written only to the local `.env`.

## What it does not do

- Create a Razorpay account
- Register a webhook
- Configure a domain or HTTPS
- Deploy the app
- File GST
