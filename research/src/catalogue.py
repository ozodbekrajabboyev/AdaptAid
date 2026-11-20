"""Build the engine's Catalogue from the real content pack (content/dsa), for simulations."""

from __future__ import annotations

from app.content_pack import DEFAULT_PACK, load_pack
from engine.bkt import BKTParams
from engine.types import AidInfo, Catalogue


def dsa_catalogue(params: BKTParams | None = None) -> Catalogue:
    pack = load_pack(DEFAULT_PACK)
    cid = {c.slug: i + 1 for i, c in enumerate(pack.concepts)}
    aids = {}
    for j, a in enumerate(pack.aids, start=1):
        aids[j] = AidInfo(id=j, concept_id=cid[a.concept], aid_type=a.type, style=tuple(a.style),  # type: ignore[arg-type]
                          difficulty=a.difficulty, default_order=a.order, title=a.title)
    return Catalogue(
        syllabus=[cid[c.slug] for c in pack.concepts],
        prereqs={cid[c.slug]: {cid[p] for p in c.prerequisites} for c in pack.concepts},
        aids=aids,
        names={cid[c.slug]: c.name for c in pack.concepts},
        params={cid[c.slug]: params or BKTParams() for c in pack.concepts},
    )
