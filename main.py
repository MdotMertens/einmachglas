import asyncio
import json
import os
import random
import string
import uuid
from collections import defaultdict
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from auth import hash_password, verify_password
from db import get_db, init_db
from i18n import DEFAULT_LANG, SUPPORTED_LANGS, t


# ---------------------------------------------------------------------------
# SSE: real-time sync between partners
# ---------------------------------------------------------------------------

_pair_listeners: dict[str, set[asyncio.Queue]] = defaultdict(set)


async def _notify_pair(pair_id: str):
    for queue in _pair_listeners.get(pair_id, set()):
        queue.put_nowait("update")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY", "change-me-in-production"),
)
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_user(request: Request) -> dict | None:
    return request.session.get("user")


def _require_user(request: Request) -> dict:
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401)
    return user


def _lang(request: Request) -> str:
    return request.cookies.get("lang", DEFAULT_LANG)


def _t(request: Request, key: str, **kwargs: str) -> str:
    return t(key, _lang(request), **kwargs)


def _get_pair_id(user_id: str) -> str | None:
    db = get_db()
    row = db.execute("SELECT pair_id FROM users WHERE id = ?", (user_id,)).fetchone()
    db.close()
    return row["pair_id"] if row else None


def _activity_context(pair_id: str) -> dict:
    db = get_db()
    activities = db.execute(
        "SELECT * FROM activities WHERE pair_id = ? ORDER BY created_at",
        (pair_id,),
    ).fetchall()
    db.close()
    undone = [a for a in activities if not a["done"]]
    done = [a for a in activities if a["done"]]
    return {"undone": undone, "done": done}


COLORS = [
    "bg-[#f4a261]",
    "bg-[#e9c46a]",
    "bg-[#2a9d8f]",
    "bg-[#5fa8d3]",
    "bg-[#e76f51]",
    "bg-[#a37bc5]",
]


def _color_for_index(i: int) -> str:
    return COLORS[i % len(COLORS)]


# Make helpers available in templates
templates.env.globals["color_for_index"] = _color_for_index
templates.env.globals["supported_langs"] = SUPPORTED_LANGS


# ---------------------------------------------------------------------------
# Language switcher
# ---------------------------------------------------------------------------

@app.get("/lang/{lang}")
async def set_language(request: Request, lang: str):
    if lang not in SUPPORTED_LANGS:
        lang = DEFAULT_LANG
    referer = request.headers.get("referer", "/")
    response = RedirectResponse(url=referer, status_code=302)
    response.set_cookie("lang", lang, max_age=60 * 60 * 24 * 365)
    return response


# ---------------------------------------------------------------------------
# Template response helper (auto-injects lang + t)
# ---------------------------------------------------------------------------

def _render(request: Request, template: str, ctx: dict | None = None):
    lang = _lang(request)
    base = {"lang": lang, "t": lambda key, **kw: t(key, lang, **kw)}
    if ctx:
        base.update(ctx)
    return templates.TemplateResponse(request, template, base)


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    user = _get_user(request)
    if not user:
        return _render(request, "login.html")

    pair_id = _get_pair_id(user["id"])
    if not pair_id:
        return _render(request, "pair.html", {"user": user})

    ctx = _activity_context(pair_id)
    db = get_db()
    partner = db.execute(
        "SELECT * FROM users WHERE pair_id = ? AND id != ?",
        (pair_id, user["id"]),
    ).fetchone()
    db.close()

    return _render(request, "home.html", {"user": user, "partner": partner, **ctx})


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return _render(request, "login.html")


@app.post("/register", response_class=HTMLResponse)
async def register(
    request: Request,
    username: str = Form(...),
    display_name: str = Form(...),
    password: str = Form(...),
):
    username = username.strip().lower()
    display_name = display_name.strip()

    if len(username) < 3:
        return _render(request, "login.html", {
            "error": _t(request, "err.username_short"), "tab": "register",
        })
    if len(password) < 6:
        return _render(request, "login.html", {
            "error": _t(request, "err.password_short"), "tab": "register",
        })

    db = get_db()
    existing = db.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    if existing:
        db.close()
        return _render(request, "login.html", {
            "error": _t(request, "err.username_taken"), "tab": "register",
        })

    user_id = str(uuid.uuid4())
    db.execute(
        "INSERT INTO users (id, username, password_hash, display_name) VALUES (?, ?, ?, ?)",
        (user_id, username, hash_password(password), display_name),
    )
    db.commit()
    db.close()

    request.session["user"] = {"id": user_id, "username": username, "display_name": display_name}
    return RedirectResponse(url="/", status_code=302)


@app.post("/login", response_class=HTMLResponse)
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    username = username.strip().lower()
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    db.close()

    if not user or not verify_password(password, user["password_hash"]):
        return _render(request, "login.html", {
            "error": _t(request, "err.invalid_login"), "tab": "login",
        })

    request.session["user"] = {
        "id": user["id"],
        "username": user["username"],
        "display_name": user["display_name"],
    }
    return RedirectResponse(url="/", status_code=302)


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=302)


# ---------------------------------------------------------------------------
# Pairing
# ---------------------------------------------------------------------------

@app.post("/pair/create", response_class=HTMLResponse)
async def create_pair(request: Request):
    user = _require_user(request)
    if _get_pair_id(user["id"]):
        return HTMLResponse(
            f'<p class="text-[#ef4444] font-bold text-sm mt-2">{_t(request, "err.already_paired")}</p>'
        )

    pair_id = str(uuid.uuid4())
    code = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))

    db = get_db()
    db.execute("INSERT INTO pairs (id, invite_code) VALUES (?, ?)", (pair_id, code))
    db.execute("UPDATE users SET pair_id = ? WHERE id = ?", (pair_id, user["id"]))
    db.commit()
    db.close()

    share = _t(request, "pair.share")
    hint = _t(request, "pair.share_hint")
    cont = _t(request, "pair.continue")
    return HTMLResponse(f"""
        <div class="text-center space-y-3">
            <p class="font-semibold">{share}</p>
            <div class="inline-block bg-[#e9c46a] neo-tag px-6 py-3">
                <span class="text-3xl font-black tracking-[0.2em]">{code}</span>
            </div>
            <p class="text-sm text-[#555]">{hint}</p>
            <a href="/" class="neo-btn inline-block bg-white px-4 py-2 text-sm mt-2">{cont}</a>
        </div>
    """)


@app.post("/pair/join", response_class=HTMLResponse)
async def join_pair(request: Request, code: str = Form(...)):
    user = _require_user(request)
    clean_code = code.strip().upper()

    db = get_db()
    pair = db.execute(
        "SELECT * FROM pairs WHERE invite_code = ?", (clean_code,)
    ).fetchone()
    if not pair:
        db.close()
        return HTMLResponse(
            f'<p class="text-[#ef4444] font-bold text-sm mt-2">{_t(request, "err.invalid_code")}</p>'
        )

    old_pair_id = _get_pair_id(user["id"])
    if old_pair_id:
        db.execute("UPDATE users SET pair_id = NULL WHERE id = ?", (user["id"],))
        remaining = db.execute(
            "SELECT COUNT(*) as c FROM users WHERE pair_id = ?", (old_pair_id,)
        ).fetchone()
        if remaining["c"] == 0:
            db.execute("DELETE FROM activities WHERE pair_id = ?", (old_pair_id,))
            db.execute("DELETE FROM pairs WHERE id = ?", (old_pair_id,))

    db.execute("UPDATE users SET pair_id = ? WHERE id = ?", (pair["id"], user["id"]))
    db.commit()
    db.close()

    return HTMLResponse(status_code=200, headers={"HX-Redirect": "/"})


@app.post("/pair/leave", response_class=HTMLResponse)
async def leave_pair(request: Request):
    user = _require_user(request)
    pair_id = _get_pair_id(user["id"])

    db = get_db()
    db.execute("UPDATE users SET pair_id = NULL WHERE id = ?", (user["id"],))

    if pair_id:
        remaining = db.execute(
            "SELECT COUNT(*) as c FROM users WHERE pair_id = ?", (pair_id,)
        ).fetchone()
        if remaining["c"] == 0:
            db.execute("DELETE FROM activities WHERE pair_id = ?", (pair_id,))
            db.execute("DELETE FROM pairs WHERE id = ?", (pair_id,))

    db.commit()
    db.close()

    return HTMLResponse(status_code=200, headers={"HX-Redirect": "/"})


# ---------------------------------------------------------------------------
# SSE endpoint + activity list fetch
# ---------------------------------------------------------------------------

@app.get("/events")
async def sse(request: Request):
    user = _get_user(request)
    if not user:
        return HTMLResponse(status_code=204)
    pair_id = _get_pair_id(user["id"])
    if not pair_id:
        return HTMLResponse(status_code=204)

    queue: asyncio.Queue = asyncio.Queue()
    _pair_listeners[pair_id].add(queue)

    async def event_stream():
        try:
            while True:
                try:
                    await asyncio.wait_for(queue.get(), timeout=15)
                    yield "event: update\ndata: refresh\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            _pair_listeners[pair_id].discard(queue)
            if not _pair_listeners[pair_id]:
                del _pair_listeners[pair_id]

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/activities/list", response_class=HTMLResponse)
async def get_activity_list(request: Request):
    user = _require_user(request)
    pair_id = _get_pair_id(user["id"])
    if not pair_id:
        raise HTTPException(status_code=400)
    ctx = _activity_context(pair_id)
    return _render(request, "partials/activity_list.html", ctx)


# ---------------------------------------------------------------------------
# Activities
# ---------------------------------------------------------------------------

@app.post("/activities", response_class=HTMLResponse)
async def add_activity(request: Request, name: str = Form(...)):
    user = _require_user(request)
    pair_id = _get_pair_id(user["id"])
    if not pair_id:
        raise HTTPException(status_code=400)

    db = get_db()
    db.execute(
        "INSERT INTO activities (id, pair_id, name) VALUES (?, ?, ?)",
        (str(uuid.uuid4()), pair_id, name.strip()),
    )
    db.commit()
    db.close()

    await _notify_pair(pair_id)
    ctx = _activity_context(pair_id)
    return _render(request, "partials/activity_list.html", ctx)


@app.put("/activities/{activity_id}/toggle", response_class=HTMLResponse)
async def toggle_activity(request: Request, activity_id: str):
    user = _require_user(request)
    pair_id = _get_pair_id(user["id"])

    db = get_db()
    activity = db.execute(
        "SELECT * FROM activities WHERE id = ?", (activity_id,)
    ).fetchone()
    if not activity or activity["pair_id"] != pair_id:
        db.close()
        raise HTTPException(status_code=403)

    db.execute("UPDATE activities SET done = NOT done WHERE id = ?", (activity_id,))
    db.commit()
    db.close()

    await _notify_pair(pair_id)
    ctx = _activity_context(pair_id)
    return _render(request, "partials/activity_list.html", ctx)


@app.delete("/activities/{activity_id}", response_class=HTMLResponse)
async def delete_activity(request: Request, activity_id: str):
    user = _require_user(request)
    pair_id = _get_pair_id(user["id"])

    db = get_db()
    activity = db.execute(
        "SELECT * FROM activities WHERE id = ?", (activity_id,)
    ).fetchone()
    if not activity or activity["pair_id"] != pair_id:
        db.close()
        raise HTTPException(status_code=403)

    db.execute("DELETE FROM activities WHERE id = ?", (activity_id,))
    db.commit()
    db.close()

    await _notify_pair(pair_id)
    ctx = _activity_context(pair_id)
    return _render(request, "partials/activity_list.html", ctx)


@app.post("/activities/reset", response_class=HTMLResponse)
async def reset_activities(request: Request):
    user = _require_user(request)
    pair_id = _get_pair_id(user["id"])
    if not pair_id:
        raise HTTPException(status_code=400)

    db = get_db()
    db.execute("UPDATE activities SET done = 0 WHERE pair_id = ?", (pair_id,))
    db.commit()
    db.close()

    await _notify_pair(pair_id)
    ctx = _activity_context(pair_id)
    return _render(request, "partials/activity_list.html", ctx)


@app.get("/pick-random", response_class=HTMLResponse)
async def pick_random(request: Request):
    user = _require_user(request)
    pair_id = _get_pair_id(user["id"])
    if not pair_id:
        raise HTTPException(status_code=400)

    db = get_db()
    all_undone = db.execute(
        "SELECT * FROM activities WHERE pair_id = ? AND done = 0",
        (pair_id,),
    ).fetchall()
    db.close()

    if not all_undone:
        return HTMLResponse(f"<p class='font-bold text-center'>{_t(request, 'no_activities')}</p>")

    picked = random.choice(all_undone)
    all_names = [a["name"] for a in all_undone]

    return _render(request, "partials/picker.html", {
        "activity": picked, "all_names_json": json.dumps(all_names),
    })
