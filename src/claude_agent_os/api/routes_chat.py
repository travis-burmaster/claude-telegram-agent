"""Chat API routes — send prompts to Claude."""

import uuid

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/")
async def chat(request: Request):
    """Send a prompt to Claude via the agent spawner."""
    body = await request.json()
    prompt = body.get("prompt", "")
    workspace = body.get("workspace")
    model = body.get("model")

    if not prompt:
        return JSONResponse({"error": "prompt is required"}, status_code=400)

    pool = request.app.state.agent_pool
    task_id = f"chat-{uuid.uuid4().hex[:8]}"

    try:
        result = await pool.spawn(
            task_id=task_id,
            prompt=prompt,
            workspace=workspace,
            model=model,
        )
        return JSONResponse({
            "task_id": result.task_id,
            "output": result.output,
            "exit_code": result.exit_code,
            "duration": result.duration,
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
