"""
examples/fastapi_agent_server.py — FastAPI REST & Streaming AI Service using MAX AI SDK.

How to Run:
    1. pip install fastapi uvicorn
    2. Run: uvicorn examples.fastapi_agent_server:app --reload --port 8000
    3. Visit http://localhost:8000/docs for Swagger UI
"""

import os
from typing import Optional
import max_ai

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import StreamingResponse
    from pydantic import BaseModel
except ImportError:
    FastAPI = None  # type: ignore[assignment,misc]

if FastAPI is not None:
    app = FastAPI(
        title="MAX AI API Service",
        description="REST and Streaming API Gateway powered by MAX AI Agent SDK",
        version=max_ai.__version__,
    )

    # Initialize shared MaxAgent
    agent = max_ai.Agent(
        model=os.environ.get("MAX_MODEL", "gemini-2.5-flash"),
        api_key=os.environ.get("MAXPLUS_API_KEY", ""),
        system_prompt="You are MAX AI, serving high-performance API requests.",
    )

    class ChatRequest(BaseModel):
        prompt: str
        session_id: Optional[str] = "default"
        model: Optional[str] = None
        temperature: Optional[float] = 0.7

    class ChatResponse(BaseModel):
        reply: str
        session_id: str
        model: str

    @app.get("/")
    def root():
        return {"status": "ok", "service": "MAX AI Agent API", "version": max_ai.__version__}

    @app.post("/api/chat", response_model=ChatResponse)
    async def chat_endpoint(req: ChatRequest):
        """Standard JSON chat endpoint with isolated session memory."""
        session = agent.get_session(req.session_id or "default")
        response = await session.send_async(req.prompt, temperature=req.temperature)
        return ChatResponse(
            reply=response.text,
            session_id=session.session_id,
            model=agent.model,
        )

    @app.post("/api/chat/stream")
    async def stream_endpoint(req: ChatRequest):
        """Server-Sent Events (SSE) token streaming endpoint."""
        session = agent.get_session(req.session_id or "default")

        async def _generator():
            async for chunk in session.stream_async(req.prompt, temperature=req.temperature):
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(_generator(), media_type="text/event-stream")

    @app.delete("/api/sessions/{session_id}")
    def clear_session_endpoint(session_id: str):
        """Reset conversation memory for a session."""
        session = agent.get_session(session_id, create_if_missing=False)
        if session:
            session.clear()
        return {"status": "cleared", "session_id": session_id}

else:
    app = None
