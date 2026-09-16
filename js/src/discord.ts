/**
 * discord.ts — Discord Bot builder and utilities for MAX AI JavaScript SDK.
 */

import { MaxAgent } from "./agent.js";
import type { DiscordBotOptions } from "./types.js";

export function splitDiscordMessage(text: string, limit: number = 1900): string[] {
  if (!Number.isInteger(limit) || limit <= 0) {
    throw new RangeError("limit must be a positive integer");
  }
  if (text.length <= limit) {
    return [text];
  }
  const chunks: string[] = [];
  const lines = text.split("\n");
  let currentChunk = "";

  for (const line of lines) {
    if (currentChunk.length + line.length + 1 > limit) {
      if (currentChunk.trim()) {
        chunks.push(currentChunk.trim());
        currentChunk = "";
      }
      if (line.length > limit) {
        for (let i = 0; i < line.length; i += limit) {
          chunks.push(line.slice(i, i + limit));
        }
        continue;
      }
    }
    currentChunk += line + "\n";
  }

  if (currentChunk.trim()) {
    chunks.push(currentChunk.trim());
  }
  return chunks;
}

export class MaxDiscordBot {
  public readonly agent: MaxAgent;
  public readonly commandPrefix: string;
  public readonly respondToMentions: boolean;
  public readonly respondToDMs: boolean;

  constructor(public readonly options: DiscordBotOptions) {
    this.commandPrefix = options.commandPrefix || "!max ";
    this.respondToMentions = options.respondToMentions ?? true;
    this.respondToDMs = options.respondToDMs ?? true;
    this.agent = new MaxAgent({
      model: options.model || "gemini-2.5-flash",
      apiKey: options.maxApiKey,
      systemPrompt: options.systemPrompt || "You are MAX, a helpful and friendly Discord AI assistant.",
    });
  }

  /**
   * Attach MAX AI message handling logic to an existing discord.js Client instance.
   */
  attachToClient(client: any): void {
    client.on("messageCreate", async (message: any) => {
      if (message.author?.bot) return;

      const content = (message.content || "").trim();
      const isDM = !message.guild;
      const isMention = this.respondToMentions && client.user && message.mentions?.has?.(client.user.id);
      const startsWithPrefix = content.startsWith(this.commandPrefix);

      let prompt = "";
      if (startsWithPrefix) {
        prompt = content.slice(this.commandPrefix.length).trim();
      } else if (isMention && client.user) {
        prompt = content.replace(new RegExp(`<@!?${client.user.id}>`, "g"), "").trim();
      } else if (isDM && this.respondToDMs) {
        prompt = content;
      }

      if (!prompt) return;

      const channelId = String(message.channelId || message.channel?.id || "dm");

      if (prompt.toLowerCase() === "reset" || prompt.toLowerCase() === "clear") {
        const session = this.agent.getSession(channelId, false);
        if (session) {
          session.clear();
        }
        await message.reply("🧹 ล้างประวัติการสนทนาในห้องนี้เรียบร้อยแล้วครับ! (Session reset)");
        return;
      }

      if (prompt.toLowerCase() === "help") {
        await message.reply(
          `**🤖 MAX AI Discord Bot**\n• โมเดลปัจจุบัน: \`${this.agent.model}\`\n• คำสั่ง: \`${this.commandPrefix}<คำถาม>\` หรือ Mention @${client.user?.username}\n• ล้างประวัติ: \`${this.commandPrefix}reset\``
        );
        return;
      }

      const session = this.agent.getSession(channelId, true)!;
      try {
        if (message.channel?.sendTyping) {
          await message.channel.sendTyping();
        }
        const res = await session.send(prompt);
        const chunks = splitDiscordMessage(res.text);
        for (const chunk of chunks) {
          await message.reply(chunk);
        }
      } catch (err: any) {
        await message.reply(`⚠️ เกิดข้อผิดพลาด: \`${err.message || err}\``);
      }
    });
  }
}

export function createDiscordBot(options: DiscordBotOptions): MaxDiscordBot {
  return new MaxDiscordBot(options);
}
