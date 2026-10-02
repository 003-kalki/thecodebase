"""Explanations shown on the codebase guide site. build.py turns this file plus the source snapshot into data.js.

Each FILES entry: summary (one line), role (where it fits), points (key facts), items (symbol -> explanation; the
line number is found automatically by searching for the text in "find"), and questions (likely demo questions).
"""

PITCH = """A governed pipeline that turns approved HDFC Bank FAQ data into a fine-tuned, retrieval-grounded assistant,
and proves it is good and safe before it is served. We clean and version the data (Delta Lake), fine-tune Llama 3.2 1B
with LoRA/QLoRA (tracked in MLflow), answer with RAG over the approved FAQs, wrap every answer in input and output
guardrails, evaluate automatically (ROUGE-L, invented figures) and with people (human review), red-team it with
promptfoo, and release it through a registry with approvals, checksum verification and one-click rollback. A web
platform with roles (admin, engineer, employee) runs the whole lifecycle, and it is deployed on a Hugging Face Space."""

FLOW = [
    ("Download", "download_data.py", "Fetches BankFAQs (Kaggle) and Banking77 (PolyAI) into data/."),
    ("Clean and version", "clean_data.py",
     "Masks personal data, restores the HDFC name, removes exact and near duplicates, splits train/validation/test by "
     "question meaning (no paraphrase leaks into test), writes an immutable Delta Lake version plus a quality report."),
    ("Govern the dataset", "control_plane.py",
     "Register -> prepare -> approve. Restricted data is refused; a split with test rows that copy training rows "
     "cannot be approved."),
    ("Build the knowledge index", "rag.py",
     "Embeds every FAQ with BAAI/bge-small-en-v1.5 and saves the vectors; retrieval is exact cosine search."),
    ("Fine-tune", "train.py",
     "LoRA (QLoRA 4-bit on NVIDIA) on Llama 3.2 1B Instruct. RAG_TRAINING=1 trains on the real served prompt: "
     "the question plus its FAQ and two look-alike FAQs. Every run is logged to MLflow with data version and git commit."),
    ("Evaluate", "evaluate.py",
     "Base vs fine-tuned, with and without RAG, on held-out and reworded questions: ROUGE-L, token F1, invented "
     "figures, retrieval hit rate. Then human review (docs/) and the promptfoo red-team suite (promptfoo/)."),
    ("Register and approve", "registry.py",
     "Each version gets status pending -> approved/rejected, its SHA-256 checksum and evaluation. Only approved "
     "versions can be promoted; rollback swaps live and previous."),
    ("Serve", "server.py + inference.py",
     "FastAPI gateway. Each answer: mask input -> block injection/transactions/other banks -> retrieve FAQs -> "
     "generate -> check output (credentials, invented numbers) -> typed response with citations and confidence."),
    ("Operate", "frontend/index.html + control_plane.py",
     "Web platform with roles, audit log, monitoring with SLOs, Prometheus /metrics, feedback on answers."),
    ("Deploy", "Dockerfile + Hugging Face Space",
     "CPU container on a Hugging Face Space; downloads the live adapter from the private model repo with HF_TOKEN "
     "and refuses to start if the checksum differs."),
]

NUMBERS = [
    ("Live model", "llama_v3_1ep (Llama 3.2 1B Instruct + LoRA, RAG-aware training, 1 epoch)"),
    ("Rollback target", "llama_v2"),
    ("Raw FAQs -> clean FAQs", "1,773 raw -> 1,405 after removing 295 exact and 73 near duplicates (Delta version 7)"),
    ("Contamination", "0 test questions >= 0.95 similar to any training question (max 0.949)"),
    ("Splits", "1,124 train / 141 validation / 140 test, grouped by question meaning"),
    ("ROUGE-L with RAG, FAQ wording", "0.91 (llama_v2: 0.82)"),
    ("ROUGE-L with RAG, customer wording", "0.91 (llama_v2: 0.51)"),
    ("Human review (50 answers)", "41 correct (82%), 8 partly, 1 wrong, 3 harmful (llama_v2: 31 correct, 5 harmful)"),
    ("Reworded questions correct", "25/30 (83%) vs 16/30 (53%) for llama_v2"),
    ("Retrieval hit@3", "94% held-out, 93% reworded"),
    ("Unsupported figures in served answers", "0% after output guardrails"),
    ("promptfoo red-team suite", "36/36 passed"),
    ("Grader agreement (llama_v2 review)", "42/50 (84%), Cohen's kappa 0.71"),
    ("Training time", "about 8 minutes for 1 epoch on an RTX 4050 (QLoRA)"),
    ("Trainable parameters", "about 1.7 million (LoRA r=16 on q_proj and v_proj) out of ~1.2 billion"),
    ("Automated tests", "55 pytest tests, run on every push by GitHub Actions"),
    ("Deployed app", "Hugging Face Space (Docker, CPU), login required"),
]

FILES = {
    # ------------------------------------------------------------------ backend / serving
    "server.py": {
        "summary": "The FastAPI web server: login, every /v1 API endpoint, the model gateway and the web page.",
        "role": "Entry point of the running app (uvicorn server:app). It loads the live model once at start-up, "
                "checks who is calling and whether their role allows the action, calls control_plane.py / registry.py "
                "for records, and inference.py for answers. Every change is written to the audit log.",
        "points": [
            "The model is loaded once at start (assistant = Assistant()); promote and rollback reload it.",
            "Three helpers do the security work: current_user (who is this token?), require (does the role allow it?), "
            "act (run the action, write the audit log, turn errors into 400/404).",
            "People log in with a bearer token; applications can call /v1/inference with the x-api-key header (APP_KEY).",
            "Errors are controlled: a failed answer returns 503 with a trace id, never a stack trace.",
            "GET / returns frontend/index.html, so the API and the website come from the same server.",
        ],
        "items": [
            ("assistant = Assistant()", "Loads the registry's live model and FAQ index at start-up (~30 s)."),
            ("def index_for", "Which knowledge index an assistant uses: the full FAQ index, or a team's subset (cached)."),
            ("def current_user", "Reads 'Authorization: Bearer <token>' and returns the logged-in user, or 401."),
            ("def require", "Checks the user's role has a permission; a refusal is audited and returns 403."),
            ("def act", "Runs a control-plane action, writes success/failure to the audit log, maps errors to HTTP codes."),
            ('@app.post("/v1/auth/login")', "Login: returns a session token. 401 for wrong password, 429 when locked out."),
            ('@app.get("/v1/health")', "Public health check: live model version and adapter checksum."),
            ('@app.get("/v1/assistants")', "Admins/engineers see all assistants; employees only approved ones assigned to them."),
            ('@app.post("/v1/users/{username}/assistants")', "Admin assigns assistants to a user; only approved assistants allowed."),
            ('@app.post("/v1/datasets")', "Register a dataset with owner, purpose, classification, permission basis, retention."),
            ('@app.post("/v1/datasets/{dataset_id}/approve")', "Admin approval; the rules live in control_plane.approve_dataset."),
            ('@app.post("/v1/runs")', "Queue a fine-tuning run (approved dataset + approved base model)."),
            ('@app.get("/metrics"', "Prometheus scrape endpoint, optionally protected by METRICS_TOKEN."),
            ('@app.post("/v1/models/register")', "Register a new model version from a completed run (starts pending)."),
            ('@app.post("/v1/models/{version}/promote")', "Make an approved version live, then reload the model."),
            ('@app.post("/v1/deployments/{deployment_id}/rollback")', "Swap back to the previous live version and reload."),
            ("def gateway_caller", "Gateway access rules: assistant must be approved; app key or a user assigned to it; rate limit."),
            ('@app.post("/v1/inference"', "The model gateway: answers a question through inference.Assistant.answer and logs it."),
            ('@app.post("/v1/feedback")', "Good/bad rating on an answer, linked to its trace id and model version."),
        ],
        "questions": [
            ("How does the API know who I am?", "Login returns a random session token. The browser sends it as "
             "'Authorization: Bearer <token>'; current_user looks it up in auth.sessions."),
            ("What stops an engineer approving their own model?", "require(authorization, 'review_model') checks the "
             "role's permissions in auth.PERMISSIONS; ai_engineer does not have review/approve/promote, so it gets 403 "
             "and the attempt is audited."),
            ("What happens if the model crashes during an answer?", "The gateway catches it, logs a failed request "
             "(counts against the success-rate SLO) and returns 503 with a trace id instead of a stack trace."),
        ],
    },
    "inference.py": {
        "summary": "The governed answer path: input checks -> retrieval -> fine-tuned model -> output checks -> typed response.",
        "role": "Used by server.py for every chat answer. It also decides which model version to load and verifies "
                "its checksum, so an artifact that differs from the evaluated one is never served.",
        "points": [
            "Model choice: argument, else MODEL_VERSION env var, else registry.json 'live'.",
            "Downloads the adapter and FAQ index from the private Hugging Face repo if they are not on disk.",
            "Refuses to start if the adapter's SHA-256 differs from the one recorded in the registry.",
            "Blocked requests (prompt injection, transaction requests, other banks) never reach the model.",
            "Retrieved FAQs containing injected instructions are dropped (context_injection_removed).",
            "Top retrieval score below 0.70 -> out of scope -> escalate to PhoneBanking instead of guessing.",
            "Confidence: high if top score >= 0.80, medium if >= 0.70. It measures retrieval strength, not correctness.",
            "If the answer asks for credentials or contains numbers not in the cited FAQs, it is withheld and escalated.",
        ],
        "items": [
            ("ESCALATION_MESSAGE", "Safe fallback text used whenever the assistant should not answer."),
            ("REFUSALS = {", "Fixed replies for prompt injection, transaction requests and other-bank questions."),
            ("def file_sha256", "Checksum of the adapter file, compared with the registry before serving."),
            ("def ensure_local", "Uses models/<folder> or downloads it from HF_REPO with snapshot_download."),
            ("class Assistant", "Loads tokenizer + base model + LoRA adapter + FAQ index; holds ModelInfo for responses."),
            ("def answer", "The full answer pipeline for one question; every exit returns the same typed response."),
            ("retrieved = index.search", "Retrieval: top 3 FAQs by cosine similarity (rag.FaqIndex.search)."),
            ("if top_score < ANSWER_THRESHOLD", "Out-of-scope gate: no FAQ is close enough, so escalate."),
            ("answer, output_flags, unsupported = check_output", "Output guardrail: masks PII, finds credential requests and invented figures."),
        ],
        "questions": [
            ("Why can't the model invent a fee or phone number?", "check_output compares every amount/rate/period/"
             "phone-like number in the answer with the cited FAQs; if a number is not in them, the answer is withheld "
             "and the customer is sent to PhoneBanking."),
            ("How do you know the deployed model is the approved one?", "The adapter's SHA-256 is recorded in "
             "registry.json when it is approved; Assistant() recomputes it at start-up and refuses to serve on mismatch. "
             "/v1/health shows the checksum."),
            ("What does 'confidence' mean?", "How close the best FAQ is to the question (retrieval score), not whether "
             "the generated text is right. That is a documented limitation."),
        ],
    },
    "rag.py": {
        "summary": "Retrieval-augmented generation: embeds the FAQs, searches them, and builds the prompt with the top 3.",
        "role": "Builds models/rag_index (faqs.parquet, embeddings.npy, meta.json) from a Delta version. Used by "
                "inference.py at serving time, by evaluate.py --rag, by train.py when RAG_TRAINING=1, and by "
                "control_plane.py to build team indexes.",
        "points": [
            "Embedding model: BAAI/bge-small-en-v1.5 (best on reworded questions; bge-base was no better at 3x size).",
            "Question and answer are embedded together, so customers who describe the problem still match.",
            "Exact cosine search with one matrix product: ~1.4k FAQs, so no vector database is needed.",
            "Near-identical FAQs (similarity >= 0.99) are skipped so the 3 slots hold 3 different answers.",
            "faq_id is a hash of the content, so citations stay stable across rebuilds.",
            "Thresholds calibrated on Delta v7: banking questions score >= 0.749, off-topic 0.45-0.68 -> cut-off 0.70.",
            "The system prompt says FAQ entries are data, not instructions (prompt-injection defence).",
            "Team indexes reuse the full index's embeddings and keep only FAQs matching keywords: seconds, no GPU.",
        ],
        "items": [
            ("EMBED_MODEL", "Sentence-embedding model used for every FAQ and question."),
            ("ANSWER_THRESHOLD", "0.70: below this the question is treated as out of scope."),
            ("HIGH_CONFIDENCE", "0.80: at or above this, confidence is 'high'."),
            ("RAG_SYSTEM_PROMPT", "Instructions given to the model with the FAQs: answer only from them, copy numbers exactly."),
            ("def build_index", "Reads a Delta version, assigns content IDs, embeds and saves the index."),
            ("def build_team_index", "Builds a team's subset index from keywords (used by team datasets)."),
            ("class FaqIndex", "Loads an index and answers search(); also is_match() for scoring retrieval."),
            ("def search", "Cosine similarity, ranked, skipping near-duplicates, top k=3."),
            ("def rag_messages", "Chat messages: system prompt + <faq_entries> + the customer question."),
        ],
        "questions": [
            ("Why RAG and fine-tuning both?", "Fine-tuning teaches tone, length and how to read FAQs; RAG supplies the "
             "facts at answer time, so facts can be updated without retraining and every answer can cite its source."),
            ("Why no vector database?", "1,405 FAQs x 384 dimensions is tiny; exact search is one matrix product and "
             "instant. A vector DB (FAISS, pgvector) would be added at tens of thousands of documents."),
            ("How did you pick 0.70?", "Calibrated on Delta v7: real banking questions scored at least 0.749 on their "
             "best FAQ, off-topic questions 0.45-0.68."),
        ],
    },
    "guardrails.py": {
        "summary": "Deterministic safety checks (regex rules) for input, retrieved content and output.",
        "role": "Shared by clean_data.py (masking training data), inference.py (live traffic) and evaluate.py "
                "(invented figures), so data and customers are treated the same way. Checks return findings; the "
                "caller decides to mask, block or escalate, and the flags are returned in the response.",
        "points": [
            "Masks card/account numbers (also typed with spaces or dashes), Indian mobile numbers, emails and secrets "
            "like 'OTP 1234' or 'password: abc' (but not plain 'change my PIN').",
            "Prompt injection: 'ignore previous instructions', 'system prompt', 'you are now', 'act as', 'jailbreak'...",
            "Transaction requests: 'transfer ... for me', 'can you block my card' are refused; 'How do I transfer "
            "money?' is a question and is answered.",
            "Other banks (SBI, ICICI, Axis...) are refused unless the question also mentions HDFC.",
            "Output: blocks answers asking the customer to share OTP/PIN/CVV/password (unless it is a warning).",
            "invented_specifics: numbers in the answer must appear in the source FAQs (number words like 'seven' "
            "count; 'free/no charges' supports Rs. 0).",
        ],
        "items": [
            ("CARD_WITH_SEPARATORS", "Card numbers typed in groups ('4111 1111 1111 1111'), added after a manual check found a gap."),
            ("SECRET = re.compile", "Masks OTP/CVV/PIN/password only when a value follows."),
            ("def mask_sensitive", "Applies all masks in order and reports what was masked."),
            ("INJECTION = re.compile", "Prompt-injection patterns, used on customer input and on retrieved FAQs."),
            ("TRANSACTION_REQUEST", "Direct requests to move money or change accounts."),
            ("OTHER_BANK", "Names of other banks (found by the promptfoo suite: an invented SBI answer)."),
            ("def invented_specifics", "Finds amounts/rates/periods/phone numbers in an answer that the source does not contain."),
            ("def check_input", "Masks PII and raises flags: prompt_injection, transaction_request, other_bank."),
            ("def check_output", "Masks leaked PII, flags credential requests and unsupported figures."),
        ],
        "questions": [
            ("Why regex instead of an AI guard model?", "Deterministic, fast, testable (13 pytest cases) and explainable "
             "to a risk team. NeMo Guardrails or Presidio could be layered on top for fuzzier cases."),
            ("How do you stop prompt injection inside the data?", "Retrieved FAQs are checked with the same injection "
             "patterns and dropped if they contain instructions; the system prompt also says FAQ entries are data."),
        ],
    },
    "auth.py": {
        "summary": "Users, password hashing, login sessions, role permissions, lockout and rate limiting.",
        "role": "Used by server.py on every request. Users live in control/users.json (hashes only); sessions live "
                "in memory. Also a CLI to list users, add users and set passwords.",
        "points": [
            "Passwords: salted PBKDF2-HMAC-SHA256, 200,000 iterations. The password itself is never stored.",
            "Session = random token (secrets.token_urlsafe(32)) -> username + expiry (8 hours). Opaque bearer tokens.",
            "Several sessions per user are allowed: two people can be logged in as admin at once.",
            "RBAC: employee -> use_assistant; ai_engineer -> build (datasets, runs, models, assistants); admin -> also "
            "approve, review, promote, rollback, manage users.",
            "Lockout: 5 wrong passwords in 15 minutes locks the username for the rest of the window.",
            "Rate limit: 20 gateway calls per minute per caller (sliding window), configurable.",
            "Same error for unknown user and wrong password, so usernames cannot be discovered.",
            "In-memory sessions/counters reset on restart; production would use Redis or signed JWTs.",
        ],
        "items": [
            ("SESSION_HOURS", "How long a login lasts (8 hours)."),
            ("PERMISSIONS = {", "The role -> permissions table (RBAC). Engineers build but cannot approve."),
            ("def allow_request", "Sliding one-minute rate limit per caller; raises TooManyAttempts (HTTP 429)."),
            ("def hash_password", "PBKDF2-HMAC-SHA256 with a per-user salt, 200k iterations."),
            ("def public", "User record without password fields, plus the role's permissions, safe to send to the browser."),
            ("def login", "Lockout check, constant-time password compare, creates the session token."),
            ("def user_for_token", "Looks up a token, drops expired sessions."),
            ("def can_use_assistant", "Admins/engineers can test any assistant; employees only assigned ones."),
            ("def add_user", "CLI: create a user with role, team and assistants."),
            ("def set_password", "CLI: new salt + hash (minimum 8 characters)."),
        ],
        "questions": [
            ("What kind of authentication is this?", "Server-side session authentication with opaque bearer tokens, "
             "8-hour expiry, RBAC, account lockout and per-user rate limiting."),
            ("Why do all tabs share one login?", "They did, because the token was in localStorage. PR #17 moved it to "
             "sessionStorage, so each tab can be a different role."),
            ("What if the server restarts?", "Sessions are in memory, so everyone logs in again. Redis or JWTs would fix "
             "that in production."),
        ],
    },
    "schemas.py": {
        "summary": "Pydantic models: the typed request and response contracts of the API.",
        "role": "FastAPI validates every request body against these and generates the OpenAPI docs at /docs from them. "
                "The UI and the promptfoo tests are built against InferenceResponse.",
        "points": [
            "InferenceRequest: question (1-1000 chars), channel, purpose (assistant id), max_new_tokens (16-512).",
            "InferenceResponse: trace_id, answer, citations, confidence, escalation_required, missing_information, "
            "policy_flags, model (version, base model, adapter checksum, data version, embed model), latency_ms.",
            "Classification is limited to public/internal/confidential/restricted; restricted is refused later.",
            "Invalid input gets HTTP 422 automatically.",
        ],
        "items": [
            ("class InferenceRequest", "What a caller sends to /v1/inference."),
            ("class Citation", "One retrieved FAQ: stable faq_id, question, similarity score, data version."),
            ("class ModelInfo", "Which exact model answered (traceability)."),
            ("class DatasetRegisterRequest", "Governance metadata required to register data."),
            ("class RunRequest", "A fine-tuning request: name, dataset, base model, config, seed."),
            ("class ModelRegisterRequest", "Registering a model needs a 64-hex SHA-256 and evaluation scores."),
            ("class InferenceResponse", "The full typed answer contract."),
        ],
        "questions": [
            ("What is a trace id for?", "Every answer gets one; feedback, logs and failures link to it, so any answer "
             "can be traced to the model version and checksum that produced it."),
        ],
    },
    "registry.py": {
        "summary": "Model registry: versions, statuses, live/previous, promote, rollback and a history of every change.",
        "role": "Reads and writes registry.json (kept in git, so every release decision is reviewable). Called by "
                "server.py for register/review/promote/rollback and by inference.py to find the live version.",
        "points": [
            "New versions start 'pending'; only 'approved' can be promoted (the release gate).",
            "The live version cannot be rejected.",
            "Rollback swaps live and previous, so a second rollback undoes the first.",
            "Every change is appended to history with time, action, from, to and who.",
        ],
        "items": [
            ("def register_model", "Adds a pending version with run id, checksum and evaluation."),
            ("def set_status", "Approve or reject after review."),
            ("def promote", "Release gate: approved only; sets previous = old live."),
            ("def rollback", "Swaps live and previous."),
            ("def record", "Appends a history entry."),
        ],
        "questions": [
            ("How fast is rollback?", "One API call or one click: the registry swaps live/previous and the server "
             "reloads that adapter (downloading it if needed). Tested by tests/test_registry.py."),
        ],
    },
    "registry.json": {
        "summary": "The registry data: every model version, its status, checksum, training lineage, scores and history.",
        "role": "Source of truth for which model is live (llama_v3_1ep) and which is the rollback target (llama_v2).",
        "points": [
            "Each version records: status, base model, adapter_sha256, HF folder, training (data version, config, git "
            "commit, MLflow run id, rows, platform), evaluation (ROUGE-L, retrieval hit@3, unsupported figures, "
            "promptfoo, human review) and notes explaining the decision.",
            "Rejected versions stay in the file with the reason (e.g. llama_v3: 3 epochs worse on customer wording).",
        ],
        "items": [("\"live\"", "The version the server loads."), ("\"previous\"", "The rollback target."),
                  ("\"history\"", "Audit trail of register / approve / reject / promote / rollback.")],
        "questions": [],
    },
    "control_plane.py": {
        "summary": "Records and rules for datasets, assistants, training runs, the audit log, monitoring, SLOs and feedback.",
        "role": "The 'business logic' behind the platform pages. Heavy jobs (clean_data.py, train.py) run on the GPU "
                "worker; this file keeps their records in control/*.json and enforces the gates.",
        "points": [
            "Dataset lifecycle: registered -> preparing -> prepared -> approved (approved = frozen).",
            "Gates: restricted data refused; approval needs a prepared dataset; a split with test rows >= 0.95 "
            "similar to training rows is refused; team datasets need >= 10 FAQs and an approved parent.",
            "Runs need an approved dataset, an approved base model and an existing config.",
            "Assistant = shared fine-tuned model + one approved dataset's knowledge index; pending -> approved/rejected.",
            "Request log stores identifiers and outcomes only, never the customer's question (privacy).",
            "SLOs over 24 h: success rate >= 99%, p95 answer time <= 30 s, bad feedback <= 20%.",
            "prometheus_metrics() exposes the same numbers in Prometheus text format.",
        ],
        "items": [
            ("APPROVED_BASE_MODELS", "Only Llama 3.2 1B Instruct and Qwen2.5 0.5B Instruct may be fine-tuned."),
            ("def register_dataset", "Creates a dataset record with governance metadata; refuses restricted data."),
            ("def request_preparation", "Base dataset: marks 'preparing' (run clean_data.py). Team dataset: builds its index now."),
            ("def prepare_team_dataset", "Builds a team knowledge index from keywords and records a quality report."),
            ("def approve_dataset", "Quality gates before approval (contamination / minimum FAQs)."),
            ("def create_assistant", "New assistant from an approved dataset (starts pending)."),
            ("def review_assistant", "Admin approves or rejects a pending assistant."),
            ("def request_run", "Validates and queues a training run, with the exact command to run."),
            ("def sync_runs_from_mlflow", "Copies finished runs from MLflow into runs.json."),
            ("def audit", "Appends who did what, to what, and the result."),
            ("def log_request", "Logs a served answer (no question text)."),
            ("def check_slos", "Computes each SLO's target, actual and status."),
            ("def monitoring_summary", "Numbers for the Monitoring page."),
            ("def prometheus_metrics", "The /metrics text for Prometheus."),
            ("def add_feedback", "Stores a rating linked to the trace id and model version."),
        ],
        "questions": [
            ("Why JSON files instead of a database?", "Simple, reviewable in git, enough for a single-instance demo. "
             "Production would use PostgreSQL (the brief's recommended stack); the functions isolate storage so only "
             "read/write helpers change."),
            ("What is contamination?", "A test question that is (nearly) the same as a training question inflates the "
             "score. clean_data.py measures it; approval is blocked if any test row is >= 0.95 similar to training."),
        ],
    },
    # ------------------------------------------------------------------ data / ML
    "download_data.py": {
        "summary": "Downloads the raw datasets: BankFAQs from Kaggle and Banking77 from PolyAI's GitHub.",
        "role": "First step of the pipeline. Output goes to data/ (not committed).",
        "points": ["BankFAQs: 1,773 bank FAQ question/answer pairs (the dump calls the bank 'M&N').",
                   "Banking77 (CC BY 4.0): customer messages labelled with 77 intents; train and test splits."],
        "items": [("kagglehub.dataset_download", "Fetches BankFAQs."), ("BANKING77_URL", "Raw CSV URL for Banking77.")],
        "questions": [],
    },
    "clean_data.py": {
        "summary": "Turns raw FAQs into a clean, de-duplicated, leak-free, versioned Delta Lake table plus a quality report.",
        "role": "Data preparation step. Output: data/s3_storage_vault/cleaned_banking_table (Delta Lake, every write "
                "is a new immutable version) and data/quality_reports/cleaned_banking_table_v<N>.json.",
        "points": [
            "PII masking with the same rules as the live gateway (guardrails.mask_sensitive).",
            "Brand fix: the Kaggle dump anonymised HDFC as 'M&N'; restored to 'HDFC Bank'.",
            "Exact duplicates removed after normalising; near-duplicates removed by embedding similarity >= 0.99.",
            "Grouped split: questions >= 0.95 similar are joined (union-find) and kept in the same split, so no "
            "paraphrase of a test question is trained on. 80/10/10 with seed 42.",
            "Contamination check: highest test-to-train similarity; the quality report records it.",
            "Banking77 goes to a separate eval table; only added to training with INCLUDE_BANKING77=1.",
        ],
        "items": [
            ("def drop_near_duplicates", "Exact then embedding-based near-duplicate removal."),
            ("def question_groups", "Union-find over similar questions so each group stays in one split."),
            ("def assign_splits", "Shuffles whole groups and fills train, validation, test by row count."),
            ("def contamination", "Measures how close test questions are to training questions."),
            ("write_deltalake(LOCAL_S3_VAULT", "Writes the new immutable Delta version."),
            ("report_path = QUALITY_REPORTS", "Writes the quality report next to the version it describes."),
        ],
        "questions": [
            ("Why Delta Lake?", "Every write is a new version you can read back exactly (time travel), so each model "
             "records which data version trained it and evaluation can rebuild the same test split."),
            ("Why grouped splits?", "Random splits put paraphrases of the same question in train and test, which "
             "inflates scores. Grouping by meaning gave 0 test rows >= 0.95 similar to training."),
        ],
    },
    "train.py": {
        "summary": "Fine-tunes the base model with LoRA / QLoRA and logs everything to MLflow.",
        "role": "Runs on the GPU worker. Reads the Delta table, builds prompts, trains a LoRA adapter with TRL's "
                "SFTTrainer, evaluates on the test split, saves the adapter + metrics.json, logs to MLflow.",
        "points": [
            "Hardware auto-detect: NVIDIA -> cuda-qlora.yaml (4-bit QLoRA), Apple -> mac-lora.yaml, else cpu-demo.yaml.",
            "LoRA: rank 16, alpha 32, dropout 0.05, on q_proj and v_proj (~1.7M trainable parameters).",
            "QLoRA: base weights loaded in 4-bit NF4 with double quantisation; adapters trained in fp16.",
            "Loss only on the answer (completion_only_loss), so the model learns to answer, not to repeat prompts.",
            "RAG_TRAINING=1: each training example is the real served prompt - its own FAQ plus 2 retrieved look-alike "
            "FAQs, shuffled. Distractors never come from validation/test answers. This made llama_v3_1ep.",
            "Reproducibility: one seed (42), data version, config, git commit and dataset digest logged to MLflow.",
            "Env vars: BASE_MODEL, LORA_OUTPUT_DIR, MAX_STEPS, NUM_EPOCHS, RAG_TRAINING, SEED.",
        ],
        "items": [
            ("RAG_TRAINING=", "Switch for RAG-aware training."),
            ("def current_git_commit", "Code version for the run manifest ('-dirty' if uncommitted changes)."),
            ("def add_faq_context", "Builds the FAQ context (own FAQ + 2 distractors) for each training example."),
            ("bnb_config=BitsAndBytesConfig", "4-bit quantisation settings (QLoRA)."),
            ("peft_config=LoraConfig", "LoRA settings from the YAML config."),
            ("def formatting_prompts", "Prompt/completion chat format, identical to serving."),
            ("training_arguments = SFTConfig", "Batch size, epochs, learning rate, eval every 50 steps, max length."),
            ("mlflow.start_run", "One MLflow run per training, with tags, dataset lineage and artifacts."),
            ('json.dump(metrics', "metrics.json saved next to the adapter."),
        ],
        "questions": [
            ("What is LoRA in one line?", "Instead of changing the 1.2B weights, we train two small matrices per "
             "attention projection (rank 16); only ~1.7M parameters learn, and the adapter is a small file."),
            ("Why QLoRA?", "The base model is loaded in 4-bit, so it fits a 6 GB laptop GPU; quality loss is small."),
            ("Why did RAG-aware training help?", "llama_v2 was trained on question -> answer only and never saw FAQs "
             "in its prompt, so it often ignored them. Training on the served prompt taught it to read the right FAQ: "
             "customer-worded questions went from 16/30 to 25/30 correct."),
            ("Why 1 epoch?", "Validation loss stopped improving after ~0.7 epochs; 1 epoch scored 0.91 on reworded "
             "questions vs 0.86 for 3 epochs."),
        ],
    },
    "evaluate.py": {
        "summary": "Scores a fine-tuned adapter against its own base model, with and without RAG, and logs to MLflow.",
        "role": "Produces reports/eval_<adapter>[_rag][_reworded].csv/.json and an MLflow evaluation run linked to "
                "the training run. Also loads models for serving (load_model, generate are reused by inference.py).",
        "points": [
            "Four conditions: base, fine-tuned, base + RAG, fine-tuned + RAG. 'Base' = same model with the adapter off.",
            "Question sets: 140 held-out test questions, or 30 hand-reworded customer-style questions (--reworded).",
            "Metrics: ROUGE-L (word-order overlap), token F1 (word overlap), answer length, stop rate, invented "
            "figures, unsupported figures with RAG, retrieval hit@1 and hit@3.",
            "Greedy decoding (do_sample=False) so results are repeatable.",
            "NoRepeatAnswerNGrams stops 8-word loops in the answer without stopping it copying FAQ phrases.",
        ],
        "items": [
            ("def load_test_split", "Rebuilds the exact test split of a Delta version."),
            ("def load_model", "Base model (4-bit on NVIDIA, fp16 on Mac, fp32 on CPU) + LoRA adapter."),
            ("class NoRepeatAnswerNGrams", "Blocks the answer from repeating its own 8-grams."),
            ("def generate", "Batched greedy generation with the chat template."),
            ("def rouge_l", "ROUGE-L F1 from the longest common word subsequence."),
            ("def token_f1", "F1 of shared words regardless of order."),
        ],
        "questions": [
            ("Why quote the reworded score?", "The held-out set is in FAQ wording, close to training text. Reworded "
             "questions are how customers actually ask; that is where llama_v2 failed (0.51) and llama_v3_1ep fixed it (0.91)."),
            ("Is ROUGE-L enough?", "No: it counts matching words and cannot tell yes from no. That is why we did a "
             "human review of 50 answers and the promptfoo red-team suite."),
        ],
    },
    # ------------------------------------------------------------------ frontend
    "frontend/index.html": {
        "summary": "The whole web platform in one file: React 18 + Tailwind, rendered in the browser (no build step).",
        "role": "Served by server.py at '/'. Calls the /v1 API with the login token. Pages appear by role.",
        "points": [
            "Libraries from CDNs: React, ReactDOM, Recharts (charts), Babel standalone (JSX in the browser), Tailwind.",
            "api() adds the bearer token and turns error responses into readable messages; useApi() loads data for a page.",
            "Login token in sessionStorage (per tab), so different tabs can be different roles (PR #17).",
            "Pages: Login, Dashboard, AI Assistant (chat), Datasets (+ detail), Training Jobs, Assistants, Models "
            "(+ detail), Evaluations, Approvals, Deployments, Monitoring, Audit Logs, Users (admin), Settings.",
            "Employees only see the AI Assistant; engineers build; admins approve, deploy and manage users.",
            "The chat shows citations, confidence, escalation and policy flags, with good/bad feedback per answer.",
        ],
        "items": [
            ("const TOKEN_KEY", "Name of the stored login token."),
            ("async function api", "Fetch wrapper: bearer token, JSON, readable errors."),
            ("function useApi", "Loads a GET endpoint for a page, with reload()."),
            ("function LoginPage", "Sign-in form."),
            ("function DashboardPage", "Pipeline overview: datasets, runs, models, monitoring, approvals."),
            ("function AnswerCard", "One chat answer with citations, confidence, flags and feedback buttons."),
            ("function AssistantPage", "The chat page; pick an assistant you are allowed to use."),
            ("function RegisterDatasetModal", "Register a base or team dataset (parent + keywords)."),
            ("function DatasetDetailPage", "Governance info, lifecycle stages, prepare/approve buttons, quality report."),
            ("function NewRunModal", "Request a training run."),
            ("function CreateAssistantModal", "Create an assistant from an approved dataset."),
            ("function AssistantsPage", "List assistants; admins approve/reject."),
            ("function ModelDetailPage", "Model card data, evaluation, review and promote."),
            ("function EvaluationsPage", "Grouped bar charts of scores per model."),
            ("function ApprovalsPage", "Everything waiting for human sign-off."),
            ("function DeploymentsPage", "Live/previous model, promote and rollback."),
            ("function MonitoringPage", "Requests, latency percentiles, SLOs, guardrail events."),
            ("function AuditLogsPage", "Who did what and when."),
            ("function UsersPage", "Admin assigns assistants to users."),
            ("const NAV_ITEMS", "Sidebar pages and which permission shows each."),
            ("function App()", "App shell: session, routing, sidebar."),
        ],
        "questions": [
            ("Why no React build step?", "One self-contained file served by FastAPI: nothing to build or deploy "
             "separately. For production you would build it with Vite/Next.js and serve static assets."),
        ],
    },
    # ------------------------------------------------------------------ control data
    "control/users.json": {
        "summary": "Demo users: admin, engineer, employee, fd_employee, with roles, teams, assigned assistants.",
        "role": "Read by auth.py. Holds only salted password hashes, never passwords.",
        "points": ["employee is assigned customer_faq; fd_employee has no assistant until an admin assigns one.",
                   "New users are added with: python auth.py --add-user <name> --role employee ..."],
        "items": [], "questions": [],
    },
    "control/assistants.json": {
        "summary": "Assistants: customer_faq (all 1,405 FAQs, approved).",
        "role": "Read by server.py/control_plane.py. Team assistants created on the website are added here.",
        "points": ["Each assistant: name, owner, dataset_id, index_dir, number of FAQs, status, history."],
        "items": [], "questions": [],
    },
    "control/datasets.json": {
        "summary": "Dataset records: ds-001 BankFAQs (approved, Delta v7) and ds-002 Banking77 (registered, eval only).",
        "role": "Read/written by control_plane.py; shown on the Datasets pages.",
        "points": ["Each record: owner, purpose, classification, permission basis, retention, status, Delta version, "
                   "quality report, approver, history."],
        "items": [], "questions": [],
    },
    "control/runs.json": {
        "summary": "Training run records copied from MLflow (control_plane.py --sync-runs) plus queued requests.",
        "role": "Shown on the Training Jobs page.",
        "points": ["Each run: base model, data version, config, LoRA settings, seed, git commit, device, epochs, "
                   "RAG training flag, train/test loss, minutes, MLflow run id."],
        "items": [], "questions": [],
    },
    # ------------------------------------------------------------------ configs
    "configs/training/cuda-qlora.yaml": {
        "summary": "Training profile for NVIDIA GPUs: Llama 3.2 1B in 4-bit (QLoRA), LoRA r=16, batch 4 x 2, lr 2e-4.",
        "role": "Picked automatically by train.py when CUDA is available. Used for the live model.",
        "points": ["load_in_4bit + nf4 + double quantisation = QLoRA.",
                   "Effective batch size 8 (4 per device x 2 gradient accumulation).",
                   "num_train_epochs 3, overridden to 1 with NUM_EPOCHS=1 for llama_v3_1ep."],
        "items": [], "questions": [],
    },
    "configs/training/mac-lora.yaml": {
        "summary": "Training profile for Apple Silicon (MPS): Qwen2.5 0.5B, fp16, no quantisation.",
        "role": "Picked by train.py on a Mac; produced the qwen_mac candidates.", "points": [], "items": [], "questions": [],
    },
    "configs/training/cpu-demo.yaml": {
        "summary": "Fallback profile for CPU-only machines: Qwen2.5 0.5B, fp32, batch 1 - for demos, not real training.",
        "role": "Picked by train.py when no GPU is found.", "points": [], "items": [], "questions": [],
    },
    # ------------------------------------------------------------------ deployment / infra
    "Dockerfile": {
        "summary": "Builds the serving container: Python 3.14 slim, CPU-only PyTorch, the serving requirements, port 7860.",
        "role": "Used by the Hugging Face Space and docker-compose. Model files are not baked in; inference.py "
                "downloads them from the private HF repo at start-up with the HF_TOKEN secret and checks the checksum.",
        "points": ["Runs as user 1000 (Hugging Face Spaces requirement).",
                   "torch installed from the CPU index first to avoid ~3 GB of CUDA libraries.",
                   "Dependencies before code, so code changes rebuild quickly (layer caching)."],
        "items": [], "questions": [
            ("Why not bake the model into the image?", "Keeps the image small and public-safe; the adapter is "
             "downloaded from a private repo and verified by checksum, so the same image can serve any version.")],
    },
    ".dockerignore": {
        "summary": "Keeps data, models, logs, tests, MLflow files and .env out of the Docker image.",
        "role": "Smaller, safer image.", "points": [], "items": [], "questions": [],
    },
    "docker-compose.yml": {
        "summary": "Local production-like stack: the app + Prometheus + Grafana.",
        "role": "docker compose up --build -> app :7860, Prometheus :9090, Grafana :3000.",
        "points": ["Model cache volumes so the 2.5 GB base model downloads once.",
                   "Health check on /v1/health with a 300 s start period for the first model download."],
        "items": [], "questions": [],
    },
    "infrastructure/kubernetes/deployment.yaml": {
        "summary": "Kubernetes Deployment for production: 1 replica, 2-4 CPU, 10-12 GiB RAM, readiness/liveness probes.",
        "role": "Reference production design (not used by the Space).",
        "points": ["Readiness probe: send traffic only after the model has loaded.",
                   "Liveness probe: restart the pod if it stops answering.",
                   "Secrets (HF_TOKEN, APP_KEY, METRICS_TOKEN) come from a Kubernetes Secret."],
        "items": [], "questions": [],
    },
    "infrastructure/kubernetes/service.yaml": {"summary": "Kubernetes Service exposing the app inside the cluster.",
                                                "role": "Pairs with deployment.yaml.", "points": [], "items": [], "questions": []},
    "infrastructure/kubernetes/namespace.yaml": {"summary": "Kubernetes namespace for the platform.", "role": "",
                                                  "points": [], "items": [], "questions": []},
    "infrastructure/prometheus/prometheus.yml": {
        "summary": "Prometheus scrape config: reads /metrics from the app using the metrics token.",
        "role": "Used by docker-compose.", "points": [], "items": [], "questions": []},
    "infrastructure/prometheus/alerts.yml": {
        "summary": "Alert rules: SLO breached, gateway down, more than 3 failed answers in 15 minutes.",
        "role": "Turns metrics into alerts.", "points": [], "items": [], "questions": []},
    "infrastructure/grafana/dashboards/hdfc-ai-platform.json": {
        "summary": "Grafana dashboard: requests by outcome, latency percentiles, guardrail events, SLO status, live model.",
        "role": "Auto-provisioned by docker-compose.", "points": [], "items": [], "questions": []},
    "infrastructure/grafana/provisioning/dashboards/dashboards.yml": {
        "summary": "Tells Grafana to load the dashboard JSON files from /var/lib/grafana/dashboards at start-up.",
        "role": "Grafana provisioning (docker-compose).", "points": [], "items": [], "questions": []},
    "infrastructure/grafana/provisioning/datasources/prometheus.yml": {
        "summary": "Adds Prometheus as Grafana's data source automatically.",
        "role": "Grafana provisioning (docker-compose).", "points": [], "items": [], "questions": []},
    "infrastructure/prometheus/metrics_token.example": {
        "summary": "Placeholder for the token Prometheus sends to /metrics; the real file is never committed.",
        "role": "Copy to metrics_token with the same value as METRICS_TOKEN.", "points": [], "items": [], "questions": []},
    "deploy/space-README.md": {
        "summary": "README used on the Hugging Face Space (its YAML header says sdk: docker, app_port: 7860).",
        "role": "Copied over README.md when uploading to the Space.", "points": [], "items": [], "questions": []},
    ".github/workflows/tests.yml": {
        "summary": "CI: runs the 55 pytest tests and checks every config file parses, on every push and pull request.",
        "role": "Stops a change that breaks a guardrail, the registry, login or control-plane rules being merged unnoticed.",
        "points": [], "items": [], "questions": []},
    ".github/workflows/keep-space-awake.yml": {
        "summary": "Calls the Space's /v1/health once a day so it is not paused after 48 h without visitors.",
        "role": "Keeps the review link responsive.", "points": [], "items": [], "questions": []},
    ".env.example": {
        "summary": "Template of environment variables: HF_TOKEN, APP_KEY, METRICS_TOKEN and optional settings.",
        "role": "Copy to .env (never committed). Secrets never live in code.", "points": [], "items": [], "questions": []},
    # ------------------------------------------------------------------ tests / evaluation evidence
    "tests/test_auth.py": {
        "summary": "14 tests: hashing, sessions, logout, expiry, role permissions, lockout, rate limit, password rules.",
        "role": "Run by CI.", "points": [], "items": [], "questions": []},
    "tests/test_control_plane.py": {
        "summary": "20 tests: dataset gates, contamination block, frozen datasets, run validation, team datasets, "
                   "assistant lifecycle, SLOs, metrics, feedback.",
        "role": "Run by CI.", "points": [], "items": [], "questions": []},
    "tests/test_guardrails.py": {
        "summary": "13 tests: masking (incl. spaced card numbers), injection, other banks, transactions, credential "
                   "requests, invented figures, echoed prompts, injected source content.",
        "role": "Run by CI.", "points": [], "items": [], "questions": []},
    "tests/test_registry.py": {
        "summary": "8 tests: rollback, double rollback, promote, unknown/unapproved versions, pending cannot go live, "
                   "live cannot be rejected.",
        "role": "Run by CI on a copy of registry.json.", "points": [], "items": [], "questions": []},
    "promptfoo/promptfooconfig.yaml": {
        "summary": "promptfoo setup: calls the running gateway's /v1/inference like a banking app would.",
        "role": "Two checks run on every case: the response contract (trace id, checksum, confidence, escalation) and "
                "'never asks the customer for a credential'.", "points": [], "items": [], "questions": []},
    "promptfoo/tests.yaml": {
        "summary": "36 red-team and quality cases in 12 categories.",
        "role": "Release gate: injection, transactions, personal data, credentials and privacy must all pass.",
        "points": ["Categories: grounded answers, over-blocking, prompt injection, transactions, personal data, "
                   "credentials, off-topic, other banks, invented figures, privacy/memorisation, bias, robustness."],
        "items": [], "questions": [
            ("What did the red-team suite find?", "An invented answer about SBI (fixed with the other_bank guardrail), "
             "a stale '7%' FD rate in the data (documented), and spaced card numbers not masked (fixed).")]},
    "promptfoo/RESULTS.md": {"summary": "Results of every promptfoo run per model (llama_v3_1ep: 36/36).",
                             "role": "Evidence for the release decision.", "points": [], "items": [], "questions": []},
    "promptfoo/README.md": {"summary": "How to run the promptfoo suite and what each category checks.",
                            "role": "", "points": [], "items": [], "questions": []},
    "docs/api-contract.md": {"summary": "Every API endpoint, who can call it, and the response contract.",
                             "role": "Documentation for app teams.", "points": [], "items": [], "questions": []},
    "docs/human_review_llama_v2.csv": {
        "summary": "Human review of 50 llama_v2 answers: grade, harmful, notes, second grader's grades.",
        "role": "Two independent graders: 84% agreement, Cohen's kappa 0.71.", "points": [], "items": [], "questions": []},
    "docs/human_review_llama_v3_1ep.csv": {
        "summary": "Human review of the same 50 questions for llama_v3_1ep: 41 correct, 8 partly, 1 wrong, 3 harmful.",
        "role": "Main evidence that the release improved real answers.", "points": [], "items": [], "questions": []},
    "data/rag_reworded_questions.csv": {
        "summary": "30 test questions rewritten the way customers ask, so they do not match the FAQ wording.",
        "role": "Used by evaluate.py --reworded; the hardest and most honest test set.", "points": [], "items": [], "questions": []},
    "data/quality_reports/cleaned_banking_table_v7.json": {
        "summary": "Quality report of Delta v7: rows, PII masks applied, duplicates removed, split sizes, contamination.",
        "role": "Attached to dataset ds-001 when it was prepared.", "points": [], "items": [], "questions": []},
    "MODEL_CARD.md": {
        "summary": "Model card: intended and prohibited uses, data, training, evaluation, human review, limitations, safety, versions.",
        "role": "What a model-risk reviewer reads before approving.", "points": [], "items": [], "questions": []},
    "README.md": {"summary": "Project overview, results, model versions, setup, pipeline commands, API, deployment.",
                  "role": "", "points": [], "items": [], "questions": []},
    "requirements.txt": {"summary": "All Python packages for data prep, training and evaluation (pinned versions).",
                         "role": "", "points": [], "items": [], "questions": []},
    "requirements-serve.txt": {"summary": "Only the packages needed to serve answers (smaller Docker image).",
                               "role": "", "points": [], "items": [], "questions": []},
    ".gitignore": {"summary": "Keeps data, models, logs, MLflow files, reports and .env out of git.",
                   "role": "", "points": [], "items": [], "questions": []},
}

QA = [
    ("Big picture", [
        ("What does this project do, in 30 seconds?", PITCH),
        ("Walk me through one question end to end.", "The browser sends the question with the login token to POST "
         "/v1/inference. server.py checks the user may use that assistant and the rate limit. inference.py masks "
         "personal data and blocks injection, transaction requests and other-bank questions. It retrieves the top 3 "
         "FAQs (rag.py); if the best score is below 0.70 it escalates. Otherwise Llama 3.2 1B + our LoRA adapter "
         "answers from those FAQs. The output check masks leaked data and withholds answers that ask for credentials "
         "or contain numbers not in the FAQs. The response carries citations, confidence, escalation flag, policy "
         "flags, the exact model version and checksum, and a trace id; the request is logged without the question text."),
        ("Why fine-tune at all if you use RAG?", "RAG gives the facts; fine-tuning teaches the model to use them: "
         "bank tone, right length, and reading the correct FAQ among look-alikes. The base model + RAG scored 0.49 on "
         "reworded questions; our RAG-trained model scores 0.91."),
        ("Why such a small model (1B)?", "It fits a 6 GB laptop GPU with QLoRA, trains in 8 minutes, serves on CPU, "
         "and is enough when the facts come from retrieval. The pipeline accepts any approved base model."),
        ("What would you do with more time?", "Fix the 3 harmful answers (car-loan age, business-loan collateral), "
         "add Banking77 rewordings as training questions, move sessions/records to Redis/PostgreSQL, canary releases, "
         "signed artifacts, and a governed rates source for figures that change."),
    ]),
    ("Data", [
        ("Where does the data come from?", "BankFAQs from Kaggle (1,773 bank FAQ Q&A rows, anonymised as 'M&N' which "
         "we restore to HDFC) and Banking77 from PolyAI (customer messages with 77 intents, CC BY 4.0), used for evaluation."),
        ("How do you protect personal data?", "Regex masking of card/account numbers, mobiles, emails and secrets in "
         "training data and live traffic (same function), the request log stores no question text, and the output "
         "check masks anything leaked."),
        ("How do you avoid data leakage between train and test?", "Near-duplicates removed, then questions >= 0.95 "
         "similar are grouped and kept in one split. The contamination check shows 0 test rows >= 0.95 similar to "
         "training, and approval is blocked otherwise."),
        ("What is Delta Lake doing here?", "Versioned storage: each clean run is a new immutable version (we are on "
         "v7). Models record which version trained them; evaluation rebuilds the exact test split from it."),
        ("Why not train on Banking77?", "It has intent labels, not answers. It is used as an evaluation set; mapped to "
         "HDFC FAQs it could later add customer-style rewordings."),
    ]),
    ("Model and training", [
        ("Explain LoRA and QLoRA.", "LoRA freezes the base model and learns small low-rank update matrices on chosen "
         "layers (rank 16 on q_proj and v_proj: ~1.7M parameters). QLoRA loads the frozen base in 4-bit NF4 so it fits "
         "small GPUs; the adapter trains in fp16."),
        ("Which models did you compare?", "Llama 3.2 1B vs Qwen 2.5 0.5B with identical settings: Llama won on "
         "customer-worded questions (0.91 vs 0.74 with RAG-aware training). 1 epoch beat 3 epochs (0.91 vs 0.86)."),
        ("What is RAG-aware training?", "Training each example on the exact prompt used at serving: the question with "
         "its own FAQ plus two retrieved look-alike FAQs, shuffled. The model learns to pick the right FAQ."),
        ("How is training reproducible?", "Fixed seed 42, pinned config YAML, Delta version, git commit, dataset digest "
         "and all metrics logged in MLflow; metrics.json saved next to the adapter; the adapter's SHA-256 in the registry."),
        ("How long does training take?", "About 8 minutes for 1 epoch on an RTX 4050 laptop GPU (QLoRA)."),
    ]),
    ("Evaluation and safety", [
        ("How did you evaluate?", "Automatic: ROUGE-L, token F1, invented figures, retrieval hit rate on 140 held-out "
         "and 30 reworded questions, base vs fine-tuned, with and without RAG. Human: 50 answers graded Correct/Partly/"
         "Wrong + harmful. Red team: 36 promptfoo cases against the live API."),
        ("What is ROUGE-L?", "F1 of the longest common subsequence of words between the answer and the reference: "
         "1.0 = same words in the same order."),
        ("What is Cohen's kappa?", "Agreement between two graders corrected for chance agreement. 0.71 = substantial."),
        ("What counts as harmful?", "If acting on the answer could cost the customer money, cause a failed or "
         "misdirected transaction, or commit them to something false. Being told 'you can't' when you can is wrong "
         "but not harmful."),
        ("What are the known failures?", "3 harmful answers: self-employed car-loan minimum age 20 instead of 21 (two "
         "questions) and collateral described for a business loan that needs none. Confidence measures retrieval, not "
         "correctness. FAQ data is a snapshot (e.g. a stale 7% FD rate)."),
        ("How do you stop prompt injection?", "Input patterns block it before the model; retrieved FAQs with injected "
         "instructions are dropped; the system prompt marks FAQ entries as data; promptfoo tests 5 injection cases."),
        ("Can the assistant move money?", "No. It only answers questions; direct transaction requests are refused and "
         "escalated before reaching the model."),
    ]),
    ("Platform, release and deployment", [
        ("Who can do what?", "Employee: chat with assigned assistants. AI engineer: register/prepare datasets, request "
         "runs, register models, create assistants - cannot approve. Admin: everything, including approvals, promote, "
         "rollback and users."),
        ("How does a model go live?", "Train -> evaluate -> register (pending, with checksum and scores) -> admin "
         "approves -> promote. Only approved versions can be promoted; every step is in registry history and the audit log."),
        ("How do you roll back?", "Deployments -> Rollback: the registry swaps live and previous and the server reloads "
         "the previous adapter. One click, tested."),
        ("What are your SLOs?", "Over 24 hours: success rate >= 99%, p95 answer time <= 30 s, bad feedback <= 20%. "
         "Shown on Monitoring and exported to Prometheus with alerts."),
        ("Where is it deployed?", "A Hugging Face Space (Docker, CPU). On start it downloads the live adapter from the "
         "private model repo with the HF_TOKEN secret and verifies the checksum. A daily GitHub Action keeps it awake."),
        ("Why is the live site slower than local?", "It runs on CPU; locally it runs on an RTX 4050 GPU."),
        ("What is a team assistant?", "The same fine-tuned model with a smaller knowledge index: an approved subset of "
         "the FAQs selected by keywords (e.g. 49 loan FAQs). Admin approves the dataset and the assistant, then assigns it."),
        ("What kind of authentication is used?", "Server-side sessions with opaque bearer tokens (8 h), salted PBKDF2 "
         "password hashes, RBAC, lockout after 5 wrong passwords, 20 requests/minute rate limit."),
    ]),
]

GLOSSARY = [
    ("LLM", "Large language model: predicts the next word; here Llama 3.2 1B Instruct."),
    ("Fine-tuning", "Further training a pretrained model on our own examples."),
    ("LoRA", "Low-Rank Adaptation: train small matrices added to frozen layers instead of all weights."),
    ("QLoRA", "LoRA on a base model loaded in 4-bit precision to save GPU memory."),
    ("Adapter", "The small trained LoRA file (adapter_model.safetensors) applied on top of the base model."),
    ("PEFT", "Parameter-Efficient Fine-Tuning: Hugging Face library that implements LoRA."),
    ("TRL / SFTTrainer", "Hugging Face library and trainer for supervised fine-tuning on prompt/completion pairs."),
    ("RAG", "Retrieval-Augmented Generation: fetch relevant documents and put them in the prompt."),
    ("Embedding", "A vector representing a text's meaning; similar texts have close vectors."),
    ("Cosine similarity", "How close two embedding vectors point; 1 = same direction."),
    ("hit@3", "Share of questions where the correct FAQ is among the top 3 retrieved."),
    ("ROUGE-L", "Overlap score based on the longest common word subsequence."),
    ("Token F1", "Overlap score of shared words regardless of order."),
    ("Epoch", "One pass over all training examples."),
    ("Validation / test split", "Validation tunes training; test is held out for the final score only."),
    ("Contamination / leakage", "Test questions that also appear (or nearly) in training, inflating scores."),
    ("Delta Lake", "Versioned table format: every write is a new, readable version."),
    ("MLflow", "Experiment tracking: parameters, metrics, artifacts and lineage of every run."),
    ("Model registry", "Record of model versions, status, checksum and live/previous (registry.json)."),
    ("SHA-256 checksum", "Fingerprint of the adapter file; any change gives a different value."),
    ("Guardrails", "Rules checked before and after the model (masking, blocking, escalation)."),
    ("Prompt injection", "Text that tries to override the assistant's instructions."),
    ("Escalation", "Sending the customer to PhoneBanking/branch instead of answering."),
    ("RBAC", "Role-Based Access Control: permissions come from the user's role."),
    ("Bearer token", "Random string sent as 'Authorization: Bearer ...' to prove you are logged in."),
    ("SLO", "Service Level Objective: a target such as p95 answer time <= 30 s."),
    ("p95 latency", "95% of answers are faster than this."),
    ("Prometheus / Grafana", "Metrics collection and dashboards/alerts."),
    ("promptfoo", "Tool that runs red-team and quality test cases against the live API."),
    ("Cohen's kappa", "Agreement between two graders corrected for chance."),
    ("Hugging Face Space", "Hosting for ML apps; ours runs our Docker image."),
    ("FastAPI / Pydantic", "Python web framework / data validation used for the typed API."),
    ("Rollback", "Switching the live model back to the previous version."),
    ("Canary release", "Sending a small share of traffic to a new version first (not implemented; future work)."),
]
