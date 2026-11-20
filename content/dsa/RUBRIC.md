# Teaching-aid tagging rubric

Every aid carries a Felder–Silverman style vector with four components in [-1, 1]:

| Component | +1 pole | -1 pole |
|---|---|---|
| `ar` | active (learn by doing) | reflective (learn by thinking it through) |
| `si` | sensing (concrete facts, examples, procedures) | intuitive (abstractions, theory, relationships) |
| `vv` | visual (diagrams, animation, video) | verbal (written or spoken words) |
| `sg` | sequential (step by step) | global (big picture first) |

## 1. Start from the default vector for the aid type

| Aid type | ar | si | vv | sg | Interactivity | Why |
|---|---|---|---|---|---|---|
| `video` | -0.3 | 0.0 | 0.6 | 0.5 | expositive | watched, mostly visual, follows a narrative order |
| `animation` | 0.3 | 0.2 | 0.9 | 0.6 | mixed | visual, learner steps through it |
| `interactive` | 0.9 | 0.5 | 0.8 | 0.4 | active | learner manipulates a live visualisation |
| `notes` | -0.5 | 0.0 | -0.8 | 0.6 | expositive | read and reflected on, structured text |
| `worked_example` | 0.1 | 0.8 | -0.2 | 0.8 | expositive | concrete, procedural, step by step |
| `cheat_sheet` | 0.0 | 0.2 | -0.4 | -0.8 | expositive | overview of everything at once |
| `concept_map` | -0.2 | -0.5 | 0.8 | -0.8 | expositive | relationships between ideas, drawn |
| `practice` | 0.9 | 0.6 | -0.3 | 0.3 | active | doing exercises, concrete |
| `article` | -0.4 | -0.4 | -0.7 | 0.3 | expositive | longer text, more theory |

## 2. Adjust only for clear reasons (at most ±0.3 per component)

- A video that is mainly a talking head or slides of text: lower `vv` by 0.2–0.3.
- A video or article that leads with a real-world application: raise `si` by 0.2.
- An article that is mostly proofs or formal definitions: lower `si` by 0.2.
- Notes that open with a one-paragraph overview and a diagram: lower `sg` by 0.2, raise `vv` by 0.2.
- An animation you watch rather than step through: lower `ar` by 0.3.

Write the final vector in the concept file only when it differs from the default.

## 3. Difficulty (1–5)

1 introduces the idea, 2 covers the standard material, 3 adds analysis or edge cases, 4 is
interview or exam level, 5 is beyond the course. Most aids are 2 or 3.

## Coverage rule (checked by `adaptaid validate-content`)

Each concept needs at least four different aid types, including at least one aid on each
side of the visual/verbal dimension (`vv` > 0.3 and `vv` < -0.3) and on each side of the
active/reflective dimension (`ar` > 0.3 and `ar` < -0.3).
