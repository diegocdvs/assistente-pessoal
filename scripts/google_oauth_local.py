from __future__ import annotations

import argparse
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar.events",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera refresh token Google localmente.")
    parser.add_argument("--client-secret-file", required=True)
    args = parser.parse_args()

    flow = InstalledAppFlow.from_client_secrets_file(args.client_secret_file, scopes=SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")

    if not creds.refresh_token:
        raise RuntimeError("Refresh token não gerado. Revogue consentimentos antigos e rode novamente.")

    print("GOOGLE_REFRESH_TOKEN=")
    print(creds.refresh_token)


if __name__ == "__main__":
    main()
