# AdaptAid pilot study protocol

Write this down and get it approved **before** the pilot starts. Changing the analysis after
seeing the data would make the result unreliable. Version 1.0.

## 1. Question

Does AdaptAid's adaptive recommendation of teaching aids help students learn more than the
same teaching aids offered in a fixed course-plan order?

- **H1 (primary).** After about two weeks, students in the adaptive arm score higher on the
  post-test than students in the control arm, after adjusting for their pre-test score.
- **H2 (secondary).** Adaptive students show higher normalised learning gain, open and
  finish more recommended aids, and rate usability at least as high (SUS).

## 2. Design

A two-arm randomised controlled pilot with a pre-test and a post-test.

| | Adaptive arm | Control arm ("course plan") |
|---|---|---|
| Concept chosen next | Highest need × concepts it unlocks, from the student's mastery | Next concept in syllabus order (advance after a passed check or 3 aids) |
| Aid ranking | Hybrid recommender (need, style, level, CF, helpfulness) | Teacher's default order: notes → worked example → visual → practice |
| Card reason | Personal explanation | "Next in the course plan." |
| Everything else | Identical: same aids, same quick checks, same mastery display, same screens | Identical |

Only the choice of concept and the ranking of aids differ, so a difference in outcome can be
attributed to the adaptive logic itself.

## 3. Participants and consent

- Students in the course who join the pilot class with its code. Target: **20 or more per
  arm** (see the power analysis in section 7).
- **Consent:** each student sees the consent text (Admin → Pilot study) and must agree before
  taking part. Taking part is voluntary, does not affect grades, and students can stop at any time.
- **Inclusion in the analysis:** students who consented and completed both tests.
- **Exclusion:** demo or simulated accounts (`users.is_synthetic`). The pilot instance must
  never run `seed-demo`.

## 4. Procedure

| Day | What happens |
|---|---|
| Before | The guide approves this protocol and the consent text. The admin sets "Study running" **and** "Freeze model parameters", and checks that the pilot instance has no demo data. |
| 0 | Students sign up with the class code → consent → **pre-test** (form A or B) → arm assignment → preference questionnaire → diagnostic. |
| 1–14 | Students use AdaptAid as often as they like (suggested: three sessions a week). Quick checks after each aid. |
| 14 | The admin turns on "Post-test open". Students take the **post-test** (the other form), then the **SUS + satisfaction survey**. |
| After | Admin → Pilot study → Download CSV. Run the analysis (section 6). |

## 5. Measures

- **Tests.** Four study concepts (stacks, queues, recursion, hashing), five items each, in two
  parallel forms (A, B) matched item by item on sub-skill and difficulty. Each student gets
  A then B, or B then A, alternating within the class (counterbalancing), so any difference
  between the forms cancels out. Study items never appear in practice material (checked by
  `adaptaid validate-content`).
- **Normalised gain** (Hake, 1998): g = (post − pre) / (1 − pre).
- **Engagement.** Aid sessions, quick checks, completion rate and active days (from the logs).
- **Usability.** System Usability Scale (Brooke, 1996), 0–100, where 68 is the usual average. Plus five satisfaction items (1–5).

## 6. Analysis (pre-specified)

Run `backend/.venv/bin/python -m research.src.pilot_analysis pilot_study.csv`.

1. **Primary.** ANCOVA, `post_score ~ pre_score + arm`. Report the arm effect with its 95% CI and p-value, at α = 0.05, two-sided.
2. **Secondary.** Mean normalised gain by arm, with the difference, a bootstrap 95% CI (4,000 resamples), Mann–Whitney U and Cohen's d. Also SUS, satisfaction and engagement by arm, described.
3. **Randomisation.** Stratified by pre-test score band (low, middle, high) within the class: each new student goes to the arm with fewer members in their band, with ties broken at random.
4. **Missing data.** Students without a post-test are reported (count by arm) but not imputed.

The analysis script was checked before the study (`--self-test`). It detects a planted effect
in simulated pilot data and does not detect one in null data.

## 7. Power and how to report the result

Power was estimated by simulation (200 runs per cell, ANCOVA at α = 0.05):

| Students per arm | No real effect (false positives) | Moderate effect | Large effect |
|---|---|---|---|
| 15 | 6% | 34% | 77% |
| 20 | 4% | 47% | 90% |
| 30 | 2% | 65% | 99% |

"Large" means about 25% more of the remaining material learned (around +10 percentage
points on the post-test); "moderate" means about 15%.

**With a class-sized pilot (10–20 students per arm), only a large effect is likely to reach
significance.** Report the pilot as a feasibility study with an effect-size estimate and its
confidence interval, not only as "significant" or "not significant". A non-significant result
with a wide CI means "not enough evidence yet", not "no effect".

## 8. Data handling

- Collect only what is needed: quiz answers, aid usage, survey answers. No sensitive personal data.
- The export uses pseudonymous ids (P001, P002, ...) with no names or emails.
- Keep the database and exports on the project's own machine or server; delete them at the end of the project.
- Follow the principles of India's Digital Personal Data Protection Act, 2023: purpose limitation, informed consent and data minimisation.

## 9. Threats to validity, stated in the report

- A small sample and a short duration (low power; novelty effects).
- No blinding: students may notice the reason texts. The two arms see the same UI otherwise.
- Students may talk to each other across arms (contamination).
- The tests cover four concepts only.
- One course and one institution (generalisability).
