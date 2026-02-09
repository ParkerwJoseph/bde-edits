import os
from dotenv import load_dotenv

load_dotenv()

# API Configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", 8000))
DATABASE_URL = os.getenv("DATABASE_URL")
API_BASE_URL = os.getenv("API_BASE_URL", "https://bde-webapp-dev.azurewebsites.net")

# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")

# Azure OpenAI Embedding Configuration
AZURE_OPENAI_EMBEDDING_ENDPOINT = os.getenv("AZURE_OPENAI_EMBEDDING_ENDPOINT")
AZURE_OPENAI_EMBEDDING_API_KEY = os.getenv("AZURE_OPENAI_EMBEDDING_API_KEY")
AZURE_OPENAI_EMBEDDING_API_VERSION = os.getenv("AZURE_OPENAI_EMBEDDING_API_VERSION", "2023-05-15")

# Azure Document Intelligence Configuration
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
AZURE_DOCUMENT_INTELLIGENCE_API_KEY = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_API_KEY")

# File Upload Configuration
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
# No file size limit - allow large files (100s of MBs)
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 0))  # 0 = no limit

# LLM Token Limits (GPT-4o-mini: 128k context, 16k max output)
# Input kept small so output (which includes all data as JSON) stays under 16k limit
LLM_MAX_INPUT_TOKENS = 10000  # ~8k per batch after margin
LLM_MAX_OUTPUT_TOKENS = 16000  # Max output tokens for GPT-4o-mini

# Azure OpenAI Whisper Configuration
AZURE_WHISPER_ENDPOINT = os.getenv("AZURE_WHISPER_ENDPOINT")
AZURE_WHISPER_API_KEY = os.getenv("AZURE_WHISPER_API_KEY")
AZURE_WHISPER_DEPLOYMENT_NAME = os.getenv("AZURE_WHISPER_DEPLOYMENT_NAME", "whisper")
AZURE_WHISPER_API_VERSION = os.getenv("AZURE_WHISPER_API_VERSION", "2024-06-01")

# Azure Blob Storage Configuration
AZURE_STORAGE_ACCOUNT_NAME = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
AZURE_STORAGE_ACCOUNT_KEY = os.getenv("AZURE_STORAGE_ACCOUNT_KEY")
AZURE_STORAGE_CONTAINER_NAME = os.getenv("AZURE_STORAGE_CONTAINER_NAME")
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")  # Optional: if provided, takes precedence

# Azure Queue Configuration (for document processing)
DOCUMENT_PROCESSING_QUEUE = os.getenv("DOCUMENT_PROCESSING_QUEUE", "document-processing")
QUICKBOOK_PROCESSING_QUEUE = os.getenv("QUICKBOOK_PROCESSING_QUEUE", "quickbook-processing")

# Webhook Configuration (for Azure Function callbacks)
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")  # Shared secret for webhook authentication

# Redis Configuration (for WebSocket pub/sub across workers)
AZURE_REDIS_CONNECTION_STRING = os.getenv("AZURE_REDIS_CONNECTION_STRING")

# QuickBooks Configuration
QUICKBOOKS_CLIENT_ID = os.getenv("QUICKBOOKS_CLIENT_ID")
QUICKBOOKS_CLIENT_SECRET = os.getenv("QUICKBOOKS_CLIENT_SECRET")
QUICKBOOKS_REDIRECT_URI = os.getenv("QUICKBOOKS_REDIRECT_URI")
QUICKBOOKS_ENVIRONMENT = os.getenv("QUICKBOOKS_ENVIRONMENT", "sandbox")  # "sandbox" or "production"

# Carbon Voice Configuration
CARBONVOICE_CLIENT_ID = os.getenv("CARBONVOICE_CLIENT_ID")
CARBONVOICE_CLIENT_SECRET = os.getenv("CARBONVOICE_CLIENT_SECRET")
CARBONVOICE_REDIRECT_URI = os.getenv("CARBONVOICE_REDIRECT_URI")
CARBONVOICE_ENVIRONMENT = os.getenv("CARBONVOICE_ENVIRONMENT", "production")  # Carbon Voice API is production

# Carbon Voice Queue (for async processing)
CARBONVOICE_PROCESSING_QUEUE = os.getenv("CARBONVOICE_PROCESSING_QUEUE", "carbonvoice-processing")

# Frontend URL for OAuth redirects
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")