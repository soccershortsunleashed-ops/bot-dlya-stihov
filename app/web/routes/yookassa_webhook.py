from fastapi import APIRouter, Request, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.application.dto.schemas import PaymentWebhook
from app.infra.payments.yookassa import YooKassaClient
from app.web.deps import get_session, get_handle_webhook_use_case
from app.application.use_cases.handle_yookassa_webhook import HandleYookassaWebhookUseCase
import structlog

logger = structlog.get_logger()
router = APIRouter()
yookassa_client = YooKassaClient()

@router.post("/yookassa")
async def yookassa_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """
    Принимает вебхуки от ЮKassa.
    """
    # 1. Проверка IP
    client_ip = request.client.host if request.client else "unknown"
    if not yookassa_client.is_valid_webhook_ip(client_ip):
        logger.warning("webhook_invalid_ip", ip=client_ip)
    
    payload = await request.json()
    logger.info("yookassa_webhook_received", payload=payload)
    
    try:
        PaymentWebhook(**payload)
    except Exception as e:
        logger.error("webhook_parse_error", error=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payload")

    # Вызываем Use Case
    use_case = await get_handle_webhook_use_case(session)
    await use_case.execute(payload)
    
    return {"status": "ok"}