# Code Coffee — extracted cache (low-memory)

Compact **digests** of each Code Coffee deck so we never re-OCR the 8–19 MB PDFs
and keep token/memory use low. The HARVEST step reads and appends here instead of
re-fetching Drive every time.

- **`extracts.jsonl`** — one JSON object per deck, newline-delimited, append-only.
- Raw decks stay in Google Drive (folder IDs in `../../config/sources.md`). We
  cache only the slim digest, never the full OCR dump.

## Record shape

```json
{
  "date": "YYYY-MM-DD",
  "file_id": "<drive id>",
  "title": "Code Coffee, <date>",
  "safe":  ["short fact nuggets cleared for use"],
  "people": ["names mentioned — must pass roster check before any use"],
  "hold_clients": ["client/project facts — need leadership sign-off"],
  "omit": ["comp / HR specifics deliberately dropped"]
}
```

`safe` feeds candidate facts. `people` triggers the roster check. `hold_clients`
goes to the leadership-signoff queue. `omit` is logged so we know what we skipped.
