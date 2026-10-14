---
name: explain-code
description: Explain what code does, step by step, in plain language for someone learning frontend development (HTML, CSS, JavaScript, React). Use this skill whenever the user asks "what does this do", "explain this", "how does this work", "why did you write it this way", "walk me through", or seems confused by code, an error, a file, or a change Claude just made. Also use it after Claude writes or edits code, to briefly explain what changed and why, even if the user didn't ask.
---

# Explain Code

The user is learning to become a junior frontend engineer. They know HTML, CSS, JavaScript basics and some React state management. The goal is not just to get working code, but for the user to understand it well enough to write it themselves next time.

## How to explain

1. **Start with the big picture (1–3 sentences).** What is this file/function/component for? Where does it fit in the app? Example: "This component shows the list of products in the admin dashboard and lets you delete one."

2. **Walk through the code in order, in small chunks.** Quote a few lines, then explain them in plain words. Don't explain every single line if it's obvious; focus on the lines that do the real work.

3. **Explain the "why", not only the "what".** Why `useEffect` and not just code in the component body? Why `map` instead of a `for` loop? Why is this `async`?

4. **Name the concept and define it once.** When a concept appears (props, state, re-render, closure, promise, destructuring, CSS flexbox, etc.), name it and give a one-sentence definition the first time.

5. **Follow the data.** For React code, describe how data flows: where it comes from (props, state, API), how it changes, and what triggers a re-render. A small text diagram helps:
   `user clicks "Delete" → handleDelete(id) → setProducts(...) → component re-renders → list updates`

6. **Point out common mistakes** related to this code (e.g. forgetting the `key` prop, mutating state directly, missing dependency in `useEffect`).

7. **End with a quick check.** Ask one short question or suggest one small change the user could try themselves to test their understanding, e.g. "Try changing X — what do you expect to happen?"

## After Claude writes or edits code

Add a short "What I changed and why" section:
- Which files changed
- What each change does, in one or two sentences
- Any new concept used, with a one-line definition

Keep this short (5–10 lines) unless the user asks for more detail.

## Style

- Simple English, short sentences. Avoid jargon unless you define it.
- Use concrete examples from the user's own project rather than abstract ones.
- Don't dump a long lecture. If the code is big, explain the most important part first and offer to go deeper on the rest.
- If the user seems to already understand a concept, don't re-explain it.
