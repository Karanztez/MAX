/**
 * session.ts — Stateful conversation memory manager for MAX AI JavaScript SDK.
 */

import type { Message, SessionOptions } from "./types.js";
import type { MaxAgent } from "./agent.js";

export class MaxResponse {
  constructor(
    public readonly text: string,
    public readonly sessionId?: string,
    public readonly raw?: any
  ) {}

  toString(): string {
    return this.text;
  }
}

export class MaxSession {
  public readonly sessionId: string;
  public systemPrompt?: string;
  public maxHistory: number;
  private _history: Message[] = [];

  constructor(
    public readonly agent: MaxAgent,
    options: SessionOptions = {}
  ) {
    this.sessionId = options.sessionId || "default";
    this.systemPrompt = options.systemPrompt;
    this.maxHistory = options.maxHistory || 40;
  }

  get history(): Message[] {
    return [...this._history];
  }

  addMessage(role: Message["role"], content: string): void {
    this._history.push({ role, content });
    this.trimHistory();
  }

  clear(): void {
    this._history = [];
  }

  private trimHistory(): void {
    if (this._history.length > this.maxHistory) {
      this._history = this._history.slice(-this.maxHistory);
    }
  }

  async send(
    message: string,
    options: { temperature?: number; maxTokens?: number } = {}
  ): Promise<MaxResponse> {
    const promptSys = this.systemPrompt || this.agent.systemPrompt;
    const messages: Message[] = [];
    if (promptSys) {
      messages.push({ role: "system", content: promptSys });
    }
    messages.push(...this._history);
    messages.push({ role: "user", content: message });

    const reply = await this.agent._callMessages(messages, options);
    this.addMessage("user", message);
    this.addMessage("assistant", reply);

    return new MaxResponse(reply, this.sessionId);
  }

  async *stream(
    message: string,
    options: { temperature?: number; maxTokens?: number } = {}
  ): AsyncIterable<string> {
    const promptSys = this.systemPrompt || this.agent.systemPrompt;
    const messages: Message[] = [];
    if (promptSys) {
      messages.push({ role: "system", content: promptSys });
    }
    messages.push(...this._history);
    messages.push({ role: "user", content: message });

    let fullReply = "";
    for await (const chunk of this.agent._streamMessages(messages, options)) {
      fullReply += chunk;
      yield chunk;
    }

    this.addMessage("user", message);
    this.addMessage("assistant", fullReply);
  }
}
