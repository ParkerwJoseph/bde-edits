from fastapi import APIRouter

from api.auth.routes import router as auth_router
from api.tenant.routes import router as tenant_router
from api.onboarding.routes import router as onboarding_router
from api.user.routes import router as user_router
from api.runtime.routes import router as runtime_router
from api.document.routes import router as document_router
from api.chat.routes import router as chat_router
from api.company.routes import router as company_router
from api.prompt.routes import router as prompt_router
from api.scoring.routes import router as scoring_router
from api.connector import quickbooks_router, carbonvoice_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(tenant_router, prefix="/tenants", tags=["tenants"])
api_router.include_router(onboarding_router, prefix="/onboarding", tags=["onboarding"])
api_router.include_router(user_router, prefix="/users", tags=["users"])
api_router.include_router(runtime_router, prefix="/runtime", tags=["runtime"])
api_router.include_router(document_router, prefix="/documents", tags=["documents"])
api_router.include_router(chat_router, prefix="/chat", tags=["chat"])
api_router.include_router(company_router, prefix="/companies", tags=["companies"])
api_router.include_router(prompt_router, prefix="/prompts", tags=["prompts"])
api_router.include_router(scoring_router, prefix="/scoring", tags=["scoring"])
api_router.include_router(quickbooks_router, prefix="/connectors/quickbooks", tags=["quickbooks"])
api_router.include_router(carbonvoice_router, prefix="/connectors/carbonvoice", tags=["carbonvoice"])
