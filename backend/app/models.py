from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    target_prompt: str | None = None
    avatar_vibe: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProjectPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    target_prompt: str | None = None
    avatar_vibe: str | None = None
    status: str | None = None
    metadata: dict[str, Any] | None = None


class AvatarCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    vibe: str | None = None
    image_url: HttpUrl
    metadata: dict[str, Any] = Field(default_factory=dict)


class AvatarGenerate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    prompt: str = Field(min_length=3, max_length=1000)
    vibe: str | None = None


class TemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    prompt: dict[str, Any]
    metadata: dict[str, Any] = Field(default_factory=dict)


class ScriptRequest(BaseModel):
    target_prompt: str = Field(min_length=3, max_length=5000)
    avatar_vibe: str | None = Field(default=None, max_length=500)
    project_id: str | None = None


class RenderMode(BaseModel):
    mode: Literal["move", "replace"]
