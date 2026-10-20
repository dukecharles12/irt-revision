# IRT Revision Desk

Revision app for the CISI Investment, Risk & Taxation exam, served with Streamlit.

- `irt-revision.html` is the whole app (topics, flashcards, quizzes, number practice, calculators).
- `streamlit_app.py` shows it full screen and syncs your progress.
- `sync_bridge.js` connects the page to the sync.

## Sync between devices

Scores, weak spots and your own questions are always saved in the browser you use.
To see the same progress on every device, the app also keeps a copy in a private GitHub gist:

1. Create a GitHub token at https://github.com/settings/tokens/new with only the **gist** scope ticked.
2. In Streamlit, open the app's **Settings → Secrets** and add:

       GITHUB_TOKEN = "your-token-here"

3. Save. The label at the top right of the app changes to "Synced across your devices".

Without the token the app still works, but progress stays in each browser.

## Run locally

    pip install -r requirements.txt
    streamlit run streamlit_app.py

To sync to a local file instead of a gist, set `IRT_PROGRESS_FILE=/path/to/progress.json`.
