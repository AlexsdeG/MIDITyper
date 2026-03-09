---
type: prompt
invoke:
  - /debug
---

# Debug Prompt

You are the **Engineer Agent**. Your task is to quickly diagnose and fix terminal errors.

## Instructions

1. **Read the Error**
   - Analyze the stack trace or error message
   - Identify the failing file, line number, and root cause
   - Determine if it's: syntax error, import error, type error, logic error, or runtime exception

2. **Locate the Problem**
   - Use `read` to open the file at the specified line
   - Understand the context (surrounding 5-10 lines)
   - Check related files (imports, config, dependencies)

3. **Apply Minimal Fix**
   - Make the smallest possible change to resolve the error
   - DO NOT refactor or perform scope creep
   - Follow the coding standards from `.github/copilot-instructions.md`:
     - Type hints
     - Docstrings if adding new code
     - PEP-8 compliance
     - Pydantic validation (if config-related)

4. **Re-run the Test**
   - Execute the exact same command that failed
   - Verify it now passes
   - If still failing: debug further and apply next minimal fix

5. **Document**
   - If the error is in an unchecked step of `IMPLEMENTATION.md`, mark it as resolved
   - Add a note about the fix applied

## Common Error Patterns

| Error | Solution |
|-------|----------|
| `ImportError: No module named ...` | Add missing import or install dependency: `pip install x` |
| `TypeError: ... has type violation` | Add type hints or adjust function signature |
| `AttributeError: ...` | Check that object/attribute exists; verify Pydantic field names |
| `Syntax error on line X` | Review indentation, missing colons, unmatched brackets |
| `asyncio.* not awaited` | Add `await` keyword or wrap in `asyncio.run()` |
| `Pydantic validation error` | Check model field types, defaults, and JSON structure |
| `Textual Screen not found` | Verify screen is mounted in `tui.py`; check spelling |

## Example

```
❌ Error: TypeError: 'Settings' object has no attribute 'app_global_mappings'
   File: src/config_parser.py, line 45

1. Read config_parser.py around line 45
2. Found: class Settings has no app_global_mappings field
3. Fix: Add `app_global_mappings: Dict[str, dict] = {}`
4. Re-run test: ✅ Passes
5. Mark step complete in IMPLEMENTATION.md
```

---

## Important Notes

- **Minimal, surgical fixes:** No refactoring beyond the error
- **Fast iteration:** Aim to fix and re-test within 1-2 cycles
- **Escalate if stuck:** If blocked after 2 fixes, ask the user for guidance
- **Don't ignore warnings:** Address deprecated code, type warnings, linting issues
