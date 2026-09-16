"""
examples/multi_agent_team.py — Programmatic Multi-Agent Team Pipeline Example.

Demonstrates chaining multiple specialized AI agents:
    1. Planner (Software Architect) -> Designs specifications
    2. Coder (Full-Stack Dev)       -> Writes code
    3. Reviewer (Security & QA)     -> Validates and optimizes
"""

import max_ai

if __name__ == "__main__":
    print("🚀 Initializing MAX Multi-Agent Team Pipeline...")

    team = max_ai.Team(name="DevOps & Web Engineering Team")

    # Define custom team members
    team.add_member(
        id=1,
        name="Lead Architect",
        role="planner",
        model="gemini-2.5-flash",
        system_prompt="You are a Lead Software Architect. Outline the file structure, API routes, and database schema.",
    )
    team.add_member(
        id=2,
        name="Senior Coder",
        role="coder",
        model="deepseek-v4.1-flash",
        system_prompt="You are a Senior Python Developer. Implement clean, robust, commented Python code.",
    )
    team.add_member(
        id=3,
        name="QA & Security Auditor",
        role="reviewer",
        model="gemini-2.5-flash",
        system_prompt="You are a Senior Security Auditor. Review the code for security holes, edge cases, and performance.",
    )

    # Link pipeline: 1 -> 2 -> 3
    team.link(from_id=1, to_id=2)
    team.link(from_id=2, to_id=3)

    task = "สร้าง Discord Bot ระบบแจ้งเตือนราคาทองคำและเหรียญคริปโตอัตโนมัติ"
    print(f"\n📋 Starting Pipeline on Task: {task}\n")

    def on_step_progress(member, output):
        print(f"\n=======================================================")
        print(f"✅ [{member.name}] (Role: {member.role}, Model: {member.model}) Completed:")
        print(f"=======================================================")
        print(output[:300] + ("..." if len(output) > 300 else ""))

    # Run pipeline
    # results = team.run(task, on_step=on_step_progress)
    # print(f"\n🎉 Finished in {results['total_steps']} steps.")
    print("Team pipeline is ready for execution.")
