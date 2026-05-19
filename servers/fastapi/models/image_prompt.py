from typing import Optional
from pydantic import BaseModel


class ImagePrompt(BaseModel):
    prompt: str
    theme_prompt: Optional[str] = None
    persona_suffix: Optional[str] = None

    def get_image_prompt(self, with_theme: bool = False) -> str:
        parts = [self.prompt]
        if with_theme and self.theme_prompt:
            parts.append(self.theme_prompt)
        if with_theme and self.persona_suffix:
            parts.append(self.persona_suffix)
        return ", ".join(parts)
