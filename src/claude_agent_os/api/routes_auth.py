"""Authentication routes — login / logout."""

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse

from claude_agent_os.auth import (
    verify_password,
    create_session,
    destroy_session,
)

router = APIRouter(tags=["auth"])


@router.post("/login")
async def login(request: Request):
    """Validate password, set session cookie, return redirect."""
    content_type = request.headers.get("content-type", "")

    if "application/json" in content_type:
        body = await request.json()
        password = body.get("password", "")
    else:
        form = await request.form()
        password = form.get("password", "")

    cfg = request.app.state.config
    password_hash = cfg.web.password_hash

    # If no password is set, allow any login
    if not password_hash or verify_password(password, password_hash):
        token = create_session()
        if "application/json" in content_type:
            response = JSONResponse({"status": "ok"})
        else:
            response = RedirectResponse(url="/", status_code=302)
        response.set_cookie(
            key="session",
            value=token,
            httponly=True,
            samesite="lax",
            max_age=86400 * 7,
        )
        return response

    if "application/json" in content_type:
        return JSONResponse({"error": "invalid password"}, status_code=401)

    # For form submissions, redirect back to login with error
    return RedirectResponse(url="/login?error=1", status_code=302)


@router.post("/logout")
async def logout(request: Request):
    """Clear session cookie."""
    token = request.cookies.get("session")
    destroy_session(token)
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("session")
    return response
