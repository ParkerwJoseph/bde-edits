import os
from dotenv import load_dotenv

load_dotenv()

# Azure AD Configuration
TENANT_ID = os.getenv("AZURE_TENANT_ID", "")  # BCP's tenant ID (platform owner)
CLIENT_ID = os.getenv("AZURE_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET", "")
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:8000/api/auth/callback")
ONBOARDING_REDIRECT_URI = os.getenv("ONBOARDING_REDIRECT_URI", "http://localhost:8000/api/onboarding/callback")

# Frontend URL for redirects
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

# Platform tenant ID - this is BCP's Azure tenant
# Users from this tenant are considered platform staff
PLATFORM_AZURE_TENANT_ID = TENANT_ID
