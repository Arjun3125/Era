"""Export ERA memory and learning state to an Obsidian vault as Markdown notes."""
from __future__ import annotations

import json
import os
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


_DEFAULT_VAULT = os.environ.get("ERA_OBSIDIAN_VAULT", "")
_NOTE_ROOT = "ERA"  # subfolder inside the vault


# ── helpers ───────────────────────────────────────────────────────────────────

def _vault_path(vault: str) -> Path:
    p = Path(vault) / _NOTE_ROOT
    p.mkdir(parents=True, exist_ok=True)
    return p


def _subdir(vault: str, name: str) -> Path:
    p = Path(vault) / _NOTE_ROOT / name
    p.mkdir(parents=True, exist_ok=True)
    return p


def _write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def _frontmatter(**fields) -> str:
    lines = ["---"]
    for k, v in fields.items():
        if isinstance(v, list):
            lines.append(f"{k}:")
            for item in v:
                lines.append(f"  - {item}")
        else:
            lines.append(f"{k}: {v!r}")
    lines.append("---")
    return "\n".join(lines)


def _ts_label(ts: Optional[str]) -> str:
    if not ts:
        return "unknown"
    try:
        dt = datetime.fromisoformat(ts)
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return ts[:16]


# ── episode notes ─────────────────────────────────────────────────────────────

def _export_episodes(vault: str, episodes_path: str) -> int:
    ep_dir = _subdir(vault, "Episodes")
    if not Path(episodes_path).exists():
        return 0
    count = 0
    try:
        with open(episodes_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    ep = json.loads(line)
                except json.JSONDecodeError:
                    continue

                turn = ep.get("turn_id", 0)
                domain = ep.get("domain", "general")
                outcome = ep.get("outcome") or "pending"
                regret = ep.get("regret_score", 0.0)
                ts = _ts_label(ep.get("timestamp"))
                ep_id = ep.get("episode_id", f"turn_{turn}")

                fm = _frontmatter(
                    type="era-episode",
                    turn=turn,
                    domain=domain,
                    outcome=outcome,
                    regret=regret,
                    date=ts,
                    tags=["era", "episode", domain, outcome],
                )

                body = [
                    fm,
                    f"# Episode {ep_id} — Turn {turn}",
                    f"",
                    f"**Domain:** [[{domain}]]  ",
                    f"**Outcome:** `{outcome}`  ",
                    f"**Regret:** {regret:.2f}  ",
                    f"**Date:** {ts}",
                    f"",
                    f"## User Input",
                    f"> {ep.get('user_input', '')}",
                    f"",
                    f"## Recommendation",
                    f"> {ep.get('persona_recommendation', '')}",
                    f"",
                    f"## Council",
                    f"- Stance: `{ep.get('minister_stance', 'unknown')}`",
                    f"- Recommendation: `{ep.get('council_recommendation', 'unknown')}`",
                    f"- Confidence: {ep.get('confidence', 0):.0%}",
                ]

                lesson = ep.get("lesson_learned")
                if lesson:
                    body += ["", f"## Lesson Learned", f"> {lesson}"]

                chains = ep.get("consequence_chain") or []
                if chains:
                    body += ["", "## Consequence Chain"]
                    for c in chains:
                        body.append(f"- Turn {c[0]}: `{c[2]}` in `{c[1]}` (magnitude {c[3]:.2f})")

                note_path = ep_dir / f"turn_{turn:04d}_{domain}.md"
                _write(note_path, "\n".join(body))
                count += 1
    except Exception as exc:
        pass
    return count


# ── user profile notes ────────────────────────────────────────────────────────

def _export_profiles(vault: str, profiles_dir: str) -> int:
    prof_dir = _subdir(vault, "Profiles")
    profiles_root = Path(profiles_dir)
    if not profiles_root.exists():
        return 0
    count = 0
    for f in profiles_root.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            uid = data.get("user_id", f.stem)
            themes = data.get("recurring_themes", {})
            top_themes = sorted(themes.items(), key=lambda x: -x[1])[:5]

            fm = _frontmatter(
                type="era-profile",
                user_id=uid,
                total_turns=data.get("total_turns", 0),
                risk_tolerance=data.get("risk_tolerance", "unknown"),
                last_active=_ts_label(data.get("last_active")),
                tags=["era", "profile"],
            )

            body = [
                fm,
                f"# User Profile — {uid}",
                f"",
                f"| Field | Value |",
                f"|-------|-------|",
                f"| Risk Tolerance | `{data.get('risk_tolerance', 'unknown')}` |",
                f"| Total Turns | {data.get('total_turns', 0)} |",
                f"| Success Rate | {data.get('success_rate', 0):.0%} |",
                f"| Last Active | {_ts_label(data.get('last_active'))} |",
                f"",
                f"## Top Themes",
            ]
            for theme, cnt in top_themes:
                body.append(f"- [[{theme}]] × {cnt}")

            _write(prof_dir / f"{uid}.md", "\n".join(body))
            count += 1
        except Exception:
            pass
    return count


# ── failure clusters note ─────────────────────────────────────────────────────

def _export_failure_clusters(vault: str, episodes_path: str) -> None:
    try:
        from persona.learning.episodic_memory import EpisodicMemory
        mem = EpisodicMemory(storage_path=episodes_path)
        clusters = mem.detect_failure_clusters()
    except Exception:
        return

    learn_dir = _subdir(vault, "Learning")
    lines = [
        _frontmatter(type="era-failures", tags=["era", "learning", "failures"]),
        "# Failure Clusters",
        "",
        f"*Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*",
        "",
    ]
    if not clusters:
        lines.append("No failure clusters detected yet.")
    else:
        for key, eps in sorted(clusters.items(), key=lambda x: -len(x[1])):
            lines += [
                f"## {key.replace('_', ' ').title()} ({len(eps)} failures)",
                "",
            ]
            for ep in eps[:5]:
                lines.append(
                    f"- [[turn_{ep.turn_id:04d}_{ep.domain}|Turn {ep.turn_id}]]: "
                    f"regret={ep.regret_score:.2f}"
                )
            if len(eps) > 5:
                lines.append(f"- … and {len(eps)-5} more")
            lines.append("")

    _write(learn_dir / "failure_clusters.md", "\n".join(lines))


# ── knowledge gaps note ───────────────────────────────────────────────────────

def _export_knowledge_gaps(vault: str, gaps: List[str]) -> None:
    learn_dir = _subdir(vault, "Learning")
    lines = [
        _frontmatter(type="era-knowledge-gaps", tags=["era", "learning", "gaps"]),
        "# Knowledge Gaps",
        "",
        f"*Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*",
        "",
        "Domains with fewer than 5 knowledge entries — consider ingesting PDFs to fill these.",
        "",
    ]
    if not gaps:
        lines.append("No knowledge gaps detected.")
    else:
        for g in gaps:
            lines.append(f"- [ ] [[{g}]] — sparse knowledge base")
    _write(learn_dir / "knowledge_gaps.md", "\n".join(lines))


# ── minister confidence note ──────────────────────────────────────────────────

def _export_minister_confidence(vault: str, confidence_path: str) -> None:
    learn_dir = _subdir(vault, "Learning")
    conf_file = Path(confidence_path)
    lines = [
        _frontmatter(type="era-minister-confidence", tags=["era", "learning", "ministers"]),
        "# Minister Confidence Weights",
        "",
        f"*Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*",
        "",
        "Bayesian weights per minister × domain. >1.0 = above prior, <1.0 = below prior.",
        "",
        "| Minister | Domain | Successes | Failures | Weight |",
        "|----------|--------|-----------|----------|--------|",
    ]
    if conf_file.exists():
        try:
            data = json.loads(conf_file.read_text(encoding="utf-8"))
            try:
                from persona.learning.minister_confidence import MinisterConfidenceTracker
                tracker = MinisterConfidenceTracker(storage_path=str(conf_file))
            except Exception:
                tracker = None

            for key, rec in sorted(data.items()):
                minister, domain = key.split("::", 1)
                succ = rec.get("successes", 0)
                fail = rec.get("failures", 0)
                weight = tracker.get_weight(minister, domain) if tracker else "?"
                w_str = f"{weight:.3f}" if isinstance(weight, float) else str(weight)
                lines.append(f"| {minister} | {domain} | {succ:.0f} | {fail:.0f} | {w_str} |")
        except Exception:
            lines.append("| (error reading confidence data) | | | | |")
    else:
        lines.append("| (no data yet — submit feedback to build history) | | | | |")

    _write(learn_dir / "minister_confidence.md", "\n".join(lines))


# ── dashboard ─────────────────────────────────────────────────────────────────

def _export_dashboard(vault: str, stats: Dict[str, Any]) -> None:
    root = _vault_path(vault)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        _frontmatter(type="era-dashboard", tags=["era", "dashboard"]),
        "# ERA Memory Dashboard",
        "",
        f"*Last export: {ts}*",
        "",
        "## Session Stats",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total Episodes | {stats.get('episodes', 0)} |",
        f"| Profiles | {stats.get('profiles', 0)} |",
        f"| Failure Clusters | {stats.get('clusters', 0)} |",
        f"| Knowledge Gaps | {stats.get('gaps', 0)} |",
        "",
        "## Navigation",
        "",
        "- [[ERA/Learning/failure_clusters|Failure Clusters]]",
        "- [[ERA/Learning/knowledge_gaps|Knowledge Gaps]]",
        "- [[ERA/Learning/minister_confidence|Minister Confidence]]",
        "",
        "## Recent Episodes",
        "",
        "```dataview",
        "TABLE turn, domain, outcome, regret FROM \"ERA/Episodes\"",
        "SORT turn DESC",
        "LIMIT 20",
        "```",
        "",
        "## Failure Rate by Domain",
        "",
        "```dataview",
        "TABLE length(rows) AS failures FROM \"ERA/Episodes\"",
        "WHERE outcome = \"failure\"",
        "GROUP BY domain",
        "SORT length(rows) DESC",
        "```",
    ]
    _write(root / "ERA_Dashboard.md", "\n".join(lines))


# ── public API ────────────────────────────────────────────────────────────────

def export_to_obsidian(
    vault_path: Optional[str] = None,
    episodes_path: str = "data/memory/episodes.jsonl",
    profiles_dir: str = "data/user_profiles",
    confidence_path: str = "data/memory/minister_confidence.json",
    knowledge_gaps: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Export all ERA memory to Obsidian vault as Markdown notes.

    Returns a dict with counts of what was exported.
    """
    vault = vault_path or _DEFAULT_VAULT
    if not vault:
        raise ValueError(
            "No Obsidian vault path. Set ERA_OBSIDIAN_VAULT env var or pass vault_path."
        )

    ep_count = _export_episodes(vault, episodes_path)
    pr_count = _export_profiles(vault, profiles_dir)
    _export_failure_clusters(vault, episodes_path)
    _export_knowledge_gaps(vault, knowledge_gaps or [])
    _export_minister_confidence(vault, confidence_path)

    # Count failure clusters for dashboard
    try:
        from persona.learning.episodic_memory import EpisodicMemory
        mem = EpisodicMemory(storage_path=episodes_path)
        cluster_count = len(mem.detect_failure_clusters())
    except Exception:
        cluster_count = 0

    stats = {
        "episodes": ep_count,
        "profiles": pr_count,
        "clusters": cluster_count,
        "gaps": len(knowledge_gaps or []),
    }
    _export_dashboard(vault, stats)

    return {
        "vault": vault,
        "exported": stats,
        "notes_root": str(Path(vault) / _NOTE_ROOT),
    }
