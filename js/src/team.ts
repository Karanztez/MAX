/**
 * team.ts — Multi-Agent Team Pipeline orchestrator for MAX AI JavaScript SDK.
 */

import { MaxAgent } from "./agent.js";
import type { TeamMemberConfig, TeamRunResult, TeamStepResult } from "./types.js";

export class TeamMember {
  public linkedTo: number | null = null;
  public agent: MaxAgent;

  constructor(
    public readonly id: number,
    public readonly name: string,
    public readonly role: string = "general",
    public readonly model: string = "gemini-2.5-flash",
    apiKey?: string,
    systemPrompt?: string
  ) {
    this.agent = new MaxAgent({
      model,
      apiKey,
      systemPrompt: systemPrompt || `You are ${name}, a specialized ${role} agent in the MAX AI team pipeline.`,
    });
  }
}

export class MaxTeam {
  public members: Map<number, TeamMember> = new Map();

  constructor(public readonly name: string = "Default Team") {}

  addMember(config: TeamMemberConfig): TeamMember {
    const member = new TeamMember(
      config.id,
      config.name,
      config.role || "general",
      config.model || "gemini-2.5-flash",
      config.apiKey,
      config.systemPrompt
    );
    this.members.set(config.id, member);
    return member;
  }

  link(fromId: number, toId: number): void {
    const member = this.members.get(fromId);
    if (member) {
      member.linkedTo = toId;
    }
  }

  unlink(fromId: number): void {
    const member = this.members.get(fromId);
    if (member) {
      member.linkedTo = null;
    }
  }

  createDefaultPipeline(model: string = "gemini-2.5-flash"): void {
    this.members.clear();
    this.addMember({
      id: 1,
      name: "Planner",
      role: "planner",
      model,
      systemPrompt: "You are a Lead Software Architect. Create a step-by-step implementation plan.",
    });
    this.addMember({
      id: 2,
      name: "Coder",
      role: "coder",
      model,
      systemPrompt: "You are an Expert Developer. Write robust, clean production code.",
    });
    this.addMember({
      id: 3,
      name: "Reviewer",
      role: "reviewer",
      model,
      systemPrompt: "You are a Senior QA Reviewer. Audit the output for security and quality.",
    });
    this.link(1, 2);
    this.link(2, 3);
  }

  async run(
    task: string,
    options: {
      startId?: number;
      maxHops?: number;
      onStep?: (member: TeamMember, output: string) => void;
    } = {}
  ): Promise<TeamRunResult> {
    if (this.members.size === 0) {
      this.createDefaultPipeline();
    }

    let currentId: number | null = options.startId ?? 1;
    let currentInput = task;
    let hops = 0;
    const maxHops = options.maxHops ?? 6;
    const steps: TeamStepResult[] = [];
    const visited = new Set<number>();

    while (currentId !== null && hops < maxHops) {
      if (!this.members.has(currentId) || visited.has(currentId)) {
        break;
      }

      const member: TeamMember = this.members.get(currentId)!;
      visited.add(currentId);
      hops++;

      const prompt = `Your task / previous input is:\n\n${currentInput}\n\nPlease produce your specialized contribution as the ${member.role} (${member.name}).`;
      const response = await member.agent.ask(prompt);

      steps.push({
        step: hops,
        memberId: member.id,
        memberName: member.name,
        memberRole: member.role,
        model: member.model,
        input: currentInput,
        output: response,
      });

      if (options.onStep) {
        options.onStep(member, response);
      }

      currentInput = response;
      currentId = member.linkedTo;
    }

    return {
      task,
      finalOutput: currentInput,
      steps,
      totalSteps: hops,
    };
  }
}
