/**
 * MAX AI — JavaScript / TypeScript SDK & Discord AI Bot Kit.
 *
 * Usage:
 *   import { MaxAgent, MaxTeam, createDiscordBot, ask } from "@karanztez/max-ai";
 *
 *   const reply = await ask("Hello, explain quantum physics");
 *   console.log(reply);
 */

import { MaxAgent } from "./agent.js";
import { MaxSession, MaxResponse } from "./session.js";
import { MaxTeam, TeamMember } from "./team.js";
import { MaxDiscordBot, createDiscordBot, splitDiscordMessage } from "./discord.js";
import {
  MaxConverter,
  toOpenAI,
  fromOpenAI,
  toGemini,
  fromGemini,
  toAnthropic,
  fromAnthropic,
  toDiscord,
  toPlainText,
  toMarkdownTable,
  type OpenAIMessage,
  type GeminiContent,
  type AnthropicMessage,
  type AnthropicPayload,
  type DiscordChunkOptions,
} from "./converter.js";
import type {
  AgentOptions,
  Message,
  Role,
  SessionOptions,
  TeamMemberConfig,
  TeamRunResult,
  TeamStepResult,
  DiscordBotOptions,
} from "./types.js";

// Convenient aliases
export const Agent = MaxAgent;
export const Session = MaxSession;
export const Team = MaxTeam;
export const Converter = MaxConverter;

export const VERSION = "1.0.5";

/**
 * Convenience 1-liner to ask a single question.
 */
export async function ask(
  prompt: string,
  options: AgentOptions & { temperature?: number; maxTokens?: number } = {}
): Promise<string> {
  const agent = new MaxAgent(options);
  return agent.ask(prompt, options);
}

/**
 * Convenience function to stream response tokens.
 */
export async function* stream(
  prompt: string,
  options: AgentOptions & { temperature?: number; maxTokens?: number } = {}
): AsyncIterable<string> {
  const agent = new MaxAgent(options);
  for await (const chunk of agent.stream(prompt, options)) {
    yield chunk;
  }
}

export {
  MaxAgent,
  MaxSession,
  MaxResponse,
  MaxTeam,
  TeamMember,
  MaxDiscordBot,
  createDiscordBot,
  splitDiscordMessage,
  MaxConverter,
  toOpenAI,
  fromOpenAI,
  toGemini,
  fromGemini,
  toAnthropic,
  fromAnthropic,
  toDiscord,
  toPlainText,
  toMarkdownTable,
};

export type {
  AgentOptions,
  Message,
  Role,
  SessionOptions,
  TeamMemberConfig,
  TeamRunResult,
  TeamStepResult,
  DiscordBotOptions,
  OpenAIMessage,
  GeminiContent,
  AnthropicMessage,
  AnthropicPayload,
  DiscordChunkOptions,
};
