"""
LiteLLM pre-call hook: strips image_url content parts from messages.

WebStorm's Copilot plugin sends image_url content parts in messages even when
vision is disabled. This hook converts multi-part messages to plain text by
dropping image_url parts and keeping only text parts.
"""

from litellm.integrations.custom_logger import CustomLogger
from litellm.types.utils import ModelResponse
from typing import Any, Optional


class StripImageUrlHook(CustomLogger):
    async def async_pre_call_hook(
        self,
        user_api_key_dict: Any,
        cache: Any,
        data: dict,
        call_type: str,
    ) -> dict:
        if call_type != "completion" or "messages" not in data:
            return data

        cleaned: list = []
        for msg in data["messages"]:
            content = msg.get("content")

            # If content is a list of parts, filter out image_url parts
            if isinstance(content, list):
                text_parts = [
                    part for part in content
                    if isinstance(part, dict) and part.get("type") != "image_url"
                ]
                if not text_parts:
                    # All parts were images — drop the whole message
                    continue
                # If only one text part remains, unwrap it to a plain string
                if len(text_parts) == 1 and text_parts[0].get("type") == "text":
                    msg = {**msg, "content": text_parts[0]["text"]}
                else:
                    msg = {**msg, "content": text_parts}

            cleaned.append(msg)

        data["messages"] = cleaned
        return data


# LiteLLM discovers this instance by name when listed in litellm_config.yaml
strip_image_url_hook = StripImageUrlHook()

