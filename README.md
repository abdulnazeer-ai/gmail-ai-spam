# Gmail AI Spam Detector

A self-directed AI proof-of-concept that connects to Gmail and uses Jev's Structured Decision Model to analyze emails for spam and legitimacy signals.

This project demonstrates a simple but powerful example of how Jev's Structured Decision Model can be used in a real-world application.

## What It Does

The application:

- Connects to a user's Gmail account using Google OAuth.
- Reads emails from the user's Inbox.
- Uses Jev to analyze each email.
- Classifies emails as Spam, Safe, or Uncertain.
- Provides structured spam and legitimacy evidence.
- Displays the analysis in a Streamlit interface.
- Allows the user to review the results before any Gmail action is taken.
- Moves eligible emails to Gmail Spam only after explicit user confirmation.

## Architecture

```text
Gmail
  |
  v
Python Application
  |
  v
Email Content
  |
  v
Jev Structured Decision Model
  |
  v
Structured Classification + Evidence
  |
  v
Deterministic Python Rules
  |
  v
Human Review
  |
  v
Gmail Action
```

The AI provides structured analysis, while deterministic Python rules control which actions are permitted.

The user remains in control of the final Gmail action.

## Structured Decision Model

Instead of relying only on free-form generated text, the application uses Jev to return structured decisions that the software can use directly.

For each email, the application evaluates signals such as:

- Sender suspicion
- Subject spam signals
- Body intent
- Links and calls to action
- Urgency
- Promotional content
- Sender consistency
- Expected context
- Transactional purpose
- Content consistency
- Link consistency
- Communication pattern

The application displays:

- Classification
- Confidence
- Spam Evidence
- Legitimacy Evidence

Confidence is displayed for informational purposes only and is not used to determine the Gmail action.

## Gmail Action Rule

An email becomes eligible to be moved to Spam only when:

```text
Classification = Spam
AND
Spam Evidence = High or Very High
```

Even when these conditions are met, the application does not automatically move the email.

The user must review the result, explicitly confirm the action, and then initiate the move to Gmail Spam.

## AI Safety and Human Oversight

The project intentionally separates AI analysis from application actions.

```text
AI Analysis
     |
     v
Deterministic Rule
     |
     v
Human Review
     |
     v
Gmail Action
```

This means:

- AI analyzes the email.
- Python applies deterministic business rules.
- The user reviews the result.
- The user makes the final decision before an email is moved to Spam.

This human-in-the-loop approach helps reduce the risk of automatically acting on an incorrect AI classification.

## Technology

- Python
- Streamlit
- Jev / TypeSafe AI
- Gmail API
- Google OAuth 2.0
- Pandas
- python-dotenv

## Project Structure

```text
gmail-ai-spam/
│
├── .streamlit/
│   └── secrets.toml       # Local only / not committed
├── .venv/                 # Local only / not committed
├── .env                   # Local only / not committed
├── .env.example
├── .gitignore
├── README.md
├── app.py
├── ai_classifier.py
├── gmail_service.py
└── requirements.txt
```

Sensitive local files such as `.env` and `.streamlit/secrets.toml` are excluded from GitHub.

## Local Setup

### 1. Clone the repository

```bash
git clone https://github.com/abdulnazeer-ai/gmail-ai-spam.git
cd gmail-ai-spam
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

### 3. Activate the virtual environment

On Windows Command Prompt:

```cmd
.venv\Scripts\activate.bat
```

On Windows PowerShell, if script execution is enabled:

```powershell
.venv\Scripts\Activate.ps1
```

### 4. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 5. Configure the TypeSafe / Jev API key

Create a `.env` file:

```text
TYPESAFE_API_KEY=your_typesafe_api_key_here
```

Do not commit the `.env` file to GitHub.

### 6. Configure Google OAuth

The application uses Google OAuth and Streamlit authentication to connect to Gmail.

Configure the appropriate Google OAuth client and store the local authentication configuration in:

```text
.streamlit/secrets.toml
```

OAuth credentials and secrets should never be committed to the repository.

### 7. Run the application

```bash
streamlit run app.py
```

## Email Data Used for AI Analysis

For the AI analysis, the application sends the following email information to Jev:

- Sender email address
- Subject
- First 6,000 characters of the extracted email body

The 6,000-character limit is an initial design choice intended to control input size and latency and can be tuned based on testing and classification accuracy.

Google credentials, OAuth tokens, and Gmail authentication information are not included in the email content sent for classification.

## Current Project Scope

This is a self-directed proof-of-concept project intended to demonstrate:

- Practical AI integration
- Structured AI decision making
- Gmail API integration
- Google OAuth authentication
- Deterministic business rules
- Human-in-the-loop AI workflows
- Streamlit application development

It is not intended to represent a production-ready enterprise spam filtering system.

Additional security controls, testing, monitoring, logging, allowlists, model evaluation, and operational safeguards would be required for production use.

## Privacy and Secrets

The GitHub repository does not include:

- Gmail OAuth tokens
- Google client secrets
- Jev / TypeSafe API keys
- User email data

Sensitive credentials are stored locally or through Streamlit's secrets configuration and are excluded from Git.

## Live Application

**Gmail Spam Classifier — Jev**

https://gmail-spam-classifier-jev.streamlit.app/

## GitHub Repository

https://github.com/abdulnazeer-ai/gmail-ai-spam

## Author

**Abdul Nazeer**

Self-directed AI proof-of-concept project.