# Gmail setup

Aeris uses official Google OAuth. It does not use or store your Gmail password.

1. Open Google Cloud Console and create or select a project.
2. Enable the Gmail API.
3. Configure the OAuth consent screen for an external desktop application.
4. Add your own Google account as a test user while the app is in testing mode.
5. Create an OAuth Client ID with application type **Desktop app**.
6. Download the client JSON file.
7. Rename it to `credentials.json` and place it in the Aeris project root.
8. Do not commit this file to GitHub.
9. Run Aeris and say `check my emails`.
10. Approve the session permission in Aeris, then complete Google's browser consent.

The OAuth token is stored in Windows Credential Manager. Sending an email still requires a separate Aeris confirmation every time.

Example command:

```text
send email to professor@example.com subject Assignment update message I will submit the assignment tomorrow.
```
