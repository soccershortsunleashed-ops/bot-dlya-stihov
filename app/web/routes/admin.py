from uuid import UUID
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import RedirectResponse
from starlette.datastructures import URL
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select, func
import sqlalchemy as sa
from typing import List

from app.web.auth import get_admin_user
from app.web.deps import get_session
from app.infra.db.models import Order, OrderStage, User, ProductConfig, ProviderConfig, APIKey, Payment
from app.domain.enums import OrderStageStatus, OrderStatus, PaymentStatus, StageType, ProviderKind
from app.infra.utils.crypto import encryption_service
from app.web import texts

router = APIRouter()
templates = Jinja2Templates(directory="app/web/templates")
templates.env.globals["texts"] = texts
templates.env.globals["STATUS_LABELS"] = texts.STATUS_LABELS

def redirect_back(request: Request, fallback_url: str):
    referer = request.headers.get("referer")
    if referer:
        url = URL(referer).include_query_params(saved="1")
    else:
        url = URL(fallback_url).include_query_params(saved="1")
    return RedirectResponse(url=str(url), status_code=303)


@router.get("/")
async def admin_root():
    # Перенаправление с /admin/ на /admin/dashboard
    return RedirectResponse(url="/admin/dashboard", status_code=302)

@router.get("/dashboard")
async def dashboard(
    request: Request,
    admin: str = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session)
):
    # Статистика для дашборда
    total_users = await session.scalar(select(func.count(User.id)))
    total_orders = await session.scalar(select(func.count(Order.id)))
    total_revenue_cents = await session.scalar(
        select(func.sum(Payment.amount))
        .join(Order, Payment.order_id == Order.id)
        .where(
            Payment.status == PaymentStatus.SUCCEEDED,
            Order.status == OrderStatus.PAID,
            Payment.currency == "RUB"
        )
    ) or 0
    total_revenue = total_revenue_cents / 100
     
    recent_orders = (await session.execute(
        select(Order).order_by(Order.created_at.desc()).limit(5)
    )).scalars().all()

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "total_users": total_users,
        "total_orders": total_orders,
        "total_revenue": total_revenue,
        "recent_orders": recent_orders
    })

@router.get("/products")
async def products_list(
    request: Request, 
    admin: str = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session)
):
    products = (await session.execute(select(ProductConfig))).scalars().all()
    return templates.TemplateResponse("products.html", {"request": request, "products": products})

@router.get("/providers")
async def providers_list(
    request: Request,
    admin: str = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session)
):
    # Get all configs
    configs_result = await session.execute(select(ProviderConfig))
    configs = {c.stage_type: c for c in configs_result.scalars().all()}
    
    # Ensure all StageTypes exist in the UI data
    ui_configs = {}
    for st in StageType:
        cfg = configs.get(st)
        ui_configs[st] = {
            "stage_type": st,
            "provider_kind": cfg.provider_kind if cfg else "DUMMY",
            "model": cfg.model if cfg else "Не выбрана",
            "models_cache": cfg.models_cache if cfg and cfg.models_cache else [],
            "status": cfg.status if cfg else "unknown",
            "api_key_set": bool(cfg and cfg.api_key_encrypted)
        }

    # Allowed providers matrix
    ALLOWED_PROVIDERS = {
        StageType.POEM: [ProviderKind.YANDEX_GPT, ProviderKind.GEMINI, ProviderKind.OPENAI],
        StageType.VOICE: [ProviderKind.SPEECHKIT],
        StageType.SONG: [ProviderKind.SUNO],
        StageType.CLIP: [ProviderKind.PIKA]
    }

    # History of keys (from api_keys table)
    api_keys_result = await session.execute(select(APIKey).order_by(APIKey.created_at.desc()))
    api_keys_ui = []
    for key in api_keys_result.scalars().all():
        api_keys_ui.append({
            "id": str(key.id),
            "masked": f"{key.key_value[:4]}****{key.key_value[-4:]}" if len(key.key_value) > 8 else "****",
            "status": key.status,
            "is_active": key.is_active,
            "created_at": key.created_at.strftime("%Y-%m-%d %H:%M")
        })

    return templates.TemplateResponse("providers.html", {
        "request": request,
        "configs": ui_configs,
        "allowed_providers": ALLOWED_PROVIDERS,
        "api_keys": api_keys_ui,
        "StageType": StageType
    })

@router.get("/orders")
async def orders_list(
    request: Request,
    admin: str = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session)
):
    orders = (await session.execute(
        select(Order).order_by(Order.created_at.desc())
    )).scalars().all()
    return templates.TemplateResponse("orders.html", {"request": request, "orders": orders})

@router.get("/orders/{order_id}")
async def order_detail(
    order_id: UUID,
    request: Request,
    admin: str = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session)
):
    order = await session.scalar(
        select(Order)
        .where(Order.id == order_id)
        .options(selectinload(Order.stages))
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return templates.TemplateResponse("order_detail.html", {"request": request, "order": order})

@router.post("/stages/{stage_id}/requeue")
async def requeue_stage(
    request: Request,
    stage_id: UUID,
    admin: str = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session)
):
    stage = await session.get(OrderStage, stage_id)
    if stage:
        stage.status = OrderStageStatus.PENDING
        await session.commit()
        # В реальной системе здесь бы вызывался enqueue_stage_job_uc
    return redirect_back(request, "/admin/orders")

@router.post("/stages/{stage_id}/cancel")
async def cancel_stage(
    request: Request,
    stage_id: UUID,
    admin: str = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session)
):
    stage = await session.get(OrderStage, stage_id)
    if stage:
        stage.status = OrderStageStatus.CANCELLED
        await session.commit()
    return redirect_back(request, "/admin/orders")

@router.post("/products/update")
async def update_product(
    request: Request,
    key: str = Form(...),
    price: float = Form(...),
    title: str = Form(...),
    enabled: bool = Form(False),
    admin: str = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session)
):
    product = await session.scalar(select(ProductConfig).where(ProductConfig.key == key))
    if product:
        product.value_json = {
            "price": int(price * 100),
            "title": title,
            "enabled": enabled
        }
        await session.commit()
    return redirect_back(request, "/admin/products")

@router.post("/providers/update")
async def update_provider(
    request: Request,
    stage_type: StageType = Form(...),
    kind: ProviderKind = Form(...),
    api_key: str = Form(None),
    model: str = Form(None),
    admin: str = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session)
):
    import logging
    logger = logging.getLogger(__name__)
    
    # 1. Get or create config for this StageType
    cfg = await session.scalar(select(ProviderConfig).where(ProviderConfig.stage_type == stage_type))
    if not cfg:
        cfg = ProviderConfig(
            stage_type=stage_type,
            provider_kind=kind,
            config_json={},
            is_active=True
        )
        session.add(cfg)
        # Flush to get the ID for new config before using it in APIKey
        await session.flush()
    else:
        cfg.provider_kind = kind

    # 2. Update API Key if provided
    if api_key:
        cfg.api_key_encrypted = encryption_service.encrypt(api_key)
        
        # Deactivate previous keys in history for this provider config
        if cfg.id:
            await session.execute(
                sa.update(APIKey).where(APIKey.provider_id == cfg.id).values(is_active=False)
            )

        # Also save to history
        new_history_key = APIKey(
            provider_id=cfg.id,
            key_value=api_key,
            is_active=True,
            status="active"
        )
        session.add(new_history_key)

    # 3. Fetch models if key is present (or was just updated)
    current_key = api_key
    if not current_key and cfg.api_key_encrypted:
        current_key = encryption_service.decrypt(cfg.api_key_encrypted)

    if current_key:
        try:
            from app.infra.ai.gemini import GeminiProvider
            from app.infra.ai.yandex_gpt import YandexGPTProvider
            from app.infra.ai.openai import OpenAIProvider
            from app.infra.ai.speechkit import SpeechKitProvider
            
            provider_inst = None
            if kind == ProviderKind.GEMINI:
                provider_inst = GeminiProvider(api_key=current_key)
            elif kind == ProviderKind.YANDEX_GPT:
                provider_inst = YandexGPTProvider(api_key=current_key)
            elif kind == ProviderKind.OPENAI:
                provider_inst = OpenAIProvider(api_key=current_key)
            elif kind == ProviderKind.SPEECHKIT:
                provider_inst = SpeechKitProvider(api_key=current_key)
            
            if provider_inst and hasattr(provider_inst, 'list_models'):
                models = await provider_inst.list_models()
                cfg.models_cache = models
                cfg.models_cache_updated_at = sa.func.now()
                cfg.status = "active"
                
                # Auto-select first model if none selected or current not in list
                if not model or (models and model not in models):
                    if models:
                        cfg.model = models[0]
                else:
                    cfg.model = model
        except Exception as e:
            logger.error(f"Error fetching models for {kind}: {e}")
            cfg.status = "error"
    
    if model and cfg.models_cache and model in cfg.models_cache:
        cfg.model = model

    await session.commit()
    return redirect_back(request, "/admin/providers")