# Multimodal Classroom Attendance & Engagement Agent (Phase 1)

An offline, privacy-first classroom attendance and observable-engagement analytics platform built with Python and Streamlit.

> **Note on Engagement Metrics**: Engagement indicators in this application are observable heuristics (e.g., presence, posture, orientation), and are not treated as direct measures of internal emotions or cognitive learning.

---

## 🚀 Features (Phase 1)

- **Local SQLite Database**: Privacy-preserving local storage for students, sessions, and attendance logs.
- **Interactive Dashboard**: Modern Streamlit-based UI with key metrics, attendance rates, session breakdowns, and engagement scores.
- **Visual Analytics**: Interactive Plotly charts for session-by-session trends and student rosters.
- **Synthetic/Demo Sessions**: Ability to toggle synthetic demo sessions for testing and demonstrations.
- **Privacy First**: Fully offline architecture; student data, faces, and logs are kept strictly local.

---

## 📁 Project Structure

```text
multimodal-attendance-agent/
├── .streamlit/             # Streamlit configuration
├── data/                   # Local databases and student assets (.gitignored)
│   ├── database/           # SQLite database directory
│   ├── sessions/           # Recorded session logs
│   └── students/           # Registered student files
├── pages/                  # Streamlit multi-page app screens
├── src/
│   ├── database/           # Database schema, models, and queries
│   └── utils/              # UI helpers and formatting utilities
├── tests/                  # Unit and integration tests
├── app.py                  # Streamlit dashboard entry point
├── config.py               # Application configuration
├── pytest.ini              # Pytest configuration
└── requirements.txt        # Project dependencies
```

---

## 🛠️ Setup & Installation

### 1. Clone the Repository

```bash
git clone https://github.com/suyashverma16/multimodal-attendance-agent-.git
cd multimodal-attendance-agent-
```

### 2. Create and Activate a Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 🏃 Running the Application

Launch the Streamlit web dashboard:

```bash
streamlit run app.py
```

The application will be accessible at `http://localhost:8501`.

---

## 🧪 Running Tests

To run the automated test suite:

```bash
pytest
```

---

## 🔒 Privacy & Data Protection

- All data stored in `data/` is excluded from version control via `.gitignore`.
- No telemetry, cloud uploads, or external API calls are made.
