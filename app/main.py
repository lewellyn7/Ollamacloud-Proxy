import os
import json
import time
import uuid
import secrets
import httpx
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException, Depends, Form, Response
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import app.database as db

app = FastAPI(title="Ollama Cloud Proxy", version="1.9.0")

# --- Middleware: Fix Double Slash ---
@app.middleware("http")
async def fix_double_slash(request: Request, call_next):
    if request.scope["path"].startswith("//"):
        request.scope["path"] = request.scope["path"].replace("//", "/", 1)
    response = await call_next(request)
    return response

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

if not os.path.exists("data"): os.makedirs("data")
db.init_db()

def get_client_ip(request: Request):
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded: return forwarded.split(",")[0]
    return request.client.host

SESSION_COOKIE_NAME = "proxy_session"

async def get_current_user(request: Request):
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token: raise HTTPException(401, "Not authenticated")
    username = db.get_session_user(token)
    if not username: raise HTTPException(401, "Session expired")
    return username

async def verify_client_key(request: Request):
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        key = auth_header.split(" ")[1]
        if db.verify_api_key(key): return key
    raise HTTPException(401, "Invalid API Key")

class ChatMessage(BaseModel):
    role: str
    content: str
class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    stream: Optional[bool] = False
    temperature: Optional[float] = 0.7

# --- HTML Routes ---
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login_action(request: Request, response: Response, username: str = Form(...), password: str = Form(...)):
    client_ip = get_client_ip(request)
    if db.is_ip_blocked(client_ip): return JSONResponse(403, {"status": "error", "message": "IP封锁中"})
    success, msg = db.verify_login_security(username, password, client_ip)
    if success:
        token = db.create_session(username)
        response = JSONResponse({"status": "success"})
        response.set_cookie(key=SESSION_COOKIE_NAME, value=token, max_age=2592000, httponly=True)
        return response
    return JSONResponse(401, {"status": "error", "message": msg})

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register")
async def register_action(request: Request, username: str = Form(...), password: str = Form(...), email: str = Form(...)):
    client_ip = get_client_ip(request)
    if not db.check_registration_limit(client_ip): return JSONResponse(403, {"status": "error", "message": "IP注册达限"})
    if len(password) < 6: return JSONResponse(400, {"status": "error", "message": "密码太短"})
    success, msg = db.create_user(username, password, email, client_ip)
    if success: return JSONResponse({"status": "success", "message": "注册成功"})
    return JSONResponse(400, {"status": "error", "message": msg})

@app.get("/logout")
async def logout_action(response: Response, request: Request):
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token: db.delete_session(token)
    resp = RedirectResponse(url="/login", status_code=302)
    resp.delete_cookie(SESSION_COOKIE_NAME)
    return resp

@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    try: user = await get_current_user(request)
    except: return RedirectResponse("/login", 302)
    return templates.TemplateResponse("profile.html", {"request": request, "username": user})

@app.post("/api/change-password")
async def change_pwd_api(old_password: str = Form(...), new_password: str = Form(...), user: str = Depends(get_current_user)):
    if len(new_password) < 6: return JSONResponse(400, {"status": "error", "message": "新密码太短"})
    success, msg = db.change_user_password(user, old_password, new_password)
    if success: return JSONResponse({"status": "success", "message": msg})
    return JSONResponse(400, {"status": "error", "message": msg})

@app.get("/", response_class=HTMLResponse)
async def admin_page(request: Request):
    try: user = await get_current_user(request)
    except: return RedirectResponse("/login", 302)
    ollama_host = db.get_config("ollama_host") or "https://ollama.com/api/chat"
    ollama_key = db.get_config("ollama_key") or ""
    keys = db.list_api_keys(user)
    return templates.TemplateResponse("admin.html", {"request": request, "username": user, "ollama_host": ollama_host, "ollama_key": ollama_key, "keys": keys})

# --- Admin API ---
@app.post("/admin/config")
async def update_config(ollama_host: str = Form(...), ollama_key: str = Form(None), _: str = Depends(get_current_user)):
    db.set_config("ollama_host", ollama_host)
    if ollama_key: db.set_config("ollama_key", ollama_key)
    return JSONResponse({"status": "success"})

@app.post("/admin/keys")
async def generate_key(name: str = Form(...), user: str = Depends(get_current_user)):
    new_key = f"sk-prox-{secrets.token_urlsafe(24)}"
    if db.create_api_key(new_key, name, user): return JSONResponse({"status": "success", "key": new_key})
    return JSONResponse(400, {"status": "error"})

@app.delete("/admin/keys/{key}")
async def remove_key(key: str, user: str = Depends(get_current_user)):
    db.delete_api_key(key, user)
    return JSONResponse({"status": "success"})

@app.post("/api/test-connection")
async def test_conn(_: str = Depends(get_current_user)):
    ollama_host = db.get_config("ollama_host")
    ollama_key = db.get_config("ollama_key")
    if not ollama_host: return JSONResponse(400, {"status": "error", "message": "Host Missing"})
    target = ollama_host.replace("/api/chat", "/api/tags") if "/api/chat" in ollama_host else ollama_host.rstrip("/") + "/api/tags"
    headers = {"User-Agent": "OllamaProxy/Test"}
    if ollama_key: headers["Authorization"] = f"Bearer {ollama_key}"
    try:
        async with httpx.AsyncClient(timeout=8.0, verify=False) as client:
            resp = await client.get(target, headers=headers)
            if resp.status_code == 200:
                try: 
                    models = [m.get("name") for m in resp.json().get("models", [])]
                    return JSONResponse({"status": "success", "message": f"成功! {len(models)}模型", "models": models})
                except: return JSONResponse(502, {"status": "error", "message": "JSON Error"})
            return JSONResponse(resp.status_code, {"status": "error", "message": f"HTTP {resp.status_code}"})
    except Exception as e: return JSONResponse(500, {"status": "error", "message": str(e)})

# --- OpenAI Logic ---
async def _list_models_logic():
    ollama_host = db.get_config("ollama_host")
    ollama_key = db.get_config("ollama_key")
    fallback = [{"id": "gpt-3.5-turbo", "object": "model", "created": 0, "owned_by": "openai"}]
    if not ollama_host: return {"object": "list", "data": fallback}
    headers = {}
    if ollama_key: headers["Authorization"] = f"Bearer {ollama_key}"
    try:
        target = ollama_host.replace("/api/chat", "/api/tags")
        async with httpx.AsyncClient(timeout=5, verify=False) as client:
            resp = await client.get(target, headers=headers)
            if resp.status_code == 200:
                models = [{"id": m.get("name"), "object": "model", "created": int(time.time()), "owned_by": "ollama"} for m in resp.json().get("models", [])]
                if models: return {"object": "list", "data": models}
    except: pass
    return {"object": "list", "data": fallback}

async def _chat_logic(req: ChatCompletionRequest, key: str):
    ollama_host = db.get_config("ollama_host")
    ollama_key = db.get_config("ollama_key")
    if not ollama_host: raise HTTPException(500, "Config missing")
    
    payload = {"model": req.model, "messages": [{"role": m.role, "content": m.content} for m in req.messages], "stream": req.stream, "options": {"temperature": req.temperature}}
    headers = {"Content-Type": "application/json"}
    if ollama_key: headers["Authorization"] = f"Bearer {ollama_key}"
    client = httpx.AsyncClient(timeout=120, verify=False)
    
    try:
        if req.stream:
            async def stream_gen():
                try:
                    async with client.stream("POST", ollama_host, json=payload, headers=headers) as r:
                        async for line in r.aiter_lines():
                            if not line: continue
                            try:
                                d = json.loads(line)
                                if d.get("done"): yield "data: [DONE]\n\n"; break
                                c = d.get("message", {}).get("content", "")
                                yield f"data: {json.dumps({'id':'chatcmpl-1','object':'chat.completion.chunk','created':int(time.time()),'model':req.model,'choices':[{'index':0,'delta':{'content':c},'finish_reason':None}]})}\n\n"
                            except: pass
                finally: await client.aclose()
            return StreamingResponse(stream_gen(), media_type="text/event-stream")
        else:
            # --- 关键修复：非流式请求的格式转换 ---
            resp = await client.post(ollama_host, json=payload, headers=headers)
            await client.aclose()
            
            if resp.status_code != 200:
                return JSONResponse(status_code=resp.status_code, content=resp.json())
            
            # 解析 Ollama 响应
            ollama_data = resp.json()
            content = ollama_data.get("message", {}).get("content", "")
            
            # 构造标准的 OpenAI 响应
            openai_resp = {
                "id": f"chatcmpl-{uuid.uuid4()}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": req.model,
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": content
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": ollama_data.get("prompt_eval_count", 0),
                    "completion_tokens": ollama_data.get("eval_count", 0),
                    "total_tokens": ollama_data.get("prompt_eval_count", 0) + ollama_data.get("eval_count", 0)
                }
            }
            return openai_resp
            
    except Exception as e:
        await client.aclose()
        print(f"DEBUG: Error in chat logic: {e}")
        raise HTTPException(500, str(e))

# --- Routes ---
@app.get("/v1/models")
async def list_models_v1(): return await _list_models_logic()

@app.post("/v1/chat/completions")
async def chat_completions_v1(req: ChatCompletionRequest, key: str = Depends(verify_client_key)): return await _chat_logic(req, key)

@app.get("/models")
async def list_models_root(): return await _list_models_logic()

@app.post("/chat/completions")
async def chat_completions_root(req: ChatCompletionRequest, key: str = Depends(verify_client_key)): return await _chat_logic(req, key)
