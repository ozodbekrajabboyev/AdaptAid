# DSA content pack

This folder holds all teaching content for the demo course. `adaptaid seed` loads it into the
database and `adaptaid validate-content` checks it. The platform itself is subject-agnostic: a
new course is a new folder with the same layout.

```
content/dsa/
├── course.json            course metadata, syllabus order, study concepts
├── concepts/<slug>.json   one file per concept: metadata, aids, questions
├── aids/<aid-slug>.md     body of every native (markdown) aid
├── questionnaire.json     learning-preference questionnaire (20 items)
├── sus.json               System Usability Scale (10 standard items)
└── RUBRIC.md              how style vectors and difficulty are assigned
```

## Concept file

```json
{
  "slug": "recursion",
  "name": "Recursion",
  "description": "One sentence a student would understand.",
  "prerequisites": ["complexity"],
  "aids": [ ... ],
  "questions": [ ... ]
}
```

### Aids

Every concept has **7 aids** (8 if it has a built-in interactive), in this teaching order
(`order` = the teacher's default order, used by the "course plan" control policy):

| order | type | delivery | slug |
|---|---|---|---|
| 1 | `notes` | `native_md` | `<concept>-notes` |
| 2 | `worked_example` | `native_md` | `<concept>-worked-example` |
| 3 | `video` | `external_url` | `<concept>-video` |
| 4 | `animation` (or `interactive`) | `external_url` | `<concept>-animation` |
| 5 | `concept_map` or `cheat_sheet` | `native_md` | `<concept>-concept-map` / `<concept>-cheat-sheet` |
| 6 | `practice` | `native_md` | `<concept>-practice` |
| 7 | `article` | `external_url` | `<concept>-article` |

Fields:

```json
{
  "slug": "recursion-notes",
  "title": "Recursion: base case, recursive case, call stack",
  "type": "notes",
  "delivery": "native_md",           // native_md | external_url | interactive_component
  "body": "recursion-notes.md",       // native_md only: file in aids/
  "url": "https://...",               // external_url only, https, checked by check-links
  "component": "recursion-stack",     // interactive_component only: sorting-stepper | recursion-stack | bst-builder
  "source": "AdaptAid",               // who made it: AdaptAid, VisuAlgo, USFCA, YouTube channel name, Programiz, ...
  "description": "One sentence shown on the card.",
  "difficulty": 2,                    // 1-5, see RUBRIC.md
  "duration": 10,                     // minutes
  "order": 1,
  "style": [0.1, 0.8, -0.2, 0.8]      // optional; omit to use the RUBRIC default for the type
}
```

### Native aid bodies (`aids/*.md`)

GitHub-flavoured markdown. Code in fenced blocks with a language (`python`). Diagrams in
` ```mermaid ` blocks (flowchart / graph). No raw HTML. Keep it student-friendly.

- **notes**: 250–450 words. What it is, why it matters, how it works, the key operations
  and their costs, a common mistake.
- **worked_example**: one realistic problem solved step by step (numbered steps), with code
  and a trace table or the intermediate states, ending with the result and its complexity.
- **concept_map**: a mermaid diagram of how the ideas relate, plus 3–5 bullet takeaways.
- **cheat_sheet**: a compact table of operations, costs and when to use what.
- **practice**: a short intro (2–3 sentences) telling the student to work through the drill
  questions below; the drill questions themselves are in the concept file (`pool: drill`).

### Questions

All multiple choice with exactly 4 options and one correct answer.

```json
{
  "key": "recursion-c03",            // unique; <concept>-<pool letter><nn>: d diagnostic, c check, p drill, a/b study forms
  "pool": "check",                    // diagnostic | check | drill | study
  "stem": "Markdown text. Code in `backticks` or fenced blocks.",
  "options": ["...", "...", "...", "..."],
  "answer": 2,                        // 0-based index
  "explanation": "Why the answer is right and the tempting wrong one is wrong.",
  "difficulty": 2,                    // 1 easy, 2 medium, 3 hard
  "aid": "recursion-practice",       // drill only: the practice aid it belongs to
  "form": "A"                         // study only: A or B
}
```

Per concept: **1 diagnostic, 10 check, 5 drill**. Study concepts (`course.json`) also have
**5 study items in form A and 5 in form B**: parallel forms of matched difficulty covering the
same sub-skills, used only for the pilot's pre/post tests. Study item text must not appear
anywhere else (the validator checks).

Distractors must be plausible (common misconceptions), options of similar length, no "all of
the above", and the correct option position should vary.
