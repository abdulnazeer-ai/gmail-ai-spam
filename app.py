import base64
import html
import re
import time

import pandas as pd
import streamlit as st

from email.utils import parseaddr, parsedate_to_datetime

from gmail_service import get_gmail_service
from ai_classifier import classify_email


# =========================================================
# PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="Gmail AI Spam Detector",
    page_icon="📧",
    layout="wide"
)

st.title("📧 Gmail AI Spam Detector")


# =========================================================
# GOOGLE LOGIN
# =========================================================

if not st.user.is_logged_in:

    st.write(
        "Connect your Gmail account to analyze your Inbox "
        "using Jev's Structured Decision Model."
    )

    st.subheader("Connect Gmail")

    st.write(
        "Google will ask you to sign in and authorize this "
        "application to access your Gmail."
    )

    if st.button(
        "Connect Gmail",
        type="primary"
    ):
        st.login()

    st.info(
        "You must connect Gmail before analyzing emails."
    )

    st.stop()


# =========================================================
# USER IS CONNECTED
# =========================================================

st.success("Gmail connected.")

user_email = getattr(
    st.user,
    "email",
    ""
)

if user_email:
    st.write(
        f"Connected account: **{user_email}**"
    )


if st.button("Disconnect Gmail"):

    st.session_state.clear()

    st.logout()


# =========================================================
# SESSION STATE
# =========================================================

if "emails" not in st.session_state:
    st.session_state.emails = []

if "stats" not in st.session_state:
    st.session_state.stats = {}


# =========================================================
# HEADER HELPER
# =========================================================

def get_header(headers, name):

    return next(
        (
            h["value"]
            for h in headers
            if h["name"].lower()
            == name.lower()
        ),
        ""
    )


# =========================================================
# DECODE GMAIL BODY
# =========================================================

def decode_body(data):

    if not data:
        return ""

    try:

        return base64.urlsafe_b64decode(
            data
        ).decode(
            "utf-8",
            errors="ignore"
        )

    except Exception:

        return ""


# =========================================================
# CLEAN HTML EMAIL
# =========================================================

def clean_html_email(html_content):

    if not html_content:
        return ""

    text = re.sub(
        r"<script.*?>.*?</script>",
        "",
        html_content,
        flags=re.IGNORECASE | re.DOTALL
    )

    text = re.sub(
        r"<style.*?>.*?</style>",
        "",
        text,
        flags=re.IGNORECASE | re.DOTALL
    )

    text = re.sub(
        r"<br\s*/?>",
        "\n",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"</p\s*>",
        "\n\n",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"</div\s*>",
        "\n",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"</li\s*>",
        "\n",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"<[^>]+>",
        "",
        text
    )

    text = html.unescape(text)

    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )

    text = re.sub(
        r"\n\s*\n\s*\n+",
        "\n\n",
        text
    )

    return text.strip()


# =========================================================
# EXTRACT EMAIL BODY
# =========================================================

def extract_email_body(payload):

    plain_text_parts = []
    html_parts = []

    def walk_parts(part):

        mime_type = part.get(
            "mimeType",
            ""
        )

        body_data = part.get(
            "body",
            {}
        ).get(
            "data"
        )

        if (
            mime_type == "text/plain"
            and body_data
        ):

            decoded = decode_body(
                body_data
            )

            if decoded:
                plain_text_parts.append(
                    decoded
                )

        elif (
            mime_type == "text/html"
            and body_data
        ):

            decoded = decode_body(
                body_data
            )

            if decoded:
                html_parts.append(
                    decoded
                )

        for child_part in part.get(
            "parts",
            []
        ):
            walk_parts(child_part)

    walk_parts(payload)

    if plain_text_parts:

        return "\n\n".join(
            plain_text_parts
        ).strip()

    if html_parts:

        combined_html = "\n".join(
            html_parts
        )

        return clean_html_email(
            combined_html
        )

    body_data = payload.get(
        "body",
        {}
    ).get(
        "data"
    )

    if body_data:

        decoded = decode_body(
            body_data
        )

        if (
            payload.get("mimeType")
            == "text/html"
        ):
            return clean_html_email(
                decoded
            )

        return decoded.strip()

    return ""


# =========================================================
# ATTACHMENT DETECTION
# =========================================================

def has_attachment(payload):

    for part in payload.get(
        "parts",
        []
    ):

        if part.get("filename"):
            return True

        if has_attachment(part):
            return True

    return False


# =========================================================
# FORMAT JEV CONFIDENCE
# =========================================================

def format_confidence(value):

    if value is None:
        return "Unknown"

    try:
        return f"{float(value):.3f}"

    except (
        TypeError,
        ValueError
    ):
        return "Unknown"


# =========================================================
# FORMAT JEV SCORE
# =========================================================

def format_score(value):

    if value is None:
        return "Unknown"

    try:
        return f"{float(value):.2f}"

    except (
        TypeError,
        ValueError
    ):
        return "Unknown"


# =========================================================
# SPAM ELIGIBILITY RULE
#
# Classification = Spam
# AND
# Spam Evidence = High or Very High
#
# Confidence is informational only.
# =========================================================

def eligible_for_spam_move(row):

    try:

        classification = str(
            row["Classification"]
        ).strip().lower()

        spam_evidence = str(
            row["Spam Evidence"]
        ).strip().lower()

        return (
            classification == "spam"
            and spam_evidence in [
                "high",
                "very high"
            ]
        )

    except (
        ValueError,
        TypeError,
        KeyError
    ):
        return False


# =========================================================
# MOVE MESSAGE TO GMAIL SPAM
# =========================================================

def move_message_to_spam(
    gmail_service,
    message_id
):

    gmail_service.users().messages().modify(
        userId="me",
        id=message_id,
        body={
            "addLabelIds": [
                "SPAM"
            ],
            "removeLabelIds": [
                "INBOX"
            ]
        }
    ).execute()


# =========================================================
# EMAIL SETTINGS
# =========================================================

st.divider()

st.subheader("Email Settings")

email_count = st.number_input(
    "Number of emails to analyze",
    min_value=1,
    max_value=125,
    value=20,
    step=5,
    help="Choose between 1 and 125 Inbox emails."
)

st.caption(
    "You can analyze up to 125 Inbox emails. "
    "More emails require more Jev processing "
    "time and API usage."
)


# =========================================================
# LOAD EMAILS
# =========================================================

if st.button(
    "Load Emails",
    type="primary"
):

    try:

        start_time = time.perf_counter()

        service = get_gmail_service()

        if service is None:

            st.error(
                "Could not connect to Gmail."
            )

            st.stop()


        results = (
            service.users()
            .messages()
            .list(
                userId="me",
                labelIds=["INBOX"],
                maxResults=int(email_count)
            )
            .execute()
        )

        messages = results.get(
            "messages",
            []
        )

        email_rows = []


        # =================================================
        # PROCESS EACH EMAIL
        # =================================================

        for item in messages:

            message_id = item["id"]

            message = (
                service.users()
                .messages()
                .get(
                    userId="me",
                    id=message_id,
                    format="full"
                )
                .execute()
            )

            payload = message.get(
                "payload",
                {}
            )

            headers = payload.get(
                "headers",
                []
            )


            # ---------------------------------------------
            # Sender
            # ---------------------------------------------

            from_header = get_header(
                headers,
                "From"
            )

            sender_name, sender_email = (
                parseaddr(from_header)
            )

            if not sender_name:
                sender_name = sender_email


            # ---------------------------------------------
            # Subject
            # ---------------------------------------------

            subject = get_header(
                headers,
                "Subject"
            )

            if not subject:
                subject = "(No Subject)"


            # ---------------------------------------------
            # Date
            # ---------------------------------------------

            date_header = get_header(
                headers,
                "Date"
            )

            try:

                email_date = (
                    parsedate_to_datetime(
                        date_header
                    )
                )

                date_display = (
                    email_date.strftime(
                        "%b %d, %Y %I:%M %p"
                    )
                )

            except Exception:

                date_display = date_header


            # ---------------------------------------------
            # Gmail labels
            # ---------------------------------------------

            labels = message.get(
                "labelIds",
                []
            )

            priority = (
                "⭐ Important"
                if "IMPORTANT" in labels
                else ""
            )


            # ---------------------------------------------
            # Attachment
            # ---------------------------------------------

            attachment = (
                "📎 Yes"
                if has_attachment(payload)
                else ""
            )


            # ---------------------------------------------
            # Email body
            # ---------------------------------------------

            body = extract_email_body(
                payload
            )


            # ---------------------------------------------
            # Jev analysis
            # ---------------------------------------------

            jev_result = classify_email(
                sender_email,
                subject,
                body
            )

            classification = (
                jev_result[
                    "classification"
                ]
            )

            classification_display = (
                str(classification)
                .replace("_", " ")
                .title()
            )

            confidence = format_confidence(
                jev_result[
                    "confidence"
                ]
            )


            # ---------------------------------------------
            # Store result
            # ---------------------------------------------

            email_rows.append(
                {
                    "Gmail Message ID":
                        message_id,

                    "Date":
                        date_display,

                    "From":
                        sender_name,

                    "Email":
                        sender_email,

                    "Subject":
                        subject,

                    "Priority":
                        priority,

                    "Attachment":
                        attachment,

                    "Classification":
                        classification_display,

                    "Confidence":
                        confidence,

                    "Spam Evidence":
                        jev_result[
                            "spam_evidence"
                        ],

                    "Spam Evidence Score":
                        jev_result[
                            "spam_evidence_score"
                        ],

                    "Legitimacy Evidence":
                        jev_result[
                            "legitimacy_evidence"
                        ],

                    "Legitimacy Evidence Score":
                        jev_result[
                            "legitimacy_evidence_score"
                        ],

                    "Sender Suspicion":
                        jev_result[
                            "sender_suspicion"
                        ],

                    "Sender Suspicion Score":
                        jev_result[
                            "sender_suspicion_score"
                        ],

                    "Subject Spam Signals":
                        jev_result[
                            "subject_spam_signals"
                        ],

                    "Subject Spam Signals Score":
                        jev_result[
                            "subject_spam_signals_score"
                        ],

                    "Body Intent":
                        jev_result[
                            "body_intent"
                        ],

                    "Body Intent Score":
                        jev_result[
                            "body_intent_score"
                        ],

                    "Links / CTA":
                        jev_result[
                            "links_cta"
                        ],

                    "Links / CTA Score":
                        jev_result[
                            "links_cta_score"
                        ],

                    "Urgency":
                        jev_result[
                            "urgency"
                        ],

                    "Urgency Score":
                        jev_result[
                            "urgency_score"
                        ],

                    "Promotional Signals":
                        jev_result[
                            "promotional"
                        ],

                    "Promotional Signals Score":
                        jev_result[
                            "promotional_score"
                        ],

                    "Sender Consistency":
                        jev_result[
                            "sender_consistency"
                        ],

                    "Sender Consistency Score":
                        jev_result[
                            "sender_consistency_score"
                        ],

                    "Expected Context":
                        jev_result[
                            "expected_context"
                        ],

                    "Expected Context Score":
                        jev_result[
                            "expected_context_score"
                        ],

                    "Transactional Purpose":
                        jev_result[
                            "transactional_purpose"
                        ],

                    "Transactional Purpose Score":
                        jev_result[
                            "transactional_purpose_score"
                        ],

                    "Content Consistency":
                        jev_result[
                            "content_consistency"
                        ],

                    "Content Consistency Score":
                        jev_result[
                            "content_consistency_score"
                        ],

                    "Link Consistency":
                        jev_result[
                            "link_consistency"
                        ],

                    "Link Consistency Score":
                        jev_result[
                            "link_consistency_score"
                        ],

                    "Communication Pattern":
                        jev_result[
                            "communication_pattern"
                        ],

                    "Communication Pattern Score":
                        jev_result[
                            "communication_pattern_score"
                        ],

                    "Body":
                        body
                }
            )


        # =================================================
        # PROCESSING STATS
        # =================================================

        processing_time = (
            time.perf_counter()
            - start_time
        )

        st.session_state.emails = (
            email_rows
        )

        st.session_state.stats = {
            "Processing Time":
                f"{processing_time:.2f} sec",

            "Emails Requested":
                int(email_count),

            "Emails Analyzed":
                len(email_rows),

            "Model":
                "Jev"
        }


    except Exception as e:

        st.error(
            f"Error processing emails: {e}"
        )


# =========================================================
# DISPLAY RESULTS
# =========================================================

if st.session_state.emails:

    st.success(
        f"Loaded and analyzed "
        f"{len(st.session_state.emails)} emails."
    )


    # -----------------------------------------------------
    # Processing summary
    # -----------------------------------------------------

    st.subheader(
        "AI Processing Summary"
    )

    stats_df = pd.DataFrame(
        [
            st.session_state.stats
        ]
    )

    st.dataframe(
        stats_df,
        use_container_width=True,
        hide_index=True
    )


    # -----------------------------------------------------
    # Email analysis
    # -----------------------------------------------------

    st.subheader(
        "Email Analysis"
    )

    st.caption(
        "Select an email to see Jev's detailed "
        "ordered-rubric assessment and the full email."
    )

    full_df = pd.DataFrame(
        st.session_state.emails
    )

    display_df = full_df[
        [
            "Date",
            "From",
            "Email",
            "Subject",
            "Priority",
            "Attachment",
            "Classification",
            "Confidence",
            "Spam Evidence",
            "Legitimacy Evidence"
        ]
    ]


    event = st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",

        column_config={
            "Date":
                st.column_config.TextColumn(
                    "Date"
                ),

            "From":
                st.column_config.TextColumn(
                    "From"
                ),

            "Email":
                st.column_config.TextColumn(
                    "Email Address"
                ),

            "Subject":
                st.column_config.TextColumn(
                    "Subject",
                    width="large"
                ),

            "Priority":
                st.column_config.TextColumn(
                    "Priority"
                ),

            "Attachment":
                st.column_config.TextColumn(
                    "Attached"
                ),

            "Classification":
                st.column_config.TextColumn(
                    "Spam"
                ),

            "Confidence":
                st.column_config.TextColumn(
                    "Confidence"
                ),

            "Spam Evidence":
                st.column_config.TextColumn(
                    "Spam Evidence"
                ),

            "Legitimacy Evidence":
                st.column_config.TextColumn(
                    "Legitimacy Evidence"
                )
        }
    )


    # =====================================================
    # SPAM ACTION
    # =====================================================

    eligible_spam = full_df[
        full_df.apply(
            eligible_for_spam_move,
            axis=1
        )
    ]


    if not eligible_spam.empty:

        st.divider()

        st.subheader(
            "High Spam Evidence"
        )

        st.warning(
            f"{len(eligible_spam)} email(s) meet "
            f"the rule for moving to Gmail Spam."
        )

        st.caption(
            "Rule: Jev Classification = Spam "
            "and Spam Evidence = High or Very High. "
            "Confidence is shown for information only."
        )


        spam_preview = eligible_spam[
            [
                "From",
                "Email",
                "Subject",
                "Classification",
                "Confidence",
                "Spam Evidence",
                "Legitimacy Evidence"
            ]
        ]

        st.dataframe(
            spam_preview,
            use_container_width=True,
            hide_index=True
        )


        confirm_spam_move = st.checkbox(
            "I reviewed these emails and want to "
            "move them to Gmail Spam."
        )


        if st.button(
            "Move Spam Emails to Gmail Spam",
            type="primary",
            disabled=not confirm_spam_move
        ):

            gmail_service = (
                get_gmail_service()
            )

            moved_ids = []
            failed_emails = []


            for _, email_row in (
                eligible_spam.iterrows()
            ):

                message_id = email_row[
                    "Gmail Message ID"
                ]

                try:

                    move_message_to_spam(
                        gmail_service,
                        message_id
                    )

                    moved_ids.append(
                        message_id
                    )

                except Exception as e:

                    failed_emails.append(
                        {
                            "subject":
                                email_row[
                                    "Subject"
                                ],

                            "error":
                                str(e)
                        }
                    )


            if moved_ids:

                moved_id_set = set(
                    moved_ids
                )

                st.session_state.emails = [
                    email_row

                    for email_row
                    in st.session_state.emails

                    if email_row[
                        "Gmail Message ID"
                    ] not in moved_id_set
                ]


            for failure in failed_emails:

                st.error(
                    f"Could not move "
                    f"'{failure['subject']}' to Spam: "
                    f"{failure['error']}"
                )


            if moved_ids:

                st.success(
                    f"{len(moved_ids)} email(s) "
                    f"successfully moved to Gmail Spam."
                )


            if failed_emails:

                st.warning(
                    f"{len(failed_emails)} email(s) "
                    f"could not be moved."
                )


            if (
                moved_ids
                and not failed_emails
            ):

                time.sleep(1)

                st.rerun()


    else:

        st.info(
            "No emails currently meet the Spam rule: "
            "Classification = Spam and "
            "Spam Evidence = High or Very High."
        )


    # =====================================================
    # SELECTED EMAIL
    # =====================================================

    if event.selection.rows:

        selected_row = (
            event.selection.rows[0]
        )

        if selected_row < len(
            full_df
        ):

            selected_email = (
                full_df.iloc[
                    selected_row
                ]
            )

            st.divider()

            st.header(
                selected_email[
                    "Subject"
                ]
            )

            st.write(
                f"**From:** "
                f"{selected_email['From']} "
                f"<{selected_email['Email']}>"
            )

            st.write(
                f"**Date:** "
                f"{selected_email['Date']}"
            )


            # ---------------------------------------------
            # Jev summary
            # ---------------------------------------------

            st.subheader(
                "Jev Classification"
            )

            col1, col2, col3, col4 = (
                st.columns(4)
            )


            with col1:

                st.metric(
                    "Classification",
                    selected_email[
                        "Classification"
                    ]
                )


            with col2:

                st.metric(
                    "Confidence",
                    selected_email[
                        "Confidence"
                    ]
                )


            with col3:

                st.metric(
                    "Spam Evidence",
                    selected_email[
                        "Spam Evidence"
                    ]
                )


            with col4:

                st.metric(
                    "Legitimacy Evidence",
                    selected_email[
                        "Legitimacy Evidence"
                    ]
                )


            st.caption(
                "Jev scores are positions on an ordered "
                "rubric, not percentages. Classification "
                "confidence is displayed for information "
                "but is not used in the Gmail Spam rule."
            )


            score_col1, score_col2 = (
                st.columns(2)
            )


            with score_col1:

                st.write(
                    "**Spam Evidence Raw Score:** "
                    + format_score(
                        selected_email[
                            "Spam Evidence Score"
                        ]
                    )
                )


            with score_col2:

                st.write(
                    "**Legitimacy Evidence Raw Score:** "
                    + format_score(
                        selected_email[
                            "Legitimacy Evidence Score"
                        ]
                    )
                )


            # =============================================
            # DETAILED EVIDENCE
            # =============================================

            st.subheader(
                "Why Jev Scored This Email"
            )


            # ---------------------------------------------
            # Spam evidence
            # ---------------------------------------------

            st.markdown(
                "### Spam Evidence"
            )

            spam_details = pd.DataFrame(
                [
                    {
                        "Evidence Signal":
                            "Sender Suspicion",

                        "Jev Rubric":
                            selected_email[
                                "Sender Suspicion"
                            ],

                        "Raw Score":
                            format_score(
                                selected_email[
                                    "Sender Suspicion Score"
                                ]
                            )
                    },

                    {
                        "Evidence Signal":
                            "Subject Spam Signals",

                        "Jev Rubric":
                            selected_email[
                                "Subject Spam Signals"
                            ],

                        "Raw Score":
                            format_score(
                                selected_email[
                                    "Subject Spam Signals Score"
                                ]
                            )
                    },

                    {
                        "Evidence Signal":
                            "Body / Intent",

                        "Jev Rubric":
                            selected_email[
                                "Body Intent"
                            ],

                        "Raw Score":
                            format_score(
                                selected_email[
                                    "Body Intent Score"
                                ]
                            )
                    },

                    {
                        "Evidence Signal":
                            "Links / CTA",

                        "Jev Rubric":
                            selected_email[
                                "Links / CTA"
                            ],

                        "Raw Score":
                            format_score(
                                selected_email[
                                    "Links / CTA Score"
                                ]
                            )
                    },

                    {
                        "Evidence Signal":
                            "Urgency / Pressure",

                        "Jev Rubric":
                            selected_email[
                                "Urgency"
                            ],

                        "Raw Score":
                            format_score(
                                selected_email[
                                    "Urgency Score"
                                ]
                            )
                    },

                    {
                        "Evidence Signal":
                            "Promotional Signals",

                        "Jev Rubric":
                            selected_email[
                                "Promotional Signals"
                            ],

                        "Raw Score":
                            format_score(
                                selected_email[
                                    "Promotional Signals Score"
                                ]
                            )
                    }
                ]
            )

            st.dataframe(
                spam_details,
                use_container_width=True,
                hide_index=True
            )


            # ---------------------------------------------
            # Legitimacy evidence
            # ---------------------------------------------

            st.markdown(
                "### Legitimacy Evidence"
            )

            legitimacy_details = pd.DataFrame(
                [
                    {
                        "Evidence Signal":
                            "Sender Consistency",

                        "Jev Rubric":
                            selected_email[
                                "Sender Consistency"
                            ],

                        "Raw Score":
                            format_score(
                                selected_email[
                                    "Sender Consistency Score"
                                ]
                            )
                    },

                    {
                        "Evidence Signal":
                            "Expected Context",

                        "Jev Rubric":
                            selected_email[
                                "Expected Context"
                            ],

                        "Raw Score":
                            format_score(
                                selected_email[
                                    "Expected Context Score"
                                ]
                            )
                    },

                    {
                        "Evidence Signal":
                            "Transactional Purpose",

                        "Jev Rubric":
                            selected_email[
                                "Transactional Purpose"
                            ],

                        "Raw Score":
                            format_score(
                                selected_email[
                                    "Transactional Purpose Score"
                                ]
                            )
                    },

                    {
                        "Evidence Signal":
                            "Content Consistency",

                        "Jev Rubric":
                            selected_email[
                                "Content Consistency"
                            ],

                        "Raw Score":
                            format_score(
                                selected_email[
                                    "Content Consistency Score"
                                ]
                            )
                    },

                    {
                        "Evidence Signal":
                            "Link Consistency",

                        "Jev Rubric":
                            selected_email[
                                "Link Consistency"
                            ],

                        "Raw Score":
                            format_score(
                                selected_email[
                                    "Link Consistency Score"
                                ]
                            )
                    },

                    {
                        "Evidence Signal":
                            "Communication Pattern",

                        "Jev Rubric":
                            selected_email[
                                "Communication Pattern"
                            ],

                        "Raw Score":
                            format_score(
                                selected_email[
                                    "Communication Pattern Score"
                                ]
                            )
                    }
                ]
            )

            st.dataframe(
                legitimacy_details,
                use_container_width=True,
                hide_index=True
            )


            # ---------------------------------------------
            # Priority / attachment
            # ---------------------------------------------

            if selected_email[
                "Priority"
            ]:

                st.write(
                    f"**Priority:** "
                    f"{selected_email['Priority']}"
                )


            if selected_email[
                "Attachment"
            ]:

                st.write(
                    f"**Attachment:** "
                    f"{selected_email['Attachment']}"
                )


            # =============================================
            # FULL EMAIL
            # =============================================

            st.divider()

            st.subheader(
                "Full Email"
            )

            body = selected_email[
                "Body"
            ]

            if body:

                st.text_area(
                    "Email Body",
                    value=body,
                    height=500,
                    disabled=True
                )

            else:

                st.info(
                    "No readable email body was found."
                )