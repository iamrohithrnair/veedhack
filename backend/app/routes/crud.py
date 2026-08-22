import asyncio
import os
import tempfile
from pathlib import Path

import fal_client
from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile, status

from app import db
from app.config import get_settings
from app.models import AvatarCreate, AvatarGenerate, ProjectCreate, ProjectPatch, TemplateCreate
from app.routes.render import _find_url, _valid_url

router = APIRouter(prefix="/api")


@router.get("/projects")
async def list_projects() -> list[dict]:
    return await db.list_rows("projects")


@router.post("/projects", status_code=status.HTTP_201_CREATED)
async def create_project(body: ProjectCreate) -> dict:
    return await db.create_project(body.model_dump())


@router.get("/projects/{project_id}")
async def get_project(project_id: str) -> dict:
    project = await db.get_project_with_events(project_id)
    if project is None:
        raise HTTPException(404, "Project not found")
    return project


@router.patch("/projects/{project_id}")
async def patch_project(project_id: str, body: ProjectPatch) -> dict:
    if await db.get_row("projects", project_id) is None:
        raise HTTPException(404, "Project not found")
    return await db.update_project(project_id, body.model_dump(exclude_unset=True))  # type: ignore[return-value]


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project_id: str) -> Response:
    if not await db.delete_row("projects", project_id):
        raise HTTPException(404, "Project not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/avatars")
async def list_avatars() -> list[dict]:
    return await db.list_rows("avatars")


@router.post("/avatars", status_code=status.HTTP_201_CREATED)
async def create_avatar(body: AvatarCreate) -> dict:
    data = body.model_dump(mode="json")
    return await db.insert_named_resource("avatars", data)


@router.post("/avatars/generate", status_code=status.HTTP_201_CREATED)
async def generate_avatar(body: AvatarGenerate) -> dict:
    settings = get_settings()
    fal_key = settings.require("fal_key")
    os.environ["FAL_KEY"] = fal_key

    full_prompt = (
        "Photorealistic charismatic presenter, centered waist-up portrait, clean studio lighting, direct eye contact, "
        f"personality and character: {body.prompt}"
    )
    try:
        result = await asyncio.wait_for(
            fal_client.subscribe_async(
                settings.fal_image_model,
                arguments={"prompt": full_prompt, "num_images": 1},
                with_logs=True,
            ),
            timeout=settings.pipeline_timeout_seconds,
        )
    except Exception as error:
        raise HTTPException(502, f"Avatar generation failed: {error}") from error

    image_url = _find_url(result, ("url", "images", "image"))
    if not image_url or not _valid_url(image_url):
        raise HTTPException(502, "Avatar generation returned no valid image URL")

    return await db.insert_named_resource(
        "avatars",
        {
            "name": body.name,
            "vibe": body.vibe or body.prompt,
            "image_url": image_url,
            "metadata": {"prompt": body.prompt, "generated": True},
        },
    )


@router.post("/avatars/upload", status_code=status.HTTP_201_CREATED)
async def upload_avatar(
    name: str = Form(..., min_length=1, max_length=200),
    vibe: str | None = Form(None),
    image_file: UploadFile = File(...),
) -> dict:
    settings = get_settings()
    fal_key = settings.require("fal_key")
    os.environ["FAL_KEY"] = fal_key

    if image_file.content_type and not image_file.content_type.startswith("image/"):
        raise HTTPException(415, "image_file must be an image upload")

    suffix = Path(image_file.filename or "avatar.png").suffix or ".png"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp:
        temp_path = Path(temp.name)
        while chunk := await image_file.read(1024 * 1024):
            temp.write(chunk)

    try:
        image_url = await fal_client.upload_file_async(str(temp_path))
        if not image_url or not _valid_url(image_url):
            raise HTTPException(502, "Failed to upload avatar image to storage")
        return await db.insert_named_resource(
            "avatars",
            {
                "name": name,
                "vibe": vibe or name,
                "image_url": image_url,
                "metadata": {"uploaded": True, "filename": image_file.filename},
            },
        )
    except Exception as error:
        raise HTTPException(502, f"Avatar upload failed: {error}") from error
    finally:
        temp_path.unlink(missing_ok=True)
        await image_file.close()


@router.delete("/avatars/{avatar_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_avatar(avatar_id: str) -> Response:
    if not await db.delete_row("avatars", avatar_id):
        raise HTTPException(404, "Avatar not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/templates")
async def list_templates() -> list[dict]:
    return await db.list_rows("templates")


@router.post("/templates", status_code=status.HTTP_201_CREATED)
async def create_template(body: TemplateCreate) -> dict:
    return await db.insert_named_resource("templates", body.model_dump())


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(template_id: str) -> Response:
    template = await db.get_row("templates", template_id)
    if template is None:
        raise HTTPException(404, "Template not found")
    if template["built_in"]:
        raise HTTPException(409, "Built-in templates cannot be deleted")
    await db.delete_row("templates", template_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/dashboard/stats")
async def get_dashboard_stats() -> dict:
    return await db.dashboard_stats()


@router.get("/wallet")
async def get_wallet() -> dict:
    wallet = await db.get_row("wallet", 1)
    if wallet is None:
        raise HTTPException(500, "Wallet was not initialized")
    return wallet
