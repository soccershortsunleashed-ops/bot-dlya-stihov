import asyncio
from functools import partial
import google.generativeai as genai
import logging
import re
from typing import List
from app.infra.config.settings import settings

logger = logging.getLogger(__name__)

class GeminiProvider:
    provider_key = "gemini"

    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-flash-latest')

    async def list_models(self) -> List[str]:
        try:
            loop = asyncio.get_event_loop()
            # genai.list_models() is a blocking call, run it in executor
            models_iter = await loop.run_in_executor(None, genai.list_models)
            
            models = []
            for m in models_iter:
                if 'generateContent' in m.supported_generation_methods:
                    models.append(m.name.replace('models/', ''))
            return sorted(models)
        except Exception as e:
            logger.error(f"Error listing Gemini models: {e}")
            return ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash-exp"]

    async def generate_poem(self, prompt: str, params: dict) -> str:
        try:
            max_tokens = params.get("max_tokens", 2048)
            logger.info(f"Generating poem with params: {params}, max_output_tokens: {max_tokens}")
            
            generation_config = genai.types.GenerationConfig(
                candidate_count=1,
                max_output_tokens=max_tokens,
                temperature=params.get("temperature", 0.7),
            )
            
            response = await self.model.generate_content_async(prompt, generation_config=generation_config)
            
            logger.info(f"Gemini response finish reason: {response.candidates[0].finish_reason}")
            
            if response.text:
                text = response.text
                # Clean up potential HTML/Markdown artifacts
                text = re.sub(r'```(?:html|markdown)?', '', text)
                text = re.sub(r'</?blockquote>', '', text, flags=re.IGNORECASE)
                text = re.sub(r'</?blockquote>', '', text, flags=re.IGNORECASE)
                return text.strip()
            return ""
            
        except Exception as e:
            logger.error(f"Error generating content with Gemini: {e}")
            raise