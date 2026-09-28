import streamlit as st

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


GMAIL_SCOPE = (
    "https://www.googleapis.com/auth/gmail.modify"
)


def get_gmail_service():

    # User must first be logged in through Streamlit / Google
    if not st.user.is_logged_in:
        return None

    try:
        # Streamlit exposes the Google OAuth access token
        # because expose_tokens = ["access"] is configured
        # in .streamlit/secrets.toml
        access_token = st.user.tokens["access"]

        if not access_token:
            return None

        # Create Google credentials using the current
        # user's OAuth access token.
        credentials = Credentials(
            token=access_token,
            scopes=[GMAIL_SCOPE]
        )

        # Build Gmail API service for this user.
        gmail_service = build(
            "gmail",
            "v1",
            credentials=credentials
        )

        return gmail_service

    except Exception as e:

        st.error(
            f"Could not create Gmail service: {e}"
        )

        return None