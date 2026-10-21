#!/usr/bin/env python3
"""RupeePort one-command setup for Windows, macOS and Linux.

This script is deliberately dependency-free: it uses only the Python standard
library, so it can run before the kit's requirements are installed.

Typical use from the unzipped kit root:

    python scripts/setup.py

Or, if this file lives outside the kit:

    python rupeeport_setup.py --project-dir /path/to/rzp-kit

It will:
  1. Check Python 3.10+.
  2. Create .venv if needed.
  3. Install requirements-dev.txt (or requirements.txt).
  4. Create .env from .env.example, with generated ADMIN_TOKEN and
     RAZORPAY_WEBHOOK_SECRET. It never overwrites an existing .env unless
     --reconfigure is passed.
  5. Run the 45-test suite.
  6. Print the exact start command and admin URL.

It does not create a Razorpay account, register webhooks, configure a domain,
deploy the app, or file GST. Those remain buyer actions.
"""

from __future__ import annotations

import argparse
import getpass
import os
import re
import secrets
import shutil
import subprocess
import sys
import venv
from datetime import datetime
from pathlib import Path

MIN_PYTHON = (3, 10)
MARKERS = ("app/main.py", "requirements.txt", ".env.example")
PLACEHOLDER_ADMIN = "change-this-long-random-string"
PLACEHOLDER_WEBHOOK = "change-me"


class SetupError(RuntimeError):
    """A setup problem that should be shown without a traceback."""


def info(message: str) -> None:
    print(f"[setup] {message}")


def warn(message: str) -> None:
    print(f"[warn]  {message}")


def fail(message: str) -> None:
    print(f"[error] {message}", file=sys.stderr)


def find_project_root(explicit: Path | None) -> Path:
    """Find the unzipped kit, even when this script is run from elsewhere."""
    candidates: list[Path] = []
    if explicit is not None:
        candidates.append(explicit.expanduser())
    else:
        here = Path.cwd()
        candidates.extend([here, *here.parents])
        script_dir = Path(__file__).resolve().parent
        candidates.extend([script_dir, *script_dir.parents])

    seen: set[Path] = set()
    for candidate in candidates:
        try:
            candidate = candidate.resolve()
        except OSError:
            continue
        if candidate in seen:
            continue
        seen.add(candidate)
        if all((candidate / marker).exists() for marker in MARKERS):
            return candidate

    raise SetupError(
        "Could not find the RupeePort kit. Run this from the unzipped rzp-kit "
        "folder, or pass --project-dir PATH."
    )


def venv_python(root: Path) -> Path:
    if os.name == "nt":
        return root / ".venv" / "Scripts" / "python.exe"
    return root / ".venv" / "bin" / "python"


def ensure_venv(root: Path) -> Path:
    python = venv_python(root)
    if python.exists():
        info(f"Using existing virtual environment: {python}")
        return python

    venv_dir = root / ".venv"
    if venv_dir.exists():
        raise SetupError(
            f"{venv_dir} exists but does not contain a working Python. "
            "Rename or delete it, then run the setup again."
        )

    info("Creating .venv ...")
    try:
        venv.EnvBuilder(with_pip=True, clear=False, symlinks=(os.name != "nt")).create(venv_dir)
    except Exception as exc:  # pragma: no cover - platform-specific
        raise SetupError(
            "Could not create the virtual environment. On Debian/Ubuntu install "
            "python3-venv (sudo apt install python3-venv), then try again. "
            f"Details: {exc}"
        ) from exc

    if not python.exists():
        raise SetupError(
            f"The virtual environment was created but {python} is missing. "
            "Check that Python's venv/ensurepip support is installed."
        )
    return python


def run_command(command: list[str], cwd: Path, capture: bool = False) -> subprocess.CompletedProcess[str]:
    printable = " ".join(command)
    info(f"Running: {printable}")
    try:
        return subprocess.run(
            command,
            cwd=str(cwd),
            check=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=capture,
        )
    except FileNotFoundError as exc:
        raise SetupError(f"Command not found: {command[0]}") from exc
    except subprocess.CalledProcessError as exc:
        if capture:
            if exc.stdout:
                print(exc.stdout.rstrip())
            if exc.stderr:
                print(exc.stderr.rstrip(), file=sys.stderr)
        raise SetupError(
            f"Command failed with exit code {exc.returncode}: {printable}"
        ) from exc


def install_requirements(root: Path, python: Path) -> None:
    requirements = root / "requirements-dev.txt"
    if not requirements.exists():
        requirements = root / "requirements.txt"
    if not requirements.exists():
        raise SetupError("requirements.txt is missing from the kit.")

    info("Installing dependencies (this can take a minute) ...")
    run_command(
        [
            str(python),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-input",
            "-r",
            str(requirements),
        ],
        cwd=root,
    )


def parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def set_env_value(text: str, key: str, value: str) -> str:
    value = str(value).replace("\n", " ").replace("\r", " ").strip()
    lines = text.splitlines()
    prefix = f"{key}="
    for index, line in enumerate(lines):
        if line.startswith(prefix):
            lines[index] = f"{key}={value}"
            break
    else:
        if lines and lines[-1].strip():
            lines.append("")
        lines.append(f"{key}={value}")
    return "\n".join(lines) + "\n"


def write_env(path: Path, updates: dict[str, str]) -> None:
    text = path.read_text(encoding="utf-8")
    for key, value in updates.items():
        if "#" in str(value):
            warn(f"{key} contains '#', which .env treats as a comment. Edit .env if needed.")
        text = set_env_value(text, key, value)
    path.write_text(text, encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def ask_text(
    label: str,
    default: str = "",
    *,
    secret: bool = False,
    required: bool = False,
) -> str:
    suffix = f" [{default}]" if default and not secret else ""
    prompt = f"{label}{suffix}: "
    while True:
        try:
            raw = getpass.getpass(prompt) if secret else input(prompt)
        except (EOFError, KeyboardInterrupt):
            print()
            return default
        raw = raw.strip()
        if raw:
            return raw
        if default or not required:
            return default
        print("A value is required.")


def is_valid_gstin(gstin: str) -> bool:
    """Format + checksum check, matching the kit's GST helper."""
    value = (gstin or "").strip().upper()
    if len(value) != 15 or not value[:2].isdigit():
        return False
    chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    if any(char not in chars for char in value):
        return False
    total = 0
    for index, char in enumerate(value[:14]):
        number = chars.index(char) * (1 if index % 2 == 0 else 2)
        total += number // 36 + number % 36
    check = chars[(36 - total % 36) % 36]
    return value[14] == check


def ask_gstin(default: str) -> str:
    while True:
        value = ask_text("GSTIN (15 characters; press Enter if not registered)", default)
        if not value:
            return ""
        if is_valid_gstin(value):
            return value.upper()
        print("That GSTIN does not pass the format/checksum check. Press Enter to skip, or try again.")


def ask_state_code(default: str) -> str:
    while True:
        value = ask_text("GST state code (36=Telangana, 29=Karnataka, 27=Maharashtra)", default or "36")
        if re.fullmatch(r"\d{2}", value):
            return value
        print("Enter the two-digit state code, for example 36.")


def ask_email(default: str) -> str:
    while True:
        value = ask_text("Business email", default)
        if not value:
            return default
        if "@" in value and "." in value.split("@", 1)[-1]:
            return value
        print("That email address looks incomplete. Try again, or press Enter to keep the default.")


def ask_base_url(default: str) -> str:
    while True:
        value = ask_text(
            "Public base URL (Enter for http://localhost:8000)",
            default or "http://localhost:8000",
        ).rstrip("/")
        if value.startswith(("http://", "https://")):
            return value
        print("Start the URL with http:// or https://, for example https://pay.example.com.")


def prepare_env(root: Path, args: argparse.Namespace) -> dict[str, str]:
    env_path = root / ".env"
    example_path = root / ".env.example"
    existed = env_path.exists()

    if existed and args.reconfigure:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = root / f".env.bak-{stamp}"
        shutil.copy2(env_path, backup)
        info(f"Backed up the old .env to {backup.name}")

    if not existed:
        shutil.copyfile(example_path, env_path)
        info("Created .env from .env.example")

    values = parse_env(env_path)
    updates: dict[str, str] = {}
    interactive = not args.yes and sys.stdin.isatty()

    if (not existed or args.reconfigure) and interactive:
        print("\nBusiness details (press Enter to keep the value in brackets):")
        updates["BUSINESS_NAME"] = ask_text("Business name", values.get("BUSINESS_NAME", ""))
        updates["BUSINESS_ADDRESS"] = ask_text("Business address", values.get("BUSINESS_ADDRESS", ""))
        updates["BUSINESS_EMAIL"] = ask_email(values.get("BUSINESS_EMAIL", ""))
        updates["BUSINESS_STATE_CODE"] = ask_state_code(values.get("BUSINESS_STATE_CODE", "36"))
        updates["GSTIN"] = ask_gstin(values.get("GSTIN", ""))
        updates["BASE_URL"] = ask_base_url(values.get("BASE_URL", "http://localhost:8000"))

        print("\nRazorpay keys (use Test Mode keys until the full test passes):")
        print("  Dashboard > Account & Settings > API Keys > Generate Test Key")
        current_key = values.get("RAZORPAY_KEY_ID", "")
        if "xxxx" in current_key:
            current_key = ""
        key_id = ask_text("Razorpay Key ID (rzp_test_... or rzp_live_...)", current_key)
        if key_id and not key_id.startswith("rzp_"):
            warn("That does not look like a Razorpay key ID; keeping it anyway.")
        if key_id.startswith("rzp_live_"):
            warn("Live Razorpay key detected. Use Test Mode first; switch to live only after the test payment passes.")
        updates["RAZORPAY_KEY_ID"] = key_id or values.get("RAZORPAY_KEY_ID", "")

        current_secret = values.get("RAZORPAY_KEY_SECRET", "")
        if "xxxx" in current_secret:
            current_secret = ""
        key_secret = ask_text("Razorpay Key Secret", current_secret, secret=True)
        updates["RAZORPAY_KEY_SECRET"] = key_secret or values.get("RAZORPAY_KEY_SECRET", "")

        current_webhook = values.get("RAZORPAY_WEBHOOK_SECRET", "")
        if current_webhook == PLACEHOLDER_WEBHOOK:
            current_webhook = ""
        webhook = ask_text(
            "Razorpay Webhook Secret (Enter to generate one; paste the same value in Razorpay)",
            current_webhook,
            secret=True,
        )
        if webhook:
            updates["RAZORPAY_WEBHOOK_SECRET"] = webhook

        if not key_id:
            info("No Razorpay key ID entered; the checkout will not work until you add one to .env.")
        elif not key_secret:
            warn("A Razorpay key ID was entered without a key secret.")
    elif not existed:
        info("Non-interactive mode: using .env.example defaults; edit .env for your business details.")

    # Never leave the two important secrets at their public placeholder values.
    admin_token = values.get("ADMIN_TOKEN", "")
    if not admin_token or admin_token == PLACEHOLDER_ADMIN:
        updates["ADMIN_TOKEN"] = secrets.token_urlsafe(32)

    webhook_secret = updates.get("RAZORPAY_WEBHOOK_SECRET") or values.get("RAZORPAY_WEBHOOK_SECRET", "")
    if not webhook_secret or webhook_secret == PLACEHOLDER_WEBHOOK:
        updates["RAZORPAY_WEBHOOK_SECRET"] = secrets.token_urlsafe(32)

    if updates:
        write_env(env_path, updates)
        if "ADMIN_TOKEN" in updates:
            info("Generated a new ADMIN_TOKEN in .env.")
        if "RAZORPAY_WEBHOOK_SECRET" in updates:
            info("Generated a new RAZORPAY_WEBHOOK_SECRET in .env.")

    if existed and not args.reconfigure:
        current = parse_env(env_path)
        if current.get("ADMIN_TOKEN") in ("", PLACEHOLDER_ADMIN):
            warn("ADMIN_TOKEN is still the placeholder. Run --reconfigure or edit .env.")
        if current.get("RAZORPAY_WEBHOOK_SECRET") in ("", PLACEHOLDER_WEBHOOK):
            warn("RAZORPAY_WEBHOOK_SECRET is still the placeholder. Run --reconfigure or edit .env.")

    return parse_env(env_path)


def validate_env(values: dict[str, str]) -> list[str]:
    warnings: list[str] = []
    admin = values.get("ADMIN_TOKEN", "")
    if admin in ("", PLACEHOLDER_ADMIN):
        warnings.append("ADMIN_TOKEN is not set; /admin is not safe.")
    elif len(admin) < 20:
        warnings.append("ADMIN_TOKEN is shorter than 20 characters; use a longer random value.")

    webhook = values.get("RAZORPAY_WEBHOOK_SECRET", "")
    if webhook in ("", PLACEHOLDER_WEBHOOK):
        warnings.append("RAZORPAY_WEBHOOK_SECRET is not set; webhooks cannot be verified.")

    key_id = values.get("RAZORPAY_KEY_ID", "")
    key_secret = values.get("RAZORPAY_KEY_SECRET", "")
    if not key_id or "xxxx" in key_id or not key_secret or "xxxx" in key_secret:
        warnings.append("Razorpay keys are placeholders; add Test Mode keys before checkout.")
    elif key_id.startswith("rzp_live_"):
        warnings.append("Live Razorpay keys are configured. Complete the Test Mode run before accepting real money.")

    base_url = values.get("BASE_URL", "")
    if not base_url.startswith(("http://", "https://")):
        warnings.append("BASE_URL must start with http:// or https://.")
    elif key_id.startswith("rzp_live_") and base_url.startswith("http://"):
        warnings.append("Live keys with a non-HTTPS BASE_URL: use HTTPS for real payments and webhooks.")

    state = values.get("BUSINESS_STATE_CODE", "")
    if not re.fullmatch(r"\d{2}", state):
        warnings.append("BUSINESS_STATE_CODE should be a two-digit GST state code.")

    gstin = values.get("GSTIN", "")
    if gstin and not is_valid_gstin(gstin):
        warnings.append("GSTIN does not pass the format/checksum check; fix it or leave it blank.")

    return warnings


def run_tests(root: Path, python: Path) -> str:
    info("Running the 45-test suite ...")
    result = run_command(
        [str(python), "-m", "pytest", "-q"],
        cwd=root,
        capture=True,
    )
    output = (result.stdout or "").strip()
    if output:
        print(output)
    match = re.search(r"(\d+) passed", output)
    return f"{match.group(1)} passed" if match else "passed"


def print_summary(
    root: Path,
    python: Path,
    env: dict[str, str],
    test_result: str,
    args: argparse.Namespace,
) -> None:
    token = env.get("ADMIN_TOKEN", "")
    key_id = env.get("RAZORPAY_KEY_ID", "")
    gstin = env.get("GSTIN", "").strip()
    base_url = env.get("BASE_URL", "http://localhost:8000").rstrip("/")
    mode = "LIVE" if key_id.startswith("rzp_live_") else "TEST"

    print("\n" + "=" * 72)
    print("RupeePort setup complete")
    print("=" * 72)
    print(f"Project:  {root}")
    print(f"Python:   {sys.version.split()[0]}")
    print(f"Venv:     {python}")
    print(f"Env file: {root / '.env'}")
    print(f"Mode:     {mode} (Razorpay key prefix: {key_id[:12] or 'not set'})")
    if token and token != PLACEHOLDER_ADMIN:
        print(f"Admin:    {base_url}/admin?token={token}")
    else:
        print("Admin:    set ADMIN_TOKEN in .env first")
    if test_result:
        print(f"Tests:    {test_result}")
    else:
        print("Tests:    skipped")

    print("\nStart the server:")
    if os.name == "nt":
        print(r"  .venv\Scripts\python -m uvicorn app.main:app --reload")
    else:
        print("  .venv/bin/python -m uvicorn app.main:app --reload")
    print(f"\nThen open: {base_url}")

    print("\nNext steps:")
    if "xxxx" in key_id or not key_id:
        print("  1. Add Razorpay Test Mode keys to .env, then restart the server.")
    else:
        print("  1. Razorpay keys are present. Confirm they are Test Mode keys before testing.")
    print("  2. Make a test payment and open the receipt + invoice.")
    print("  3. Create the Razorpay webhook:")
    print(f"       URL:    {base_url}/webhooks/razorpay")
    print("       Secret: copy RAZORPAY_WEBHOOK_SECRET from .env")
    print("       Events: the 13 listed in README.md")
    print("  4. On localhost, test with: python scripts/simulate_webhook.py --help")
    print("  5. Read README.md for deployment and go-live steps.")
    if not gstin:
        print("  GSTIN is blank: the kit will issue a Bill of Supply with no GST.")
    print("\nKeep .env private. It contains your Razorpay secret and admin token.")


def start_server(root: Path, python: Path) -> None:
    print("\nStarting the development server. Press Ctrl+C to stop.\n")
    try:
        subprocess.run(
            [str(python), "-m", "uvicorn", "app.main:app", "--reload"],
            cwd=str(root),
            check=False,
        )
    except KeyboardInterrupt:
        print("\nServer stopped.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Set up the RupeePort FastAPI kit on Windows, macOS or Linux.",
    )
    parser.add_argument(
        "--project-dir",
        type=Path,
        help="Path to the unzipped rzp-kit folder (auto-detected when run inside it).",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Non-interactive: use .env.example defaults and generate secrets.",
    )
    parser.add_argument(
        "--reconfigure",
        action="store_true",
        help="Back up the existing .env and ask for business/Razorpay details again.",
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Install and configure, but do not run pytest.",
    )
    parser.add_argument(
        "--start",
        action="store_true",
        help="Start the development server after setup.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    print("=" * 72)
    print("RupeePort setup")
    print("=" * 72)
    print(f"Python {sys.version.split()[0]} on {sys.platform}")
    if sys.version_info < MIN_PYTHON:
        fail(
            f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ is required. "
            "Install a newer Python from python.org and run this again."
        )
        return 2

    try:
        root = find_project_root(args.project_dir)
        info(f"Kit found at: {root}")

        python = ensure_venv(root)
        install_requirements(root, python)
        env = prepare_env(root, args)

        warnings = validate_env(env)
        for warning in warnings:
            warn(warning)

        test_result = ""
        if not args.skip_tests:
            test_result = run_tests(root, python)
        else:
            info("Skipping tests because --skip-tests was passed.")

        print_summary(root, python, env, test_result, args)
        if args.start:
            start_server(root, python)
        return 0
    except SetupError as exc:
        fail(str(exc))
        return 1
    except KeyboardInterrupt:
        print("\nSetup stopped.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
