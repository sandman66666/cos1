import os

folders = [
    "chief_of_staff_ai",
    "chief_of_staff_ai/config",
    "chief_of_staff_ai/auth",
    "chief_of_staff_ai/data",
    "chief_of_staff_ai/ingest",
    "chief_of_staff_ai/processors",
    "chief_of_staff_ai/embeddings",
    "chief_of_staff_ai/storage",
    "chief_of_staff_ai/interface",
    "chief_of_staff_ai/utils",
]

files = {
    "chief_of_staff_ai/README.md": "# Chief of Staff AI – Gmail E2E v0.1\n",
    "chief_of_staff_ai/.env.example": "GOOGLE_CLIENT_ID=\nGOOGLE_CLIENT_SECRET=\nOPENAI_API_KEY=\n",
    "chief_of_staff_ai/requirements.txt": "google-api-python-client\noauth2client\nopenai\nfaiss-cpu\nstreamlit\n",
    "chief_of_staff_ai/run.py": "# Entry point for Gmail E2E flow\n\nif __name__ == '__main__':\n    print('Run your pipeline here')\n",

    "chief_of_staff_ai/config/settings.py": "# Configuration settings",
    "chief_of_staff_ai/auth/gmail_auth.py": "# Handles Gmail OAuth setup",
    "chief_of_staff_ai/data/email_store.json": "[]",
    "chief_of_staff_ai/ingest/gmail_fetcher.py": "# Fetch Gmail messages",
    "chief_of_staff_ai/processors/email_normalizer.py": "# Normalize Gmail data",
    "chief_of_staff_ai/processors/task_extractor.py": "# Extract tasks from email",
    "chief_of_staff_ai/embeddings/embedder.py": "# Create vector embeddings",
    "chief_of_staff_ai/storage/vector_store.py": "# Manage FAISS or similar DB",
    "chief_of_staff_ai/interface/prompt_console.py": "# User interface for queries",
    "chief_of_staff_ai/utils/datetime_utils.py": "# Convert natural dates to datetime",
}

for folder in folders:
    os.makedirs(folder, exist_ok=True)

for path, content in files.items():
    with open(path, 'w') as f:
        f.write(content)

print("✅ Project structure created.")