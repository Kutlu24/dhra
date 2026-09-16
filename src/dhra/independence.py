"""Independence testing and descent clustering -- DHRA_BUILD_SPEC.md
section 7.3, the hardest and most important component of the epistemic
engine. Eleven provincial newspapers printing the same wire dispatch are
one witness, not eleven -- corroboration (E2) is the level most easily
awarded in error, and this module is what stands between "similar" and
"actually independent".

Pipeline (section 7.3): shingle similarity (recall-oriented candidate
generation) -> pairwise alignment -> descent signal extraction -> cluster
formation -> verdict.

Deviation from spec section 16 ("datasketch MinHash for candidate
generation"): this implements exact Jaccard similarity over word
3-shingles instead of MinHash. At the corpus sizes a single researcher
works with interactively, MinHash's approximation is solving a problem
(sketch a huge set cheaply) this project doesn't have yet; exact Jaccard
is simpler, exactly reproducible, and adding `datasketch` as a
dependency for no accuracy gain at this scale would be premature. Revisit
if/when candidate-generation cost actually matters (see OPEN_QUESTIONS.md).
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from enum import StrEnum

# Minimal reference lexicon -- section 7.3 signal 1 needs "rare or absent
# from a reference lexicon" as one condition for a shared-error signal.
# This is a small, hand-written common-word list, not a real dictionary;
# good enough to separate "the/was/signed" from a garbled proper noun in
# a fixture, not production-grade. See OPEN_QUESTIONS.md.
COMMON_WORDS = frozenset(
    """
    a an the this that these those of in on at to for from with by as is
    was were are be been being it its he she they them his her their our
    we you your i and or but not no so if then than there here when
    where who whom which what how all any both each few more most other
    some such only own same just also very into over under again further
    once about above below out off down up will would can could shall
    should may might must did do does done has have had having said says
    say told tell reported report according account event place year
    month day time man woman city town village district province
    """.split()
)

TOKEN_RE = re.compile(r"[^\W\d_]+", re.UNICODE)


class IndependenceVerdict(StrEnum):
    INDEPENDENT = "independent"
    SHARED_DESCENT = "shared_descent"
    UNDETERMINED = "undetermined"


@dataclass(frozen=True)
class DescentSignal:
    kind: str  # "shared_error" | "shared_phrasing"
    detail: str
    strength: int  # higher = stronger evidence, section 7.3's descending order


@dataclass(frozen=True)
class PairVerdict:
    a: str
    b: str
    verdict: IndependenceVerdict
    similarity: float
    signals: tuple[DescentSignal, ...]


@dataclass(frozen=True)
class DescentCluster:
    members: tuple[str, ...]  # ids (e.g. item_id), all sharing descent
    representative: str
    signals: tuple[DescentSignal, ...]


def _shingles(text: str, n: int = 3) -> set[str]:
    tokens = [t.lower() for t in TOKEN_RE.findall(text)]
    if len(tokens) < n:
        return {" ".join(tokens)} if tokens else set()
    return {" ".join(tokens[i : i + n]) for i in range(len(tokens) - n + 1)}


def jaccard(text_a: str, text_b: str) -> float:
    sa, sb = _shingles(text_a), _shingles(text_b)
    if not sa and not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def _find_shared_error(text_a: str, text_b: str, outside_texts: list[str]) -> DescentSignal | None:
    """Signal 1 (strongest, section 7.3): tokens that are (a) rare/absent
    from the reference lexicon, (b) identical across the pair, (c) at
    positions where texts outside the group differ (or the token is
    simply absent from every outside text)."""
    tokens_a = [t.lower() for t in TOKEN_RE.findall(text_a)]
    tokens_b = set(t.lower() for t in TOKEN_RE.findall(text_b))
    outside_tokens: set[str] = set()
    for t in outside_texts:
        outside_tokens |= set(x.lower() for x in TOKEN_RE.findall(t))

    for token in tokens_a:
        if len(token) < 4 or token in COMMON_WORDS:
            continue
        if token in tokens_b and token not in outside_tokens:
            return DescentSignal(
                kind="shared_error",
                detail=f"shared rare token {token!r}, absent from every text outside this pair",
                strength=5,
            )
    return None


def _find_shared_phrasing(text_a: str, text_b: str) -> DescentSignal | None:
    """Signal 2: rare n-grams (long matching blocks) shared beyond chance."""
    matcher = difflib.SequenceMatcher(a=text_a.lower(), b=text_b.lower())
    ratio = matcher.ratio()
    if ratio >= 0.6:
        longest = max(matcher.get_matching_blocks(), key=lambda m: m.size, default=None)
        detail = f"overall alignment ratio {ratio:.2f}"
        if longest and longest.size > 20:
            detail += f"; longest shared run: {text_a[longest.a: longest.a + longest.size]!r}"
        return DescentSignal(kind="shared_phrasing", detail=detail, strength=3)
    return None


def check_pair(id_a: str, text_a: str, id_b: str, text_b: str, outside_texts: list[str], *, recall_threshold: float = 0.08) -> PairVerdict:
    """`outside_texts` should be every OTHER candidate group's texts --
    section 7.3 signal 1 needs the shared token absent from texts
    "outside the group", not merely outside this one pair (a token
    every member of an 11-way reprint family shares is not "outside"
    any single pair within that family). `cluster_by_descent` supplies
    group-level outside texts; a caller checking one isolated pair with
    no broader group should pass `[]` and rely on shared_phrasing alone,
    or accept that shared_error can only be confirmed within a group."""
    similarity = jaccard(text_a, text_b)
    if similarity < recall_threshold:
        return PairVerdict(a=id_a, b=id_b, verdict=IndependenceVerdict.INDEPENDENT, similarity=similarity, signals=())

    signals = []
    shared_error = _find_shared_error(text_a, text_b, outside_texts)
    if shared_error:
        signals.append(shared_error)
    shared_phrasing = _find_shared_phrasing(text_a, text_b)
    if shared_phrasing:
        signals.append(shared_phrasing)

    if signals:
        return PairVerdict(a=id_a, b=id_b, verdict=IndependenceVerdict.SHARED_DESCENT, similarity=similarity, signals=tuple(signals))
    # Passed the recall filter (plausibly related) but no descent signal
    # confirmed it -- default conservative (section 7.3): never an
    # optimistic verdict either way, so UNDETERMINED, not INDEPENDENT.
    return PairVerdict(a=id_a, b=id_b, verdict=IndependenceVerdict.UNDETERMINED, similarity=similarity, signals=())


def _union_find_groups(ids: list[str], pairs_to_union: list[tuple[str, str]]) -> dict[str, list[str]]:
    parent = {i: i for i in ids}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in pairs_to_union:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    groups: dict[str, list[str]] = {}
    for i in ids:
        groups.setdefault(find(i), []).append(i)
    return groups


def cluster_by_descent(candidates: list[tuple[str, str]], *, recall_threshold: float = 0.08) -> tuple[list[DescentCluster], list[PairVerdict]]:
    """candidates: [(id, text), ...]. Two phases per the spec's pipeline
    (section 7.3): (1) recall-oriented shingle similarity forms broad
    candidate groups -- cheap, deliberately permissive; (2) within each
    group, descent signals are extracted with "outside the group" as the
    reference set (not "outside this one pair"), so a token every member
    of an 11-way reprint family shares still counts as absent from
    outside -- then only the pairs actually carrying a signal are merged
    into the final descent cluster. Returns the final clusters plus
    every pairwise verdict computed, for display (section 7.3: "surface
    it explicitly in the output")."""
    ids = [c[0] for c in candidates]
    texts = {c[0]: c[1] for c in candidates}

    recall_pairs = [
        (ids[i], ids[j])
        for i in range(len(ids))
        for j in range(i + 1, len(ids))
        if jaccard(texts[ids[i]], texts[ids[j]]) >= recall_threshold
    ]
    candidate_groups = _union_find_groups(ids, recall_pairs)

    all_verdicts: list[PairVerdict] = []
    descent_pairs: list[tuple[str, str]] = []
    cluster_signals: dict[str, list[DescentSignal]] = {}

    for group_ids in candidate_groups.values():
        if len(group_ids) < 2:
            continue
        group_set = set(group_ids)
        outside_texts = [texts[i] for i in ids if i not in group_set]
        for i in range(len(group_ids)):
            for j in range(i + 1, len(group_ids)):
                id_a, id_b = group_ids[i], group_ids[j]
                verdict = check_pair(id_a, texts[id_a], id_b, texts[id_b], outside_texts, recall_threshold=recall_threshold)
                all_verdicts.append(verdict)
                if verdict.verdict == IndependenceVerdict.SHARED_DESCENT:
                    descent_pairs.append((id_a, id_b))

    # Pairs that never even reached the recall threshold with anyone are
    # not "checked" above; record them as INDEPENDENT explicitly so
    # every candidate pair has a verdict.
    checked = {(v.a, v.b) for v in all_verdicts} | {(v.b, v.a) for v in all_verdicts}
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            id_a, id_b = ids[i], ids[j]
            if (id_a, id_b) not in checked:
                all_verdicts.append(
                    PairVerdict(a=id_a, b=id_b, verdict=IndependenceVerdict.INDEPENDENT, similarity=jaccard(texts[id_a], texts[id_b]), signals=())
                )

    final_groups = _union_find_groups(ids, descent_pairs)
    for root, members in final_groups.items():
        if len(members) <= 1:
            continue
        member_set = set(members)
        signals: list[DescentSignal] = []
        for v in all_verdicts:
            if v.a in member_set and v.b in member_set:
                for s in v.signals:
                    if s not in signals:
                        signals.append(s)
        cluster_signals[root] = signals

    clusters = [
        DescentCluster(
            members=tuple(sorted(members)),
            representative=sorted(members)[0],
            signals=tuple(cluster_signals.get(root, [])),
        )
        for root, members in final_groups.items()
        if len(members) > 1
    ]
    return clusters, all_verdicts


def dedupe_by_descent(locators: list, clusters: list[DescentCluster]):
    """Given supporting locators for a claim and the descent clusters
    found among their item ids, keep only the representative locator per
    cluster (plus every locator whose item wasn't clustered at all) --
    this is the "37 passages, 11 share a descent, count as one" collapse
    (section 18)."""
    member_to_root: dict[str, str] = {}
    for cluster in clusters:
        for member in cluster.members:
            member_to_root[member] = cluster.representative

    seen_roots: set[str] = set()
    kept = []
    for loc in locators:
        root = member_to_root.get(loc.item_id)
        if root is None:
            kept.append(loc)
            continue
        if root not in seen_roots:
            seen_roots.add(root)
            kept.append(loc)
    return kept
