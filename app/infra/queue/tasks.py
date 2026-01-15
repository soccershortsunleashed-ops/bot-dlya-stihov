import asyncio
from typing import List
from uuid import UUID
from celery import shared_task
from app.infra.queue.celery_app import celery_app
from app.infra.db.session import async_session_factory
from app.infra.db.repositories.order_repo import OrderRepo
from app.infra.db.repositories.stage_repo import StageRepo
from app.infra.db.repositories.artifact_repo import ArtifactRepo
from app.infra.db.repositories.config_repo import ConfigRepo
from app.infra.ai.yandex_gpt import YandexGPTProvider
from app.infra.ai.test_provider import DummyTextProvider
from app.infra.ai.gemini import GeminiProvider
from app.infra.ai.openai import OpenAIProvider
from app.infra.ai.speechkit import SpeechKitProvider
from app.infra.storage.s3 import S3Storage
from app.infra.config.settings import settings
from app.application.services.prompt_builder import PromptBuilder
from app.application.services.content_policy import ContentPolicy
from app.domain.enums import OrderStageStatus, ArtifactType, ProviderKind, StageType
import logging

logger = logging.getLogger(__name__)

def get_provider(kind: ProviderKind, api_key: str = None):
    if kind == ProviderKind.YANDEX_GPT:
        return YandexGPTProvider(api_key=api_key)
    if kind == ProviderKind.GEMINI:
        return GeminiProvider(api_key=api_key)
    if kind == ProviderKind.OPENAI:
        return OpenAIProvider(api_key=api_key)
    if kind == ProviderKind.SPEECHKIT:
        return SpeechKitProvider(api_key=api_key)
    return DummyTextProvider()

async def _generate_poem_logic(stage_id: str):
    async with async_session_factory() as session:
        stage_repo = StageRepo(session)
        order_repo = OrderRepo(session)
        artifact_repo = ArtifactRepo(session)
        config_repo = ConfigRepo(session)
        
        stage = await stage_repo.get_by_id(UUID(stage_id))
        if not stage:
            logger.error(f"Stage {stage_id} not found")
            return

        if stage.status != OrderStageStatus.PAID and stage.status != OrderStageStatus.QUEUED:
            logger.warning(f"Stage {stage_id} has invalid status for generation: {stage.status}")
            return

        order = await order_repo.get_by_id(stage.order_id)
        
        # Обновляем статус на PROCESSING
        stage.status = OrderStageStatus.PROCESSING
        await session.commit()

        try:
            logger.info(f"Starting poem generation for stage {stage_id}")

            # Получаем конфиг провайдера для этапа POEM
            cfg = await config_repo.get_provider_config(StageType.POEM)
            
            if not cfg or not cfg.api_key_encrypted:
                # Fallback to settings if no DB config found
                if not settings.GEMINI_API_KEY:
                    raise ValueError("No provider configuration found for POEM and no fallback GEMINI_API_KEY")
                provider = GeminiProvider(api_key=settings.GEMINI_API_KEY.get_secret_value())
                provider_params = {"model": "gemini-1.5-flash"}
            else:
                api_key = config_repo.decrypt_api_key(cfg.api_key_encrypted)
                provider = get_provider(cfg.provider_kind, api_key=api_key)
                provider_params = {"model": cfg.model}
            
            # Собираем промпт
            prompt_builder = PromptBuilder()
            prompt = prompt_builder.build_poem_prompt(order.context_json)
            
            logger.info(f"Generated prompt: {prompt}")

            # Генерируем
            poem_text = await provider.generate_poem(prompt, provider_params)
            
            logger.info(f"Raw provider response: {poem_text}")
            
            # Проверяем контент-политику
            policy_cfg = await config_repo.get_content_policy("poem_rules")
            stop_words = policy_cfg.rules_json.get("stop_words", []) if policy_cfg else []
            content_policy = ContentPolicy(stop_words=stop_words)
            
            if not content_policy.is_appropriate(poem_text):
                raise ValueError("Generated content violates content policy")

            # Сохраняем артефакт
            from app.infra.db.models import Artifact
            artifact = Artifact(
                order_id=order.id,
                stage_id=stage.id,
                type=ArtifactType.TEXT,
                storage_key=poem_text # Для текста храним прямо в поле или в storage_key если так решили в Итерации 1
            )
            # В модели Artifact в Итерации 1 было storage_key. 
            # Согласно РоудМэп.md в artifacts есть поле text (null) - для стихов.
            # Но в текущей app/infra/db/models.py поля text нет. 
            # Буду использовать storage_key как временное хранилище текста или проверю модель еще раз.
            # Перечитаю models.py... Там только storage_key.
            
            session.add(artifact)
            stage.status = OrderStageStatus.COMPLETED
            await session.commit()
            logger.info(f"Poem generated successfully for stage {stage_id}")

        except Exception as e:
            logger.exception(f"Error generating poem for stage {stage_id}: {e}")
            stage.status = OrderStageStatus.FAILED
            await session.commit()
            raise

@celery_app.task(name="generate_poem_task", bind=True, max_retries=3)
def generate_poem_task(self, stage_id: str):
    return asyncio.run(_generate_poem_logic(stage_id))

async def _generate_voice_logic(stage_id: str):
    async with async_session_factory() as session:
        stage_repo = StageRepo(session)
        artifact_repo = ArtifactRepo(session)
        config_repo = ConfigRepo(session)
        
        stage = await stage_repo.get_by_id(UUID(stage_id))
        if not stage or stage.stage_type != StageType.VOICE:
            logger.error(f"Invalid stage for voice generation: {stage_id}")
            return

        if stage.status not in [OrderStageStatus.PAID, OrderStageStatus.QUEUED]:
            logger.warning(f"Stage {stage_id} has invalid status: {stage.status}")
            return

        stage.status = OrderStageStatus.PROCESSING
        await session.commit()

        try:
            # 1. Получаем текст стиха
            text_artifact = await artifact_repo.get_latest_text_artifact(stage.order_id)
            if not text_artifact:
                raise ValueError(f"No text artifact found for order {stage.order_id}")
            
            poem_text = text_artifact.storage_key # Текст хранится в storage_key

            # 2. Получаем конфиг SpeechKit
            cfg = await config_repo.get_provider_config(StageType.VOICE)
            if not cfg or cfg.provider_kind != ProviderKind.SPEECHKIT:
                # Fallback to settings
                api_key = settings.SPEECHKIT_API_KEY.get_secret_value() if settings.SPEECHKIT_API_KEY else None
                provider = SpeechKitProvider(api_key=api_key)
                provider_params = {"model": "filipp"}
            else:
                api_key = config_repo.decrypt_api_key(cfg.api_key_encrypted)
                provider = get_provider(cfg.provider_kind, api_key=api_key)
                provider_params = {"model": cfg.model}

            # 3. Синтезируем
            logger.info(f"Synthesizing voice for stage {stage_id} with voice {provider_params['model']}")
            audio_content = await provider.synthesize(poem_text, provider_params)

            # 4. Сохраняем в S3
            s3 = S3Storage()
            s3_key = f"orders/{stage.order_id}/voice_{stage.id}.mp3"
            uploaded_key = await s3.upload_file(audio_content, s3_key)
            
            if not uploaded_key:
                raise ValueError("Failed to upload audio to S3 (check credentials)")

            # 5. Создаем артефакт
            from app.infra.db.models import Artifact
            artifact = Artifact(
                order_id=stage.order_id,
                stage_id=stage.id,
                type=ArtifactType.AUDIO,
                storage_key=uploaded_key
            )
            session.add(artifact)
            
            stage.status = OrderStageStatus.COMPLETED
            await session.commit()
            logger.info(f"Voice generated successfully for stage {stage_id}")

        except Exception as e:
            logger.exception(f"Error generating voice for stage {stage_id}: {e}")
            stage.status = OrderStageStatus.FAILED
            await session.commit()
            raise

@celery_app.task(name="generate_voice_task", bind=True, max_retries=3)
def generate_voice_task(self, stage_id: str):
    return asyncio.run(_generate_voice_logic(stage_id))

async def _sync_provider_models_logic():
    async with async_session_factory() as session:
        config_repo = ConfigRepo(session)
        configs = await config_repo.get_all_provider_configs()
        
        from app.infra.ai.gemini import GeminiProvider
        from app.infra.ai.yandex_gpt import YandexGPTProvider
        from app.infra.ai.openai import OpenAIProvider
        from app.infra.ai.speechkit import SpeechKitProvider
        
        for cfg in configs:
            if not cfg.api_key_encrypted:
                continue
                
            try:
                api_key = config_repo.decrypt_api_key(cfg.api_key_encrypted)
                provider_inst = None
                if cfg.provider_kind == ProviderKind.GEMINI:
                    provider_inst = GeminiProvider(api_key=api_key)
                elif cfg.provider_kind == ProviderKind.YANDEX_GPT:
                    provider_inst = YandexGPTProvider(api_key=api_key)
                elif cfg.provider_kind == ProviderKind.OPENAI:
                    provider_inst = OpenAIProvider(api_key=api_key)
                elif cfg.provider_kind == ProviderKind.SPEECHKIT:
                    provider_inst = SpeechKitProvider(api_key=api_key)
                
                if provider_inst and hasattr(provider_inst, 'list_models'):
                    models = await provider_inst.list_models()
                    cfg.models_cache = models
                    from sqlalchemy import func
                    cfg.models_cache_updated_at = func.now()
                    
                    # Auto-fix model if current is missing
                    if cfg.model and models and cfg.model not in models:
                        logger.warning(f"Model {cfg.model} for {cfg.stage_type} disappeared from provider. Switching to {models[0]}")
                        cfg.model = models[0]
                    
                    cfg.status = "active"
            except Exception as e:
                logger.error(f"Error syncing models for {cfg.stage_type}: {e}")
                cfg.status = "error"
        
        await session.commit()

@celery_app.task(name="sync_provider_models_task")
def sync_provider_models_task():
    return asyncio.run(_sync_provider_models_logic())