/**
 * agent.ts — Main MaxAgent class for MAX AI JavaScript SDK.
 */

import type { AgentOptions, Message, SessionOptions } from "./types.js";
import { MaxSession } from "./session.js";

export class MaxAgent {
  public model: string;
  public apiKey: string;
  public baseUrl: string;
  public systemPrompt: string;
  public temperature: number;
  public maxTokens: number;
  public timeout: number;
  public apiMode: string;
  private _sessions: Map<string, MaxSession> = new Map();

  constructor(options: AgentOptions = {}) {
    this.model = options.model || "gemini-2.5-flash";
    this.apiKey = options.apiKey || (typeof process !== "undefined" && process.env ? process.env.MAXPLUS_API_KEY || "" : "");
    this.baseUrl = (options.baseUrl || "https://api.maxplus-ai.cc/gemini-full/v1").replace(/\/+$/, "");
    this.systemPrompt = options.systemPrompt || "";
    this.temperature = options.temperature ?? 0.7;
    this.maxTokens = options.maxTokens ?? 4096;
    this.timeout = options.timeout ?? 60000;
    this.apiMode = options.apiMode || "chat_completions";
  }

  async ask(
    prompt: string,
    options: { temperature?: number; maxTokens?: number } = {}
  ): Promise<string> {
    const messages: Message[] = [];
    if (this.systemPrompt) {
      messages.push({ role: "system", content: this.systemPrompt });
    }
    messages.push({ role: "user", content: prompt });
    return this._callMessages(messages, options);
  }

  async *stream(
    prompt: string,
    options: { temperature?: number; maxTokens?: number } = {}
  ): AsyncIterable<string> {
    const messages: Message[] = [];
    if (this.systemPrompt) {
      messages.push({ role: "system", content: this.systemPrompt });
    }
    messages.push({ role: "user", content: prompt });
    for await (const chunk of this._streamMessages(messages, options)) {
      yield chunk;
    }
  }

  createSession(sessionId: string = "default", options: SessionOptions = {}): MaxSession {
    const session = new MaxSession(this, { ...options, sessionId });
    this._sessions.set(sessionId, session);
    return session;
  }

  getSession(sessionId: string, createIfMissing: boolean = true): MaxSession | undefined {
    if (!this._sessions.has(sessionId) && createIfMissing) {
      return this.createSession(sessionId);
    }
    return this._sessions.get(sessionId);
  }

  clearSessions(): void {
    this._sessions.clear();
  }

  async _callMessages(
    messages: Message[],
    options: { temperature?: number; maxTokens?: number } = {}
  ): Promise<string> {
    const url = `${this.baseUrl}/chat/completions`;
    const payload = {
      model: this.model,
      messages,
      temperature: options.temperature ?? this.temperature,
      max_tokens: options.maxTokens ?? this.maxTokens,
    };

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      const resp = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${this.apiKey}`,
        },
        body: JSON.stringify(payload),
        signal: controller.signal,
      });

      if (!resp.ok) {
        const errorText = await resp.text();
        throw new Error(`HTTP ${resp.status}: ${errorText}`);
      }

      const data = await resp.json();
      const choices = data.choices || [];
      if (!choices.length) {
        return "";
      }
      return choices[0].message?.content || "";
    } finally {
      clearTimeout(timeoutId);
    }
  }

  async *_streamMessages(
    messages: Message[],
    options: { temperature?: number; maxTokens?: number } = {}
  ): AsyncIterable<string> {
    const url = `${this.baseUrl}/chat/completions`;
    const payload = {
      model: this.model,
      messages,
      temperature: options.temperature ?? this.temperature,
      max_tokens: options.maxTokens ?? this.maxTokens,
      stream: true,
    };

    const resp = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${this.apiKey}`,
      },
      body: JSON.stringify(payload),
    });

    if (!resp.ok) {
      const errorText = await resp.text();
      throw new Error(`HTTP ${resp.status}: ${errorText}`);
    }

    if (!resp.body) {
      throw new Error("Response body is null");
    }

    const reader = resp.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed || !trimmed.startsWith("data:")) continue;

        const dataStr = trimmed.slice(5).trim();
        if (dataStr === "[DONE]") return;

        try {
          const json = JSON.parse(dataStr);
          const delta = json.choices?.[0]?.delta?.content;
          if (delta) {
            yield delta;
          }
        } catch {
          // ignore malformed sse line
        }
      }
    }
  }
}
