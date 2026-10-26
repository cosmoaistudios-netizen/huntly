# 🤝 Contributing to Huntly

Thank you for your interest in contributing to **Huntly**! We welcome bug fixes, documentation improvements, new scraper integrations, and UX enhancements.

---

## 🛠️ Local Development Setup

### 1. Prerequisites
- Python 3.9, 3.10, 3.11, or 3.12
- Git

### 2. Fork and Clone
```bash
git clone https://github.com/<your-username>/huntly.git
cd huntly
```

### 3. Create a Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 4. Running the Development Sandbox
You can run Huntly without paid API keys using the offline demo sandbox:
```bash
python3 -m huntly.cli demo
```

To run with real live APIs:
```bash
cp .env.example .env
# Fill in your RAPIDAPI_KEY and NVIDIA_API_KEY in .env
python3 -m huntly.cli ui
```

---

## 🧪 Testing & Code Quality

Run tests and code formatting checks before opening a Pull Request:
```bash
pytest tests/
ruff check .
```

---

## 📝 Pull Request Guidelines

1. **Create a branch**: `git checkout -b feat/your-feature-name` or `fix/issue-description`.
2. **Keep PRs focused**: Each PR should address a single feature or bug.
3. **Preserve credential security**: Never commit API keys or private databases. Verify `.gitignore` matches your changes.
4. **Follow conventions**:
   - Write clear docstrings and maintain type annotations.
   - For UI components, adhere to Textual TUI paradigms and async event workers.

---

## 💬 Community & Questions
Feel free to open an Issue on GitHub for questions, architectural discussions, or feature suggestions.
