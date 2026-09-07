"""
SIP Phase 1 hello-world job.

This is NOT part of CFIE, F5, or any production engine. It exists solely
to prove, end to end, that a Cloud Run Job can:
  1. Read secrets from Secret Manager at runtime
  2. Authenticate to Google APIs using the stored OAuth refresh token
     (no human present, no browser login)
  3. Create a Google Doc
  4. Send a Gmail message

If this succeeds, the single highest-uncertainty item in the whole SIP
architecture (unattended Google auth) is proven to work.
"""

import base64
from email.mime.text import MIMEText

from google.cloud import secretmanager
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

PROJECT_ID = "sports-investment-platform"

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/gmail.send",
]

# Where the test email goes. Using the SIP account's own address for this
# first test keeps things simple -- no new info needed to run it. Once
# real engines are built, reports will go to your personal address instead.
TEST_EMAIL_RECIPIENT = "sportsinvestmentengine@gmail.com"


def get_secret(secret_id):
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{PROJECT_ID}/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")


def get_credentials():
    client_id = get_secret("GOOGLE_OAUTH_CLIENT_ID")
    client_secret = get_secret("GOOGLE_OAUTH_CLIENT_SECRET")
    refresh_token = get_secret("GOOGLE_OAUTH_REFRESH_TOKEN")

    return Credentials(
        token=None,
        refresh_token=refresh_token,
        client_id=client_id,
        client_secret=client_secret,
        token_uri="https://oauth2.googleapis.com/token",
        scopes=SCOPES,
    )


def create_test_doc(creds):
    docs_service = build("docs", "v1", credentials=creds)
    doc = docs_service.documents().create(
        body={"title": "SIP Phase 1 Hello World Test"}
    ).execute()
    doc_id = doc.get("documentId")

    docs_service.documents().batchUpdate(
        documentId=doc_id,
        body={
            "requests": [
                {
                    "insertText": {
                        "location": {"index": 1},
                        "text": (
                            "SIP Phase 1 hello-world test succeeded.\n\n"
                            "This document was created by an unattended "
                            "Cloud Run Job with no human present, using a "
                            "stored OAuth refresh token. If you're reading "
                            "this, the Google integration works end to end."
                        ),
                    }
                }
            ]
        },
    ).execute()

    return doc_id


def send_test_email(creds):
    gmail_service = build("gmail", "v1", credentials=creds)

    message = MIMEText(
        "This is a test email from the SIP Phase 1 hello-world Cloud Run "
        "Job. It was sent unattended, with no human present, using a "
        "stored OAuth refresh token. If you're reading this, Gmail "
        "sending works end to end."
    )
    message["to"] = TEST_EMAIL_RECIPIENT
    message["subject"] = "SIP Hello World Test"

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    gmail_service.users().messages().send(userId="me", body={"raw": raw}).execute()


def main():
    print("Starting SIP hello-world job...")

    creds = get_credentials()
    print("Credentials obtained from Secret Manager and refreshed.")

    doc_id = create_test_doc(creds)
    print(f"Created test doc: https://docs.google.com/document/d/{doc_id}/edit")

    send_test_email(creds)
    print(f"Test email sent to {TEST_EMAIL_RECIPIENT}.")

    print("SIP hello-world job completed successfully.")


if __name__ == "__main__":
    main()
