---
description: Dynamically analyzes the codebase and scaffolds a complete 2026 AI Agent architecture.
agent: Architect
tools: [read, search, edit, execute]
---

# Universal AI Workspace Initializer

You are tasked with bootstrapping this repository with a modern 2026 AI Agent architecture. This system must be language and framework agnostic. 

Execute the following phases sequentially.

## Phase 1: Codebase Analysis
1. Scan the root directory (e.g., `package.json`, `composer.json`, `requirements.txt`, `go.mod`).
2. Identify the primary programming language, framework, and package manager.
3. Identify the testing framework and linting tools currently in use.

## Phase 2: Scaffold Instructions & Docs
Generate the following files tailored EXACTLY to the stack you discovered in Phase 1:
- **`.github/copilot-instructions.md`**: The routing file. Define the tech stack, strict coding standards (e.g., TypeScript strict mode, PEP-8), and verification commands.
- **`.github/docs/architecture-blueprint.md`**: A brief mapping of where business logic, routes, and UI components live in this specific repo.

## Phase 3: Scaffold Custom Agents
Create the standard dual-agent setup in `.vscode/agents/`:
- **`architect.agent.md`**: Tools: `[read, search]`. Persona: System planner. Does not write code. Generates `IMPLEMENTATION.md` checklists.
- **`engineer.agent.md`**: Tools: `[read, edit, execute]`. Persona: Senior Developer. Executes checklists, writes code, and runs tests.

## Phase 4: Scaffold Core Prompts
Create the following essential action shortcuts in `.vscode/prompts/`:

1. **`plan.prompt.md` (/plan)**
   - Instructs the Architect to read the user request and generate a strict, checkbox-based `IMPLEMENTATION.md` file with distinct phases.
   
2. **`execute.prompt.md` (/execute)**
   - Instructs the Engineer to read `IMPLEMENTATION.md`, implement the first unchecked `[ ]` step, run the required tests, check the box `[x]`, and loop.
   - **MANDATORY DIRECTIVE IN THIS PROMPT:** "Upon completing the final phase of any plan, you MUST automatically bump the semantic version in the relevant configuration file (e.g., package.json) and add a bulleted summary of changes to `CHANGELOG.md`."

3. **`debug.prompt.md` (/debug)**
   - Instructs the Engineer to read the terminal error, locate the file, apply the exact minimal fix, and re-run the test to verify.

4. **`explain.prompt.md` (/explain)**
   - Instructs the Architect to analyze the selected code and provide a dry, highly technical explanation of the data flow and architectural patterns, skipping basic programming concepts.

## Execution Requirements:
Generate and save all these files directly into the workspace. Ensure they follow the 2026 standard (lean, high-signal, zero-fluff). When finished, output a brief summary of the stack you detected and the files you created.