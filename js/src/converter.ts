/**
 * converter.ts — Converters and format adapters for MAX AI.
 *
 * Provides format conversion between MAX AI messages and major LLM provider formats
 * (Google Gemini, OpenAI, Anthropic Claude), as well as text output adapters
 * for Discord (chunking & code-block safety), Markdown, and Plain Text.
 */

import type { Message, Role } from "./types.js";

export interface OpenAIMessage {
  role: "system" | "user" | "assistant" | "developer" | "tool";
  content: string;
  tool_call_id?: string;
  name?: string;
}

export interface GeminiPart {
  text: string;
}

export interface GeminiContent {
  role: "user" | "model";
  parts: GeminiPart[];
}

export interface AnthropicMessage {
  role: "user" | "assistant";
  content: string;
}

export interface AnthropicPayload {
  system?: string;
  messages: AnthropicMessage[];
}

export interface DiscordChunkOptions {
  maxChunkLength?: number;
  preserveCodeBlocks?: boolean;
}

/**
 * MaxConverter — Static converter and adapter utility class.
 */
export class MaxConverter {
  /**
   * Convert MAX AI messages into OpenAI-compatible chat messages.
   */
  static toOpenAI(messages: Message[]): OpenAIMessage[] {
    return messages.map((m) => {
      const contentStr =
        typeof m.content === "string"
          ? m.content
          : m.content
              .map((p) => (p.type === "text" ? p.text ?? "" : ""))
              .join("\n");

      const openAIMsg: OpenAIMessage = {
        role: (m.role === "developer" ? "developer" : m.role) as OpenAIMessage["role"],
        content: contentStr,
      };
      if (m.tool_call_id) {
        openAIMsg.tool_call_id = m.tool_call_id;
      }
      return openAIMsg;
    });
  }

  /**
   * Convert OpenAI messages into MAX AI messages.
   */
  static fromOpenAI(messages: OpenAIMessage[]): Message[] {
    return messages.map((m) => ({
      role: m.role as Role,
      content: m.content,
      tool_call_id: m.tool_call_id,
    }));
  }

  /**
   * Convert MAX AI messages into Google Gemini API contents structure.
   *
   * Gemini uses role: 'user' | 'model', and does not have a native 'system' role in contents
   * (system is passed via systemInstruction or prepended to user prompt).
   */
  static toGemini(
    messages: Message[],
    options: { systemInstruction?: boolean } = {}
  ): { contents: GeminiContent[]; systemInstruction?: string } {
    let systemInstruction: string | undefined = undefined;
    const contents: GeminiContent[] = [];

    for (const m of messages) {
      const text =
        typeof m.content === "string"
          ? m.content
          : m.content
              .map((p) => (p.type === "text" ? p.text ?? "" : ""))
              .join("\n");

      if (m.role === "system" || m.role === "developer") {
        if (options.systemInstruction !== false) {
          systemInstruction = systemInstruction ? `${systemInstruction}\n${text}` : text;
        } else {
          // Prepend as user message if systemInstruction is disabled
          contents.push({
            role: "user",
            parts: [{ text: `[System]: ${text}` }],
          });
        }
      } else {
        const geminiRole: "user" | "model" = m.role === "assistant" ? "model" : "user";
        contents.push({
          role: geminiRole,
          parts: [{ text }],
        });
      }
    }

    return { contents, systemInstruction };
  }

  /**
   * Convert Google Gemini API contents structure back to MAX AI messages.
   */
  static fromGemini(
    contents: GeminiContent[],
    systemInstruction?: string
  ): Message[] {
    const messages: Message[] = [];
    if (systemInstruction) {
      messages.push({ role: "system", content: systemInstruction });
    }
    for (const c of contents) {
      const text = c.parts.map((p) => p.text).join("");
      messages.push({
        role: c.role === "model" ? "assistant" : "user",
        content: text,
      });
    }
    return messages;
  }

  /**
   * Convert MAX AI messages into Anthropic Claude Messages API format.
   *
   * Claude expects system prompts in a top-level `system` string field,
   * and `messages` containing only alternating 'user' and 'assistant' roles.
   */
  static toAnthropic(messages: Message[]): AnthropicPayload {
    const systemParts: string[] = [];
    const anthropicMessages: AnthropicMessage[] = [];

    for (const m of messages) {
      const text =
        typeof m.content === "string"
          ? m.content
          : m.content
              .map((p) => (p.type === "text" ? p.text ?? "" : ""))
              .join("\n");

      if (m.role === "system" || m.role === "developer") {
        systemParts.push(text);
      } else {
        anthropicMessages.push({
          role: m.role === "assistant" ? "assistant" : "user",
          content: text,
        });
      }
    }

    return {
      system: systemParts.length > 0 ? systemParts.join("\n\n") : undefined,
      messages: anthropicMessages,
    };
  }

  /**
   * Convert Anthropic Claude messages back to MAX AI format.
   */
  static fromAnthropic(
    messages: AnthropicMessage[],
    system?: string
  ): Message[] {
    const result: Message[] = [];
    if (system) {
      result.push({ role: "system", content: system });
    }
    for (const m of messages) {
      result.push({
        role: m.role,
        content: m.content,
      });
    }
    return result;
  }

  /**
   * Convert long text / Markdown response into Discord-safe split chunks (<2000 chars),
   * intelligently handling markdown codeblocks so code styling is preserved across splits.
   */
  static toDiscord(text: string, options: DiscordChunkOptions = {}): string[] {
    const maxLength = options.maxChunkLength ?? 1990;
    const preserveCodeBlocks = options.preserveCodeBlocks ?? true;

    if (!Number.isInteger(maxLength) || maxLength <= 0) {
      throw new RangeError("maxChunkLength must be a positive integer");
    }

    if (text.length <= maxLength) {
      return [text];
    }

    const chunks: string[] = [];
    const lines = text.split("\n");
    let currentChunk = "";
    let activeCodeFence: string | null = null; // e.g. "```js" or "```"

    for (const line of lines) {
      // Track opening / closing code blocks
      const fenceMatch = line.match(/^```(\w+)?/);
      const isFence = fenceMatch !== null;

      const lineWithBreak = currentChunk.length === 0 ? line : `\n${line}`;

      if (currentChunk.length + lineWithBreak.length > maxLength) {
        if (preserveCodeBlocks && activeCodeFence) {
          // Close fence for current chunk
          currentChunk += "\n```";
          chunks.push(currentChunk);
          // Re-open fence on next chunk
          currentChunk = `${activeCodeFence}\n${line}`;
        } else {
          if (currentChunk) {
            chunks.push(currentChunk);
          }
          currentChunk = line;
        }
      } else {
        currentChunk += lineWithBreak;
      }

      if (isFence) {
        if (activeCodeFence) {
          activeCodeFence = null; // Closed
        } else {
          activeCodeFence = line.trim(); // Opened
        }
      }
    }

    if (currentChunk.length > 0) {
      chunks.push(currentChunk);
    }

    // A single unbroken line can still exceed the requested Discord limit.
    // Split that edge case so callers can rely on the hard size guarantee.
    return chunks.flatMap((chunk) => {
      if (chunk.length <= maxLength) return [chunk];
      const pieces: string[] = [];
      for (let i = 0; i < chunk.length; i += maxLength) {
        pieces.push(chunk.slice(i, i + maxLength));
      }
      return pieces;
    });
  }

  /**
   * Strip Markdown syntax for plaintext environments (SMS, CLI, notifications).
   */
  static toPlainText(markdown: string): string {
    return markdown
      // Remove code blocks
      .replace(/```[\s\S]*?```/g, (match) => {
        return match.replace(/```\w*\n?([\s\S]*?)```/, "$1").trim();
      })
      // Inline code
      .replace(/`([^`]+)`/g, "$1")
      // Images & Links
      .replace(/!\[(.*?)\]\(.*?\)/g, "$1")
      .replace(/\[(.*?)\]\(.*?\)/g, "$1")
      // Headers
      .replace(/^#{1,6}\s+(.*)$/gm, "$1")
      // Bold & Italic
      .replace(/\*\*([^*]+)\*\*/g, "$1")
      .replace(/\*([^*]+)\*/g, "$1")
      .replace(/__([^_]+)__/g, "$1")
      .replace(/_([^_]+)_/g, "$1")
      // Blockquotes
      .replace(/^>\s+/gm, "")
      // Horizontal rules
      .replace(/^[-*_]{3,}\s*$/gm, "")
      .trim();
  }

  /**
   * Convert tabular array data into a formatted GitHub-flavored Markdown table.
   */
  static toMarkdownTable(headers: string[], rows: (string | number)[][]): string {
    const colWidths = headers.map((h, i) => {
      const maxRowLen = rows.reduce(
        (max, row) => Math.max(max, String(row[i] ?? "").length),
        0
      );
      return Math.max(h.length, maxRowLen, 3);
    });

    const formatRow = (cells: (string | number)[]) =>
      "| " +
      cells
        .map((c, i) => String(c ?? "").padEnd(colWidths[i]))
        .join(" | ") +
      " |";

    const separator =
      "| " + colWidths.map((w) => "-".repeat(w)).join(" | ") + " |";

    const lines = [formatRow(headers), separator];
    for (const row of rows) {
      lines.push(formatRow(row));
    }
    return lines.join("\n");
  }
}

// Convenient function exports
export const toOpenAI = MaxConverter.toOpenAI;
export const fromOpenAI = MaxConverter.fromOpenAI;
export const toGemini = MaxConverter.toGemini;
export const fromGemini = MaxConverter.fromGemini;
export const toAnthropic = MaxConverter.toAnthropic;
export const fromAnthropic = MaxConverter.fromAnthropic;
export const toDiscord = MaxConverter.toDiscord;
export const toPlainText = MaxConverter.toPlainText;
export const toMarkdownTable = MaxConverter.toMarkdownTable;
