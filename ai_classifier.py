import os

from dotenv import load_dotenv
from typesafe_sdk import Choice, Score, TypeSafeClient


# ---------------------------------------------------------
# Load environment variables
# ---------------------------------------------------------

load_dotenv()

api_key = os.getenv("TYPESAFE_API_KEY")

if not api_key:
    raise ValueError(
        "TYPESAFE_API_KEY was not found in the .env file."
    )


# ---------------------------------------------------------
# Rubric labels
# Jev Score criteria are ordered:
# 0 = Very Low
# 1 = Low
# 2 = Medium
# 3 = High
# 4 = Very High
# ---------------------------------------------------------

RUBRIC_LABELS = [
    "Very Low",
    "Low",
    "Medium",
    "High",
    "Very High"
]


# ---------------------------------------------------------
# Convert Jev's continuous ordered score to nearest
# human-readable rubric level for display.
#
# IMPORTANT:
# We still keep the original Jev score separately.
# ---------------------------------------------------------

def score_to_level(value):

    if value is None:
        return "Unknown"

    try:
        value = float(value)

        if value < 0.5:
            return "Very Low"
        elif value < 1.5:
            return "Low"
        elif value < 2.5:
            return "Medium"
        elif value < 3.5:
            return "High"
        else:
            return "Very High"

    except (TypeError, ValueError):
        return "Unknown"


# ---------------------------------------------------------
# Reusable ordered rubric
# ---------------------------------------------------------

def simple_rubric(topic):

    return [
        f"Very Low: Almost no {topic} evidence is present.",
        f"Low: Weak {topic} evidence is present.",
        f"Medium: Meaningful {topic} evidence is present, "
        f"but the evidence is mixed.",
        f"High: Strong {topic} evidence is present.",
        f"Very High: Multiple strong and reinforcing "
        f"{topic} signals are present."
    ]


# ---------------------------------------------------------
# Main classifier
# ---------------------------------------------------------

def classify_email(sender, subject, body):

    # Keep complete body in app.py.
    # Only first 6,000 characters go to Jev for this POC.
    ai_body = (body or "")[:6000]

    email_state = {
        "sender": sender or "",
        "subject": subject or "",
        "body": ai_body
    }


    # -----------------------------------------------------
    # Questions sent to Jev
    # -----------------------------------------------------

    questions = {

        # =================================================
        # OVERALL CLASSIFICATION
        # =================================================

        "classification": Choice(

            instructions=(
                "Classify this email using only the supplied sender, "
                "subject, and body. Consider phishing, deception, "
                "unsolicited promotion, suspicious requests, urgency, "
                "expected business context, transactional purpose, "
                "and legitimacy signals. Do not assume that the "
                "sender or domain has been externally verified."
            ),

            criteria={

                "spam": (
                    "The email shows sufficient evidence of "
                    "unsolicited promotion, phishing, deception, "
                    "scam behavior, suspicious intent, or clearly "
                    "unwanted bulk email."
                ),

                "safe": (
                    "The email appears to be a legitimate personal, "
                    "business, transactional, account, security, "
                    "service, or otherwise expected communication."
                ),

                "uncertain": (
                    "The evidence is mixed or insufficient to "
                    "confidently classify the email as spam or safe."
                )
            }
        ),


        # =================================================
        # OVERALL SPAM EVIDENCE
        # =================================================

        "spam_evidence": Score(

            instructions=(
                "Rate the overall strength of spam evidence in this "
                "email. Consider sender suspicion, subject wording, "
                "body intent, suspicious links or calls to action, "
                "urgency, phishing signals, deception, and "
                "unsolicited promotional content."
            ),

            criteria=[
                (
                    "Very Low: Almost no meaningful spam, phishing, "
                    "deception, suspicious urgency, or unwanted "
                    "promotional evidence is present."
                ),
                (
                    "Low: Some weak spam-like characteristics exist, "
                    "but there is little evidence that the email is "
                    "actually spam."
                ),
                (
                    "Medium: Several meaningful spam characteristics "
                    "are present, but the evidence is mixed or "
                    "ambiguous."
                ),
                (
                    "High: Strong evidence of spam, phishing, "
                    "deception, unsolicited promotion, suspicious "
                    "calls to action, or manipulation is present."
                ),
                (
                    "Very High: Multiple strong and mutually "
                    "reinforcing spam or phishing signals are present "
                    "with little reasonable benign explanation."
                )
            ]
        ),


        # =================================================
        # OVERALL LEGITIMACY EVIDENCE
        # =================================================

        "legitimacy_evidence": Score(

            instructions=(
                "Rate the overall strength of legitimacy evidence. "
                "Consider sender consistency, expected relationship "
                "or context, transactional purpose, content "
                "consistency, link or call-to-action consistency "
                "when visible, and normal personal or business "
                "communication patterns. Do not claim external "
                "verification of the sender or domain."
            ),

            criteria=[
                (
                    "Very Low: Little evidence exists that the "
                    "message represents a legitimate or expected "
                    "communication."
                ),
                (
                    "Low: Some legitimacy indicators exist, but "
                    "sender, context, or purpose remain weak or "
                    "uncertain."
                ),
                (
                    "Medium: Meaningful legitimacy evidence exists, "
                    "but important uncertainties remain."
                ),
                (
                    "High: Strong evidence exists of a normal "
                    "expected, transactional, personal, account, "
                    "service, or business communication."
                ),
                (
                    "Very High: Multiple strong and internally "
                    "consistent legitimacy signals exist across "
                    "sender, context, purpose, content, and "
                    "requested action."
                )
            ]
        ),


        # =================================================
        # DETAILED SPAM SIGNALS
        # =================================================

        "sender_suspicion": Score(

            instructions=(
                "Rate sender or identity suspicion. Consider whether "
                "the visible sender appears inconsistent, misleading, "
                "unusual, or potentially impersonating another "
                "person or organization. Do not assume external "
                "domain verification."
            ),

            criteria=simple_rubric(
                "sender or identity suspicion"
            )
        ),


        "subject_spam_signals": Score(

            instructions=(
                "Rate spam-like signals in the subject. Consider "
                "misleading claims, prizes, suspicious urgency, "
                "manipulative wording, excessive promotion, or "
                "other characteristics commonly associated with "
                "spam or phishing."
            ),

            criteria=simple_rubric(
                "spam-like subject"
            )
        ),


        "body_intent": Score(

            instructions=(
                "Rate suspicious or spam-like intent in the email "
                "body. Consider deception, scams, suspicious "
                "requests, unwanted solicitation, phishing intent, "
                "or irrelevant bulk content."
            ),

            criteria=simple_rubric(
                "suspicious body intent"
            )
        ),


        "links_cta": Score(

            instructions=(
                "Rate suspicious link or call-to-action evidence "
                "using only information visible in the supplied "
                "email. Consider unusual clicking instructions, "
                "credential requests, payment requests, verification "
                "requests, or visible inconsistencies. Do not claim "
                "that a URL was externally verified."
            ),

            criteria=simple_rubric(
                "suspicious link or call-to-action"
            )
        ),


        "urgency": Score(

            instructions=(
                "Rate manipulative urgency or pressure. Consider "
                "artificial deadlines, threats, fear, account "
                "suspension warnings, financial pressure, or "
                "instructions to act immediately."
            ),

            criteria=simple_rubric(
                "manipulative urgency or pressure"
            )
        ),


        "promotional": Score(

            instructions=(
                "Rate unsolicited promotional evidence. Consider "
                "sales messages, discounts, prizes, giveaways, "
                "aggressive marketing, or bulk promotional content. "
                "Do not assume that all marketing email is malicious."
            ),

            criteria=simple_rubric(
                "unsolicited promotional"
            )
        ),


        # =================================================
        # DETAILED LEGITIMACY SIGNALS
        # =================================================

        "sender_consistency": Score(

            instructions=(
                "Rate how internally consistent the visible sender "
                "identity appears with the person or organization "
                "claimed in the email. Use only the supplied email "
                "information and do not claim external verification."
            ),

            criteria=simple_rubric(
                "sender consistency"
            )
        ),


        "expected_context": Score(

            instructions=(
                "Rate evidence that this is an expected communication "
                "based on the email itself. Consider evidence of an "
                "existing customer relationship, account, order, "
                "subscription, business interaction, colleague "
                "relationship, or prior context."
            ),

            criteria=simple_rubric(
                "expected communication context"
            )
        ),


        "transactional_purpose": Score(

            instructions=(
                "Rate evidence of a legitimate transactional or "
                "service purpose such as a receipt, order update, "
                "appointment, account notification, security notice, "
                "billing message, delivery update, or normal "
                "business communication."
            ),

            criteria=simple_rubric(
                "legitimate transactional or service purpose"
            )
        ),


        "content_consistency": Score(

            instructions=(
                "Rate the internal consistency between the visible "
                "sender, subject, body, claimed organization, "
                "message purpose, and requested action."
            ),

            criteria=simple_rubric(
                "internal content consistency"
            )
        ),


        "link_consistency": Score(

            instructions=(
                "Rate how consistent visible links or calls to action "
                "appear with the claimed sender and message purpose. "
                "Use only information actually visible in the email. "
                "Do not claim external URL or domain verification."
            ),

            criteria=simple_rubric(
                "link or call-to-action consistency"
            )
        ),


        "communication_pattern": Score(

            instructions=(
                "Rate how consistent the message is with a normal "
                "personal, business, transactional, account, or "
                "service communication pattern. Professional "
                "appearance alone is weak evidence because phishing "
                "emails can also look professional."
            ),

            criteria=simple_rubric(
                "normal communication pattern"
            )
        )
    }


    # -----------------------------------------------------
    # Call Jev
    # -----------------------------------------------------

    try:

        with TypeSafeClient(
            api_key=api_key
        ) as client:

            response = client.system_one(
                state=email_state,
                questions=questions
            )


        # -------------------------------------------------
        # Choice result
        # -------------------------------------------------

        classification_answer = response.choices[
            "classification"
        ]

        classification = classification_answer.choice
        confidence = classification_answer.confidence


        # -------------------------------------------------
        # Score results
        # -------------------------------------------------

        spam_score = response.scores[
            "spam_evidence"
        ].score

        legitimacy_score = response.scores[
            "legitimacy_evidence"
        ].score


        sender_suspicion_score = response.scores[
            "sender_suspicion"
        ].score

        subject_spam_score = response.scores[
            "subject_spam_signals"
        ].score

        body_intent_score = response.scores[
            "body_intent"
        ].score

        links_cta_score = response.scores[
            "links_cta"
        ].score

        urgency_score = response.scores[
            "urgency"
        ].score

        promotional_score = response.scores[
            "promotional"
        ].score


        sender_consistency_score = response.scores[
            "sender_consistency"
        ].score

        expected_context_score = response.scores[
            "expected_context"
        ].score

        transactional_purpose_score = response.scores[
            "transactional_purpose"
        ].score

        content_consistency_score = response.scores[
            "content_consistency"
        ].score

        link_consistency_score = response.scores[
            "link_consistency"
        ].score

        communication_pattern_score = response.scores[
            "communication_pattern"
        ].score


        # -------------------------------------------------
        # Return structured result
        # -------------------------------------------------

        return {

            "classification":
                classification,

            "confidence":
                confidence,


            # Overall scores
            "spam_evidence_score":
                spam_score,

            "spam_evidence":
                score_to_level(
                    spam_score
                ),

            "legitimacy_evidence_score":
                legitimacy_score,

            "legitimacy_evidence":
                score_to_level(
                    legitimacy_score
                ),


            # Detailed spam scores + labels
            "sender_suspicion_score":
                sender_suspicion_score,

            "sender_suspicion":
                score_to_level(
                    sender_suspicion_score
                ),

            "subject_spam_signals_score":
                subject_spam_score,

            "subject_spam_signals":
                score_to_level(
                    subject_spam_score
                ),

            "body_intent_score":
                body_intent_score,

            "body_intent":
                score_to_level(
                    body_intent_score
                ),

            "links_cta_score":
                links_cta_score,

            "links_cta":
                score_to_level(
                    links_cta_score
                ),

            "urgency_score":
                urgency_score,

            "urgency":
                score_to_level(
                    urgency_score
                ),

            "promotional_score":
                promotional_score,

            "promotional":
                score_to_level(
                    promotional_score
                ),


            # Detailed legitimacy scores + labels
            "sender_consistency_score":
                sender_consistency_score,

            "sender_consistency":
                score_to_level(
                    sender_consistency_score
                ),

            "expected_context_score":
                expected_context_score,

            "expected_context":
                score_to_level(
                    expected_context_score
                ),

            "transactional_purpose_score":
                transactional_purpose_score,

            "transactional_purpose":
                score_to_level(
                    transactional_purpose_score
                ),

            "content_consistency_score":
                content_consistency_score,

            "content_consistency":
                score_to_level(
                    content_consistency_score
                ),

            "link_consistency_score":
                link_consistency_score,

            "link_consistency":
                score_to_level(
                    link_consistency_score
                ),

            "communication_pattern_score":
                communication_pattern_score,

            "communication_pattern":
                score_to_level(
                    communication_pattern_score
                )
        }


    except Exception as e:

        print(
            f"Jev classification error: {e}"
        )

        return {

            "classification": "error",
            "confidence": None,

            "spam_evidence_score": None,
            "spam_evidence": "Unknown",

            "legitimacy_evidence_score": None,
            "legitimacy_evidence": "Unknown",

            "sender_suspicion_score": None,
            "sender_suspicion": "Unknown",

            "subject_spam_signals_score": None,
            "subject_spam_signals": "Unknown",

            "body_intent_score": None,
            "body_intent": "Unknown",

            "links_cta_score": None,
            "links_cta": "Unknown",

            "urgency_score": None,
            "urgency": "Unknown",

            "promotional_score": None,
            "promotional": "Unknown",

            "sender_consistency_score": None,
            "sender_consistency": "Unknown",

            "expected_context_score": None,
            "expected_context": "Unknown",

            "transactional_purpose_score": None,
            "transactional_purpose": "Unknown",

            "content_consistency_score": None,
            "content_consistency": "Unknown",

            "link_consistency_score": None,
            "link_consistency": "Unknown",

            "communication_pattern_score": None,
            "communication_pattern": "Unknown"
        }