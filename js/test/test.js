/**
 * js/test/test.js — Node.js test suite for @karanztez/max-ai SDK.
 */

import assert from "node:assert/strict";
import {
  MaxAgent,
  MaxSession,
  MaxTeam,
  MaxConverter,
  toOpenAI,
  toGemini,
  toAnthropic,
  toDiscord,
  toPlainText,
  toMarkdownTable,
  splitDiscordMessage,
  VERSION,
} from "../dist/index.js";

console.log("🧪 Running MAX AI JavaScript SDK Tests...");

// 1. Version test
assert.equal(VERSION, "1.0.2");
console.log("✅ VERSION matched: 1.0.2");

// 2. Agent Initialization
const agent = new MaxAgent({
  model: "deepseek-v4.1-flash",
  apiKey: "test-token",
  systemPrompt: "You are a test assistant",
  temperature: 0.8,
  maxTokens: 1024,
});
assert.equal(agent.model, "deepseek-v4.1-flash");
assert.equal(agent.apiKey, "test-token");
assert.equal(agent.systemPrompt, "You are a test assistant");
assert.equal(agent.temperature, 0.8);
assert.equal(agent.maxTokens, 1024);
console.log("✅ MaxAgent initialization passed");

// 3. Session History & Memory Trimming
const session = agent.createSession("user-channel-1", { maxHistory: 4 });
assert.equal(session.sessionId, "user-channel-1");
assert.equal(session.history.length, 0);

session.addMessage("user", "Hello 1");
session.addMessage("assistant", "Hi 1");
session.addMessage("user", "Hello 2");
session.addMessage("assistant", "Hi 2");
session.addMessage("user", "Hello 3"); // Should trim the oldest message

assert.equal(session.history.length, 4);
assert.equal(session.history[session.history.length - 1].content, "Hello 3");
console.log("✅ MaxSession memory management & trimming passed");

session.clear();
assert.equal(session.history.length, 0);
console.log("✅ MaxSession clear passed");

// 4. Team Pipeline Linking
const team = new MaxTeam("Dev Team");
team.addMember({ id: 1, name: "Planner", role: "planner" });
team.addMember({ id: 2, name: "Coder", role: "coder" });
team.addMember({ id: 3, name: "Reviewer", role: "reviewer" });

team.link(1, 2);
team.link(2, 3);

assert.equal(team.members.get(1)?.linkedTo, 2);
assert.equal(team.members.get(2)?.linkedTo, 3);
assert.equal(team.members.get(3)?.linkedTo, null);
console.log("✅ MaxTeam member linking passed");

// 5. Discord Message Splitting (<2000 chars)
const shortMsg = "Hello Discord";
assert.deepEqual(splitDiscordMessage(shortMsg, 100), [shortMsg]);

const longMsg = "A".repeat(250);
const chunks = splitDiscordMessage(longMsg, 100);
assert.equal(chunks.length, 3);
assert.equal(chunks[0].length, 100);
assert.equal(chunks[1].length, 100);
assert.equal(chunks[2].length, 50);
assert.throws(() => splitDiscordMessage("test", 0), RangeError);
console.log("✅ Discord message chunking passed");

// 6. MaxConverter — OpenAI format conversion
const rawMessages = [
  { role: "system", content: "Act as assistant" },
  { role: "user", content: "Hello!" },
  { role: "assistant", content: "Hi there!" },
];
const openAIMsgs = toOpenAI(rawMessages);
assert.equal(openAIMsgs.length, 3);
assert.equal(openAIMsgs[0].role, "system");
assert.equal(openAIMsgs[1].role, "user");
assert.equal(openAIMsgs[2].role, "assistant");
console.log("✅ MaxConverter.toOpenAI passed");

// 7. MaxConverter — Google Gemini format conversion
const geminiData = toGemini(rawMessages);
assert.equal(geminiData.systemInstruction, "Act as assistant");
assert.equal(geminiData.contents.length, 2);
assert.equal(geminiData.contents[0].role, "user");
assert.equal(geminiData.contents[0].parts[0].text, "Hello!");
assert.equal(geminiData.contents[1].role, "model");
assert.equal(geminiData.contents[1].parts[0].text, "Hi there!");
console.log("✅ MaxConverter.toGemini passed");

const discordChunks = toDiscord("A".repeat(250), { maxChunkLength: 100 });
assert.deepEqual(discordChunks.map((chunk) => chunk.length), [100, 100, 50]);
assert.throws(() => toDiscord("test", { maxChunkLength: 0 }), RangeError);
console.log("✅ MaxConverter.toDiscord hard limit passed");

// 8. MaxConverter — Anthropic Claude format conversion
const anthropicData = toAnthropic(rawMessages);
assert.equal(anthropicData.system, "Act as assistant");
assert.equal(anthropicData.messages.length, 2);
assert.equal(anthropicData.messages[0].role, "user");
assert.equal(anthropicData.messages[1].role, "assistant");
console.log("✅ MaxConverter.toAnthropic passed");

// 9. MaxConverter — Markdown to PlainText
const md = "# Title\n**bold text** and `code` with [link](https://example.com)";
const plain = toPlainText(md);
assert.equal(plain, "Title\nbold text and code with link");
console.log("✅ MaxConverter.toPlainText passed");

// 10. MaxConverter — Markdown Table
const table = toMarkdownTable(["Name", "Role"], [["Max", "Agent"], ["Alice", "User"]]);
assert(table.includes("| Name"));
assert(table.includes("| Max"));
console.log("✅ MaxConverter.toMarkdownTable passed");

console.log("\n🎉 ALL JavaScript SDK & Converter Tests Passed Successfully!\n");
