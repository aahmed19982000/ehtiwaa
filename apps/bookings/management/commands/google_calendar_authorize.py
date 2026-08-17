from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.bookings.google_calendar import CALENDAR_SCOPES

ENV_KEYS = ["GOOGLE_CALENDAR_CLIENT_ID", "GOOGLE_CALENDAR_CLIENT_SECRET", "GOOGLE_CALENDAR_REFRESH_TOKEN"]


class Command(BaseCommand):
    help = (
        "One-time OAuth authorization for Google Calendar (Meet link creation "
        "for bookings). Opens a browser for you to sign in with the Google "
        "account whose calendar should host booking events, then writes the "
        "resulting credentials to .env. See docs/google-calendar-setup.md."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "client_secrets_file",
            help=(
                "Path to the OAuth client JSON downloaded from Google Cloud "
                "Console (APIs & Services > Credentials > OAuth client ID > "
                "Desktop app)."
            ),
        )

    def handle(self, *args, **options):
        try:
            from google_auth_oauthlib.flow import InstalledAppFlow
        except ImportError as exc:
            raise CommandError(
                "google-auth-oauthlib not installed — pip install -r requirements/base.txt"
            ) from exc

        client_secrets_path = Path(options["client_secrets_file"])
        if not client_secrets_path.exists():
            raise CommandError(f"File not found: {client_secrets_path}")

        flow = InstalledAppFlow.from_client_secrets_file(
            str(client_secrets_path), scopes=CALENDAR_SCOPES
        )
        # prompt=consent + access_type=offline forces Google to issue a
        # refresh_token even if this account already authorized this app
        # before (otherwise it's only returned on the very first consent).
        credentials = flow.run_local_server(port=0, access_type="offline", prompt="consent")

        if not credentials.refresh_token:
            raise CommandError(
                "No refresh token returned. Revoke this app's access at "
                "https://myaccount.google.com/permissions and run this command again."
            )

        self.stdout.write(self.style.SUCCESS("Authorized as a Google account successfully."))
        self._update_env(credentials)

    def _update_env(self, credentials):
        values = {
            "GOOGLE_CALENDAR_CLIENT_ID": credentials.client_id,
            "GOOGLE_CALENDAR_CLIENT_SECRET": credentials.client_secret,
            "GOOGLE_CALENDAR_REFRESH_TOKEN": credentials.refresh_token,
        }

        env_path = Path(settings.BASE_DIR) / ".env"
        if not env_path.exists():
            self.stdout.write(self.style.WARNING(f".env not found at {env_path} — add these manually:"))
            for key, value in values.items():
                self.stdout.write(f"{key}={value}")
            return

        lines = env_path.read_text().splitlines()
        seen = set()
        for i, line in enumerate(lines):
            for key, value in values.items():
                if line.startswith(f"{key}="):
                    lines[i] = f"{key}={value}"
                    seen.add(key)
        for key, value in values.items():
            if key not in seen:
                lines.append(f"{key}={value}")

        env_path.write_text("\n".join(lines) + "\n")
        self.stdout.write(self.style.SUCCESS(f"Updated {env_path} — restart the dev server to pick it up."))
