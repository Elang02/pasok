# Branch `history` — the 76 commits this repo was rebuilt from

`main` is the cleaned repo. It carries the same tree but starts from one commit, so
it reads as a deliberate build rather than 76 rounds of patching.

`history` is the original repository's commit line, imported whole so the record of
what was decided, broken and fixed is not thrown away. Use it to answer "why is this
written this way", never to diff against `main` for review: the trees diverged, so a
diff shows the whole rebuild, not a change.

To find when something was introduced:

```bash
git log history --oneline -- <path>
git log history -S<string> --oneline
```

Two things worth reading first:

- the phase records explain why the event calendar was wrong for a year, and the
  registry fix that followed
- the earlier WAPE figures (0.1276, 0.2811) were corrected later; `history` shows
  when and what the correction was, `main` only holds the answer
