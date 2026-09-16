/**
 * types.ts — Type definitions for MAX AI JavaScript/TypeScript SDK.
 */

export type Role = "user" | "assistant" | "system" | "developer" | "tool";

export interface Message {
  role: Role;
  content: string | Array<{ type: string; text?: string; image_url?: string | { url: string } }>;
  tool_call_id?: string;
}

export interface AgentOptions {
  model?: string;
  provider?: string;
  apiKey?: string;
  baseUrl?: string;
  systemPrompt?: string;
  temperature?: number;
  maxTokens?: number;
  timeout?: number;
  apiMode?: "chat_completions" | "responses";
}

export interface SessionOptions {
  sessionId?: string;
  systemPrompt?: string;
  maxHistory?: number;
}

export interface TeamMemberConfig {
  id: number;
  name: string;
  role?: string;
  model?: string;
  apiKey?: string;
  systemPrompt?: string;
}

export interface TeamStepResult {
  step: number;
  memberId: number;
  memberName: string;
  memberRole: string;
  model: string;
  input: string;
  output: string;
}

export interface TeamRunResult {
  task: string;
  finalOutput: string;
  steps: TeamStepResult[];
  totalSteps: number;
}

export interface DiscordBotOptions {
  discordToken: string;
  maxApiKey?: string;
  model?: string;
  commandPrefix?: string;
  systemPrompt?: string;
  respondToMentions?: boolean;
  respondToDMs?: boolean;
}
