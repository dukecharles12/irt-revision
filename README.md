# IRT Revision Desk

Revision app for the CISI Investment, Risk & Taxation exam, served with Streamlit.

- `irt-revision.html` is the whole app (topics, flashcards, quizzes, number practice, calculators).
- `streamlit_app.py` shows it full screen.
- Scores, weak spots and your own questions are saved in the browser you use.

## Run locally

    pip install -r requirements.txt
    streamlit run streamlit_app.py

## Deploy

1. Push this folder to a GitHub repository.
2. Go to https://share.streamlit.io, sign in with GitHub, choose **Create app**, pick the repository, and set the main file to `streamlit_app.py`.
