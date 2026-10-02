# HDFC LLM pipeline: codebase guide

A phone-friendly website that explains every file of the
[HDFC custom LLM pipeline](https://github.com/pranatipradhanwork-alt/Hdfc-bank-custom-llm-pipeline-project):
folder tree, what each file does, its key functions with line numbers, the full code, a demo Q&A cheat sheet,
a glossary, and search across all of it.

Open `index.html` in a browser, or the GitHub Pages site of this repository.

## Update it after the project changes

```bash
python build.py ../Hdfc-bank-custom-llm-pipeline-project
```

This exports the committed `origin/main` of the project (never local or secret files), combines it with the
explanations in `notes.py`, and writes `data.js`. Edit `notes.py` to change or add explanations.
