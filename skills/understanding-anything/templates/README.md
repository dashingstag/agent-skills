# understanding-X

Notes from a long, slow attempt to understand <DOMAIN> well enough to
eventually follow <NORTH STAR>.

> **North star.** <One paragraph: the goal — a proof, a system, a book —
> and what "understanding it" means. Link to status references, never copy
> them.>

This is a learning journal, not a textbook and not a claim about the
subject. Anything here may be wrong until it is marked as verified (see
[Understanding levels](#understanding-levels)).

---

## Method: teardown, not survey

Each high-level concept gets **torn down** into smaller concepts until every
leaf is actually understandable. The rule:

**A concept is only understood once every one of its children is
understood, and every claim in it points to a source.**

---

## Understanding levels

Every concept carries one of these (front matter + the level chip).

| Level | Name | Meaning |
|---|---|---|
| 0 | Unseen | Only a name on the map |
| 1 | Content | The page/playback exists — content has been written |
| 2 | Recognised | I can state it in my own words |
| 3 | Followed | I have read a proof and could follow each step with the source open |
| 4 | Reproduced | I can prove it, or work an example, without notes |
| 5 | Connected | I can explain why it is needed upstream and where it breaks if a hypothesis is removed |

Level 1 is the content flag, set by whoever writes the page. Levels 2-5 are
the owner's: set with the level chip in the header, saved to
`progress/levels.json` — gitignored, so progress never commits.

---

## Map

The concept tree lives in `map.json`, best viewed in `site/index.html`.
`parents` lists the concepts that need this one; children are derived.
A concept needed by several parents stays at `concepts/<id>/`; only a
single-parent concept may nest.

After any change run:

```
python tools/build.py
```

---

## File structure

See `AGENTS.md` — it documents the layout, the kit every playback ships,
and every rule the build enforces.

## Ground rules

- Cite everything. A claim without a source or a computation is an open question.
- Link to outside material instead of copying it.
- Keep the difference clear between "this is true", "the source says this"
  and "I think this".
- It is fine for this to take years.
