"""
ai_client.py — MaxPlus AI (Gemini-compatible) Client
ใช้งานง่าย: เรียก ask() หรือ chat() ได้เลย

Usage:
    from src.core.ai_client import ask, chat, AIClient

    # ถามทีเดียว
    answer = ask("อธิบาย Blender Python API ให้หน่อย")
    print(answer)

    # multi-turn chat
    history = []
    history = chat("สวัสดี", history)
    history = chat("ช่วยเขียน script สร้าง cube ใน Blender", history)
"""

import os
import json
import urllib.request
import urllib.error
from typing import Any, Callable, Optional, Union

# ─── CONFIG ───────────────────────────────────────────────────────────────────
# ใส่ API key ตรงนี้ หรือตั้ง environment variable: MAXPLUS_API_KEY
_API_KEY = os.environ.get(
    "MAXPLUS_API_KEY",
    ""
)
_BASE_URL = "https://api.maxplus-ai.cc/gemini-full/v1"
_DEFAULT_MODEL = "gemini-2.5-flash"
# ──────────────────────────────────────────────────────────────────────────────


class AIClient:
    """
    Client สำหรับ MaxPlus AI API (OpenAI-compatible / Gemini)
    """

    def __init__(
        self,
        api_key: str = _API_KEY,
        base_url: str = _BASE_URL,
        model: str = _DEFAULT_MODEL,
        system_prompt: str = "",
        timeout: int = 60,
        api_mode: str = "chat_completions",
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.system_prompt = system_prompt
        self.timeout = timeout
        self.api_mode = api_mode

    def _call_response(self, messages: list[dict[str, Any]], temperature: float = 0.7,
                       max_tokens: int = 8192, tools: Optional[list[dict[str, Any]]] = None,
                       _retry: int = 0) -> dict[str, Any]:
        """Call endpoint and return the response message dict (with content and/or tool_calls)."""
        import time
        if not self.api_key:
            raise RuntimeError(
                "ยังไม่ได้ตั้งค่า API key สำหรับโปรไฟล์ที่เลือก กรุณากดปุ่ม ⚙ เพื่อตั้งค่า"
            )
        if self.api_mode == "responses":
            url = f"{self.base_url}/responses"
            instructions = "\n\n".join(
                str(message.get("content", "")) for message in messages
                if message.get("role") in {"system", "developer"}
            )
            input_messages = self._response_input_items(messages)
            payload: dict[str, Any] = {"model": self.model, "input": input_messages,
                                       "max_output_tokens": max_tokens}
            if instructions:
                payload["instructions"] = instructions
            if tools:
                payload["tools"] = [self._response_tool(tool) for tool in tools]
        else:
            url = f"{self.base_url}/chat/completions"
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if tools:
                payload["tools"] = tools
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if self.api_mode == "responses":
                    tool_calls = []
                    for item in data.get("output", []):
                        if isinstance(item, dict) and item.get("type") == "function_call":
                            tool_calls.append({
                                "id": str(item.get("call_id") or item.get("id") or ""),
                                "type": "function",
                                "function": {
                                    "name": str(item.get("name") or ""),
                                    "arguments": item.get("arguments") or "{}",
                                },
                            })
                    result: dict[str, Any] = {
                        "role": "assistant",
                        "content": self._response_text(data, required=not tool_calls),
                    }
                    if tool_calls:
                        result["tool_calls"] = tool_calls
                    return result
                choices = data.get("choices", [])
                if not choices:
                    return {"role": "assistant", "content": ""}
                return choices[0].get("message", {"role": "assistant", "content": ""})
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            # 429 rate limit or 500/502/503/504 temporary server unavailable → retry with backoff
            if e.code in (429, 500, 502, 503, 504) and _retry < 3:
                wait = 2 ** _retry          # 1s, 2s, 4s
                time.sleep(wait)
                return self._call_response(messages, temperature, max_tokens, tools, _retry + 1)
            # Never silently remove tools: doing so lets a model claim an edit succeeded
            # even though it was not given any way to touch the project.
            if e.code == 400 and tools and any(k in err_body.lower() for k in ["tool", "invalid_request", "schema", "function", "unsupported"]):
                raise RuntimeError(f"The selected API/model rejected tool calling: {err_body}") from e
            raise RuntimeError(f"HTTP {e.code}: {err_body}") from e
        except urllib.error.URLError as e:
            raise RuntimeError(f"Connection error: {e.reason}") from e

    def _call(self, messages: list[dict[str, Any]], temperature: float = 0.7,
              max_tokens: int = 8192, tools: Optional[list[dict[str, Any]]] = None) -> str:
        """เรียก endpoint และคืนข้อความ content ล่าสุด"""
        res = self._call_response(messages, temperature=temperature, max_tokens=max_tokens, tools=tools)
        return str(res.get("content") or "")

    @staticmethod
    def _response_message(message: dict[str, Any]) -> dict[str, Any]:
        role = str(message.get("role", "user"))
        content = message.get("content", "")
        if isinstance(content, str):
            return {"role": role, "content": content}
        converted = []
        for item in content if isinstance(content, list) else []:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "text":
                converted.append({"type": "input_text", "text": str(item.get("text", ""))})
            elif item.get("type") == "image_url":
                image = item.get("image_url", {})
                url = image.get("url", "") if isinstance(image, dict) else str(image)
                converted.append({"type": "input_image", "image_url": url})
        return {"role": role, "content": converted}

    @classmethod
    def _response_input_items(cls, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Convert chat-style history, including function calls, to Responses input items."""
        items: list[dict[str, Any]] = []
        for message in messages:
            role = str(message.get("role", "user"))
            if role in {"system", "developer"}:
                continue
            if role == "tool":
                items.append({
                    "type": "function_call_output",
                    "call_id": str(message.get("tool_call_id") or ""),
                    "output": str(message.get("content") or ""),
                })
                continue

            content = message.get("content")
            if content not in (None, "", []):
                items.append(cls._response_message(message))
            for call in message.get("tool_calls") or []:
                function = call.get("function", {}) if isinstance(call, dict) else {}
                items.append({
                    "type": "function_call",
                    "call_id": str(call.get("id") or ""),
                    "name": str(function.get("name") or ""),
                    "arguments": function.get("arguments") or "{}",
                })
        return items

    @staticmethod
    def _response_tool(tool: dict[str, Any]) -> dict[str, Any]:
        """Convert a Chat Completions function tool to Responses API format."""
        function = tool.get("function", {})
        return {
            "type": "function",
            "name": str(function.get("name") or ""),
            "description": str(function.get("description") or ""),
            "parameters": function.get("parameters") or {"type": "object", "properties": {}},
        }

    @staticmethod
    def _response_text(data: dict[str, Any], required: bool = True) -> str:
        direct = data.get("output_text")
        if isinstance(direct, str) and direct:
            return direct
        parts = []
        for output in data.get("output", []):
            for item in output.get("content", []) if isinstance(output, dict) else []:
                if isinstance(item, dict) and item.get("type") in {"output_text", "text"}:
                    parts.append(str(item.get("text", "")))
        if parts:
            return "\n".join(parts)
        if required:
            raise RuntimeError("API response did not contain output text")
        return ""

    def ask(
        self,
        prompt: Union[str, list],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """
        ถาม AI คำถามเดียว คืน string คำตอบ
        prompt รับได้ทั้ง str และ list (multimodal: text + image_url)

        Example:
            client = AIClient()
            print(client.ask("สวัสดี"))
        """
        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        msg: dict[str, Any] = {"role": "user", "content": prompt}
        messages.append(msg)
        return self._call(messages, temperature=temperature, max_tokens=max_tokens)

    def stream_ask(
        self,
        prompt: Union[str, list],
        on_chunk: Optional[Callable[[str], None]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """Single-turn ask with real-time SSE streaming callback."""
        messages: list[dict[str, Any]] = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.append({"role": "user", "content": prompt})
        return self._stream_call(messages, on_chunk=on_chunk, temperature=temperature, max_tokens=max_tokens)

    def chat(
        self,
        user_message: Union[str, list],
        history: Optional[list] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> list:
        """
        Multi-turn chat รับ history list คืน history ที่อัปเดตแล้ว
        user_message รับได้ทั้ง str และ list (multimodal: text + image_url)
        """
        if history is None:
            history = []

        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.extend(history)
        msg: dict[str, Any] = {"role": "user", "content": user_message}
        messages.append(msg)

        reply = self._call(messages, temperature=temperature, max_tokens=max_tokens)

        updated = list(history)
        updated.append({"role": "user", "content": user_message})
        updated.append({"role": "assistant", "content": reply})
        return updated

    def stream_chat(
        self,
        user_message: Union[str, list],
        history: Optional[list] = None,
        on_chunk: Optional[Callable[[str], None]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> list:
        """Multi-turn chat with real-time SSE streaming callback."""
        if history is None:
            history = []
        messages: list[dict[str, Any]] = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.extend(history)
        messages.append({"role": "user", "content": user_message})

        reply = self._stream_call(messages, on_chunk=on_chunk, temperature=temperature, max_tokens=max_tokens)
        updated = list(history)
        updated.append({"role": "user", "content": user_message})
        updated.append({"role": "assistant", "content": reply})
        return updated

    def _stream_call(
        self,
        messages: list[dict[str, Any]],
        on_chunk: Optional[Callable[[str], None]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """Execute stream request and yield tokens via on_chunk callback."""
        if not on_chunk or self.api_mode == "responses":
            return self._call(messages, temperature=temperature, max_tokens=max_tokens)

        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        full_text: list[str] = []
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                for raw_line in resp:
                    line = raw_line.decode("utf-8", errors="replace").strip()
                    if not line or not line.startswith("data:"):
                        continue
                    data_str = line[5:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        choices = chunk.get("choices", [])
                        if choices:
                            delta = choices[0].get("delta", {})
                            token = delta.get("content") or ""
                            if token:
                                full_text.append(token)
                                on_chunk(token)
                    except Exception:
                        continue
            res_str = "".join(full_text)
            if res_str:
                return res_str
        except Exception:
            pass
        return self._call(messages, temperature=temperature, max_tokens=max_tokens)

    def chat_with_tools(
        self,
        user_message: Union[str, list],
        history: Optional[list] = None,
        tools: Optional[list[dict[str, Any]]] = None,
        tool_executor: Optional[Callable[[str, dict[str, Any]], str]] = None,
        on_status: Optional[Callable[[str], None]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        max_tool_rounds: int = 10,
    ) -> tuple[list, list[str]]:
        """
        Multi-turn chat with autonomous tool-calling loop.
        Returns: (updated_history, tool_action_logs)
        """
        if history is None:
            history = []

        messages: list[dict[str, Any]] = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.extend(history)
        user_msg: dict[str, Any] = {"role": "user", "content": user_message}
        messages.append(user_msg)

        logs: list[str] = []
        round_idx = 0
        final_content = ""

        # If tools are not provided, fallback to a regular call.
        if not tools:
            reply = self._call(messages, temperature=temperature, max_tokens=max_tokens)
            updated = list(history)
            updated.append(user_msg)
            updated.append({"role": "assistant", "content": reply})
            return updated, logs

        call_history: list[str] = []
        repeat_counts: dict[str, int] = {}
        should_break_loop = False

        while round_idx < max_tool_rounds and not should_break_loop:
            round_idx += 1
            try:
                assistant_msg = self._call_response(
                    messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    tools=tools,
                )
            except Exception as ex:
                err_msg = str(ex)
                logs.append(f"⚠️ เกิดข้อผิดพลาดจากเซิร์ฟเวอร์ AI: {err_msg}")
                if on_status:
                    on_status(f"⚠️ เซิร์ฟเวอร์ขัดข้อง: {err_msg[:80]}")
                # If we already have tool actions executed, don't crash and drop everything!
                # Break out and synthesize or generate a fallback summary from what was gathered.
                if logs:
                    break
                raise
            messages.append(assistant_msg)

            tool_calls = assistant_msg.get("tool_calls")
            if not tool_calls:
                final_content = str(assistant_msg.get("content") or "")
                break

            for tc in tool_calls:
                tc_id = str(tc.get("id") or f"call_{round_idx}")
                func_info = tc.get("function", {})
                tool_name = str(func_info.get("name") or "")
                args_str = func_info.get("arguments", "{}")
                try:
                    tool_args = json.loads(args_str) if isinstance(args_str, str) else (args_str or {})
                except Exception:
                    tool_args = {}

                sig = f"{tool_name}:{json.dumps(tool_args, sort_keys=True, ensure_ascii=False)}"
                call_history.append(sig)
                repeat_counts[sig] = repeat_counts.get(sig, 0) + 1

                status_msg = f"🔧 เรียกใช้เครื่องมือ: {tool_name}({json.dumps(tool_args, ensure_ascii=False)})"
                logs.append(status_msg)
                if on_status:
                    on_status(status_msg)

                if tool_executor:
                    try:
                        tool_result = tool_executor(tool_name, tool_args)
                    except Exception as ex:
                        tool_result = f"Error executing {tool_name}: {ex}"
                else:
                    tool_result = f"Tool executor not provided for {tool_name}"

                # Loop prevention & cognitive guidance
                if repeat_counts[sig] >= 2:
                    tool_result += (
                        "\n\n[คำแนะนำจากระบบ: ตรวจพบว่าคุณเรียกใช้เครื่องมือนี้ด้วยพารามิเตอร์เดิมซ้ำ "
                        "กรุณาวิเคราะห์ผลลัพธ์หรือข้อผิดพลาดข้างต้น ปรับเปลี่ยนแนวทาง หรือตอบสรุปผลลัพธ์ให้ผู้ใช้โดยตรง หลีกเลี่ยงการวนลูปซ้ำ]"
                    )
                if repeat_counts[sig] >= 4:
                    should_break_loop = True

                result_status = f"-> ผลลัพธ์ {tool_name}: {tool_result[:300]}"
                logs.append(result_status)
                if on_status:
                    on_status(result_status)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc_id,
                    "content": tool_result,
                })

        # Ensure a comprehensive final answer is produced after tool execution
        is_empty_or_trivial = (
            not final_content.strip()
            or final_content.strip() in {"(ดำเนินการเสร็จสิ้น)", "เสร็จสิ้น", "done", "Done", "ok", "OK"}
        )

        if is_empty_or_trivial and round_idx > 0:
            status_msg = "🧠 กำลังประมวลผลและสรุปคำตอบให้ผู้ใช้..."
            logs.append(status_msg)
            if on_status:
                on_status(status_msg)

            # Build a clean synthesis conversation for final output
            synthesis_messages = [m for m in messages if m.get("content") or m.get("tool_calls")]
            while synthesis_messages and synthesis_messages[-1].get("role") == "assistant" and not synthesis_messages[-1].get("content") and not synthesis_messages[-1].get("tool_calls"):
                synthesis_messages.pop()

            synthesis_prompt = (
                "การเรียกใช้เครื่องมือเพื่อค้นหา/ตรวจสอบเสร็จสิ้นแล้ว กรุณาสรุปและตอบคำถามของผู้ใช้อย่างครบถ้วน ละเอียด และชัดเจนเป็นภาษาไทย:\n"
                "1. สรุปสิ่งที่ได้ตรวจสอบ สืบค้น หรือดำเนินการไปแล้วทีละขั้นตอน\n"
                "2. สรุปข้อมูลที่ค้นพบ ผลการเชื่อมต่อ หรือไฟล์/โค้ดที่สร้างหรือแก้ไข (พร้อมระบุชื่อไฟล์และโค้ดตัวอย่างถ้ามี)\n"
                "3. หากมีข้อผิดพลาด (Error) หรือไม่สามารถเชื่อมต่อได้ ให้ระบุสาเหตุอย่างตรงไปตรงมา และแนะนำวิธีแก้ไข\n"
                "4. ให้คำตอบสุดท้ายที่สมบูรณ์และนำไปใช้ต่อได้ทันที (ห้ามตอบสั้นหรือเว้นว่างเด็ดขาด)"
            )
            synthesis_messages.append({"role": "user", "content": synthesis_prompt})

            try:
                synth_reply = self._call(
                    synthesis_messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                if synth_reply and synth_reply.strip():
                    final_content = synth_reply.strip()
            except Exception as ex:
                logs.append(f"Synthesis call failed: {ex}")

        # If still empty or trivial, generate a detailed fallback summary from logs
        if not final_content or not final_content.strip() or final_content.strip() in {"(ดำเนินการเสร็จสิ้น)", "เสร็จสิ้น"}:
            final_content = self._generate_fallback_summary(logs, user_message)

        updated = list(history)
        updated.append(user_msg)
        updated.append({"role": "assistant", "content": final_content})
        return updated, logs

    @staticmethod
    def _generate_fallback_summary(logs: list[str], user_message: Union[str, list[dict[str, Any]]]) -> str:
        """Construct a structured and helpful summary from execution logs when the LLM returns empty."""
        actions: list[dict[str, str]] = []
        for l in logs:
            if l.startswith("🔧 เรียกใช้เครื่องมือ:"):
                act = l.replace("🔧 เรียกใช้เครื่องมือ:", "").strip()
                actions.append({"action": act, "result": ""})
            elif l.startswith("-> ผลลัพธ์") and actions:
                res = l.replace("-> ผลลัพธ์", "").strip()
                actions[-1]["result"] = res

        if not actions:
            return "ดำเนินการตามคำสั่งเสร็จสิ้นเรียบร้อยแล้วครับ หากต้องการให้ดำเนินการเพิ่มเติมในส่วนใด สามารถแจ้งได้ทันทีครับ"

        lines = [
            "### 🛠️ รายงานสรุปผลการดำเนินการ (Execution Summary)",
            f"ระบบได้ดำเนินการไปทั้งหมด **{len(actions)} ขั้นตอน** รายละเอียดดังนี้:\n",
        ]
        has_errors = False
        for i, item in enumerate(actions, 1):
            act = item["action"]
            res = item["result"]
            is_err = "error" in res.lower() or "fail" in res.lower() or "🚫" in res
            if is_err:
                has_errors = True
                status_badge = "❌ [พบข้อผิดพลาด]"
            else:
                status_badge = "✔ [สำเร็จ]"

            lines.append(f"{i}. **เครื่องมือ:** `{act}`")
            lines.append(f"   - **สถานะ:** {status_badge}")
            if res:
                lines.append(f"   - **รายละเอียด:** {res[:250]}")
            lines.append("")

        if has_errors:
            lines.append("⚠️ **ข้อสังเกต:** มีบางคำสั่งหรือการเชื่อมต่อพบข้อผิดพลาด กรุณาตรวจสอบรายละเอียดข้างต้น หรือระบุพารามิเตอร์เพิ่มเติมเพื่อให้ระบบช่วยดำเนินการแก้ไขต่อไปครับ")
        else:
            lines.append("✅ การดำเนินการของเครื่องมือเสร็จสิ้นสมบูรณ์ หากต้องการให้ปรับแต่งหรือเขียนโค้ดเพิ่มเติม สามารถสั่งการต่อได้ทันทีครับ")

        server_errs = [l for l in logs if "⚠️ เกิดข้อผิดพลาดจากเซิร์ฟเวอร์ AI:" in l]
        if server_errs:
            err_line = server_errs[-1].replace("⚠️ เกิดข้อผิดพลาดจากเซิร์ฟเวอร์ AI:", "").strip()
            lines.append(f"\n> ℹ️ **หมายเหตุการเชื่อมต่อ:** ในขั้นตอนสุดท้ายเซิร์ฟเวอร์ AI ปลายทางขัดข้องชั่วคราว ({err_line}) ระบบจึงได้รวบรวมข้อมูลจากการตรวจสอบข้างต้นมาให้เรียบร้อยแล้วครับ")

        return "\n".join(lines)

    def list_models(self) -> list:
        """ดูรายการ models ที่ใช้งานได้"""
        url = f"{self.base_url}/models"
        req = urllib.request.Request(
            url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return [m["id"] for m in data.get("data", [])]
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {e.code}: {err_body}") from e


# ─── MODULE-LEVEL SHORTCUTS ───────────────────────────────────────────────────
_default_client: Optional[AIClient] = None


def _get_client() -> AIClient:
    global _default_client
    if _default_client is None:
        _default_client = AIClient()
    return _default_client


def ask(prompt: str, system: str = "", model: str = _DEFAULT_MODEL, **kwargs) -> str:
    """Shortcut: ถาม AI คำถามเดียว"""
    client = AIClient(system_prompt=system, model=model)
    return client.ask(prompt, **kwargs)


def chat(user_message: str, history: Optional[list] = None, **kwargs) -> list:
    """Shortcut: multi-turn chat ใช้ default client"""
    return _get_client().chat(user_message, history, **kwargs)


if __name__ == "__main__":
    print("MaxPlus AI Client Self Test")
    client = AIClient()
    print("Ready.")
