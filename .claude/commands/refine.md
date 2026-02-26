Reflect on this session and update the project documentation with what we learned.

## Steps

1. **Review the session.** Think about:
   - What problems did we encounter?
   - What did we change and why?
   - What worked? What didn't?
   - Any new insights about how the models behave?
   - Any new debugging techniques or workflows discovered?

2. **Scan existing docs.** Run `find docs/ -name "*.md" | sort` to see what documentation exists.

3. **Read relevant docs.** Read only the docs that relate to what we worked on this session.

4. **Update docs.** For each learning:
   - If it fits an existing doc, update that doc (don't duplicate).
   - If it's a new topic, create a new doc in the appropriate folder:
     - `docs/pipeline/` — how the pipeline works, prompt strategy, config
     - `docs/learnings/` — iteration logs, model behavior insights
     - `docs/actions/` — how to perform specific tasks/tests
   - Keep docs concise and scannable. Use tables and bullet points.
   - Include dates on iteration entries.

5. **Present a summary** of what was updated or created.

## Rules

- Do NOT edit CLAUDE.md.
- Do NOT add information you're unsure about — only confirmed learnings.
- Do NOT duplicate content across docs — pick one home for each fact.
- Keep each doc focused on a single topic.
- If a learning contradicts something in an existing doc, update the existing doc (don't leave stale info).
