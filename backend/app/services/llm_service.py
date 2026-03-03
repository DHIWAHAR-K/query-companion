"""LLM service - abstraction layer for multiple LLM providers"""
import structlog
from typing import Dict, Any, Optional, List
from anthropic import AsyncAnthropic
import google.generativeai as genai
from langchain_core.messages import BaseMessage
from langchain_core.language_models import BaseChatModel
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    MessagesPlaceholder,
    HumanMessagePromptTemplate,
)

from app.config import settings

logger = structlog.get_logger()


class LLMService:
    """
    Abstraction layer for LLM providers.
    Supports both Anthropic Claude and Google Gemini.
    """
    
    def __init__(self, provider: str = None):
        self.provider = provider or settings.LLM_PROVIDER
        
        if self.provider == "anthropic":
            if not settings.ANTHROPIC_API_KEY:
                raise ValueError("ANTHROPIC_API_KEY is required when using Anthropic provider")
            self.claude_client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        elif self.provider == "google":
            if not settings.GOOGLE_API_KEY:
                raise ValueError("GOOGLE_API_KEY is required when using Google provider")
            genai.configure(api_key=settings.GOOGLE_API_KEY)
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")
        
        logger.info("LLM service initialized", provider=self.provider)
    
    # Deprecated Gemini model IDs that return 404 on v1beta; map to current stable IDs
    _GEMINI_MODEL_FALLBACK = {
        "gemini-1.5-pro": "gemini-2.5-flash",
        "gemini-1.5-flash": "gemini-2.5-flash-lite",
        "gemini-1.5-pro-latest": "gemini-2.5-flash",
        "gemini-1.5-flash-latest": "gemini-2.5-flash-lite",
    }

    def get_model_name(self, mode: str) -> str:
        """Get model name for the specified performance mode"""
        if self.provider == "anthropic":
            mapping = {
                "valtryek": settings.VALTRYEK_MODEL,
                "achillies": settings.ACHILLIES_MODEL,
                "spryzen": settings.SPRYZEN_MODEL,
            }
        elif self.provider == "google":
            mapping = {
                "valtryek": settings.GOOGLE_VALTRYEK_MODEL,
                "achillies": settings.GOOGLE_ACHILLIES_MODEL,
                "spryzen": settings.GOOGLE_SPRYZEN_MODEL,
            }
        result = mapping.get(mode, mapping["achillies"])
        if self.provider == "google" and result in self._GEMINI_MODEL_FALLBACK:
            result = self._GEMINI_MODEL_FALLBACK[result]
        return result
    
    async def generate_sql(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        max_tokens: int = 2048
    ) -> str:
        """
        Generate SQL using the configured LLM provider.
        
        Args:
            system_prompt: System instructions
            user_prompt: User query with schema context
            model: Model name to use
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text response
        """
        if self.provider == "anthropic":
            return await self._generate_with_claude(
                system_prompt, user_prompt, model, max_tokens
            )
        elif self.provider == "google":
            return await self._generate_with_gemini(
                system_prompt, user_prompt, model, max_tokens
            )
    
    async def _generate_with_claude(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        max_tokens: int
    ) -> str:
        """Generate using Anthropic Claude"""
        logger.debug("Generating with Claude", model=model)
        
        response = await self.claude_client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )
        
        return response.content[0].text
    
    async def _generate_with_gemini(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        max_tokens: int
    ) -> str:
        """Generate using Google Gemini"""
        logger.debug("Generating with Gemini", model=model)
        
        # Combine system and user prompts for Gemini
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        
        # Create model
        gemini_model = genai.GenerativeModel(
            model_name=model,
            generation_config={
                "max_output_tokens": max_tokens,
                "temperature": 0.7,
            }
        )
        
        # Generate content
        response = await gemini_model.generate_content_async(full_prompt)
        
        return response.text
    
    async def generate_with_tools(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        tools: list,
        max_tokens: int = 1024
    ) -> tuple[str, list]:
        """
        Generate with tool use capability.
        
        Returns:
            Tuple of (response_text, tool_calls)
        """
        if self.provider == "anthropic":
            return await self._generate_with_claude_tools(
                system_prompt, user_prompt, model, tools, max_tokens
            )
        elif self.provider == "google":
            # Gemini also supports function calling
            return await self._generate_with_gemini_tools(
                system_prompt, user_prompt, model, tools, max_tokens
            )
    
    async def _generate_with_claude_tools(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        tools: list,
        max_tokens: int
    ) -> tuple[str, list]:
        """Claude tool use"""
        response = await self.claude_client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_prompt,
            tools=tools,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )
        
        tool_calls = []
        response_text = ""
        
        for content_block in response.content:
            if content_block.type == "text":
                response_text = content_block.text
            elif content_block.type == "tool_use":
                tool_calls.append({
                    "name": content_block.name,
                    "input": content_block.input
                })
        
        return response_text, tool_calls
    
    async def _generate_with_gemini_tools(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        tools: list,
        max_tokens: int
    ) -> tuple[str, list]:
        """Gemini function calling"""
        # Convert Claude tool format to Gemini function declaration format
        gemini_tools = []
        for tool in tools:
            gemini_tools.append({
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["input_schema"]
            })
        
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        
        gemini_model = genai.GenerativeModel(
            model_name=model,
            generation_config={"max_output_tokens": max_tokens},
            tools=gemini_tools
        )
        
        response = await gemini_model.generate_content_async(full_prompt)
        
        tool_calls = []
        response_text = ""
        
        # Parse function calls from response
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'text'):
                    response_text = part.text
                elif hasattr(part, 'function_call'):
                    tool_calls.append({
                        "name": part.function_call.name,
                        "input": dict(part.function_call.args)
                    })
        
        return response_text, tool_calls
    
    def get_lc_model(self, model_name: str) -> BaseChatModel:
        """Return a LangChain chat model for the given model name."""
        if self.provider == "anthropic":
            return ChatAnthropic(
                api_key=settings.ANTHROPIC_API_KEY,
                model=model_name,
                max_tokens=2048,
            )
        return ChatGoogleGenerativeAI(
            google_api_key=settings.GOOGLE_API_KEY,
            model=model_name,
            max_output_tokens=2048,
        )

    async def generate_sql_with_history(
        self,
        system_prompt: str,
        lc_history: List[BaseMessage],
        user_prompt: str,
        model: str,
        max_tokens: int = 2048,
    ) -> str:
        """History-aware SQL generation using LangChain ChatPromptTemplate."""
        prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template("{system}"),
            MessagesPlaceholder(variable_name="history"),
            HumanMessagePromptTemplate.from_template("{question}"),
        ])
        chain = prompt | self.get_lc_model(model)
        result = await chain.ainvoke({
            "system": system_prompt,
            "history": lc_history,
            "question": user_prompt,
        })
        return result.content

    async def extract_from_image(
        self,
        image_data: bytes,
        prompt: str,
        model: str
    ) -> str:
        """
        Extract information from image using vision capabilities.
        
        Args:
            image_data: Base64 encoded image
            prompt: Instruction prompt
            model: Model name
            
        Returns:
            Extracted text
        """
        if self.provider == "anthropic":
            return await self._extract_with_claude_vision(image_data, prompt, model)
        elif self.provider == "google":
            return await self._extract_with_gemini_vision(image_data, prompt, model)
    
    async def _extract_with_claude_vision(
        self,
        image_data: bytes,
        prompt: str,
        model: str
    ) -> str:
        """Claude vision"""
        import base64
        
        if isinstance(image_data, bytes):
            image_b64 = base64.b64encode(image_data).decode('utf-8')
        else:
            image_b64 = image_data
        
        response = await self.claude_client.messages.create(
            model=model,
            max_tokens=2048,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": image_b64
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
        )
        
        return response.content[0].text
    
    async def _extract_with_gemini_vision(
        self,
        image_data: bytes,
        prompt: str,
        model: str
    ) -> str:
        """Gemini vision"""
        import PIL.Image
        import io
        
        # Convert bytes to PIL Image
        image = PIL.Image.open(io.BytesIO(image_data))
        
        gemini_model = genai.GenerativeModel(model_name=model)
        
        response = await gemini_model.generate_content_async([prompt, image])
        
        return response.text
