"""A tiny but complete content pack for API tests: 3 concepts (a -> b -> c), study concept b."""

import json
from pathlib import Path

STYLES = {
    "notes": [-0.5, 0.0, -0.8, 0.6],
    "video": [-0.3, 0.0, 0.6, 0.5],
    "practice": [0.9, 0.6, -0.3, 0.3],
    "concept_map": [-0.2, -0.5, 0.8, -0.8],
    "worked_example": [0.1, 0.8, -0.2, 0.8],
}


def make_minipack(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "concepts").mkdir(exist_ok=True)
    (root / "aids").mkdir(exist_ok=True)
    slugs = ["alpha", "beta", "gamma"]
    (root / "course.json").write_text(json.dumps({
        "code": "MINI", "title": "Mini course", "description": "Test course",
        "concepts_in_syllabus_order": slugs, "study_concepts": ["beta"],
    }))
    for i, slug in enumerate(slugs):
        aids, questions = [], []
        for order, t in enumerate(["notes", "worked_example", "video", "concept_map", "practice"], start=1):
            aid = {"slug": f"{slug}-{t.replace('_', '-')}", "title": f"{slug} {t}", "type": t,
                   "description": f"{t} for {slug}", "difficulty": 2 + (order % 2), "duration": 5, "order": order,
                   "style": STYLES[t]}
            if t == "video":
                aid.update(delivery="external_url", url=f"https://example.com/{slug}")
            else:
                aid.update(delivery="native_md", body=f"{slug}-{t}.md")
                (root / "aids" / f"{slug}-{t}.md").write_text(f"# {slug} {t}\n\n" + "Some useful text. " * 20)
            aids.append(aid)

        def q(key, pool, n, questions=questions, slug=slug, **kw):
            questions.append({"key": key, "pool": pool, "stem": f"{slug} question {key}?",
                              "options": [f"{key} opt {j}" for j in range(4)], "answer": n % 4,
                              "explanation": "Because.", "difficulty": 2, **kw})

        q(f"{slug}-d01", "diagnostic", 0)
        for n in range(1, 11):
            q(f"{slug}-c{n:02d}", "check", n)
        for n in range(1, 6):
            q(f"{slug}-p{n:02d}", "drill", n, aid=f"{slug}-practice")
        if slug == "beta":
            for form in "AB":
                for n in range(1, 6):
                    q(f"{slug}-{form.lower()}{n:02d}", "study", n, form=form)
        (root / "concepts" / f"{slug}.json").write_text(json.dumps({
            "slug": slug, "name": slug.title(), "description": f"The {slug} concept",
            "prerequisites": [slugs[i - 1]] if i else [], "aids": aids, "questions": questions,
        }))
    items = [{"key": f"q{n:02d}", "dim": ["ar", "si", "vv", "sg"][(n - 1) // 5], "a_pole": 1 if n % 2 else -1,
              "prompt": f"Prompt {n}", "a": "A", "b": "B"} for n in range(1, 21)]
    (root / "questionnaire.json").write_text(json.dumps({"version": "test", "items": items}))
    (root / "sus.json").write_text(json.dumps({"items": [f"Item {n}" for n in range(1, 11)]}))
    return root
