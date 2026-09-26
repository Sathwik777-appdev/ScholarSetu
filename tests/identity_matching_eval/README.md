# Identity matching evaluation set

`pairs.csv` holds labelled name pairs for the Identity Resolver
(`services/core/app/verification/identity_resolver.py`). Run it with:

```bash
pytest tests/identity_matching_eval -s
```

The test prints a confusion matrix (expected vs actual decision) and every miss. It **fails** if
any row marked `hard_negative=yes` (two different people) is `AUTO_VERIFY`, or if exact agreement
drops below 90%.

## Adding real cases

Real variants from Aadhaar, school, caste-certificate and bank records are the most useful rows.
Add a line per pair:

| Column | Meaning |
|---|---|
| `category` | e.g. `spelling_variant`, `transliteration`, `initials`, `twins_siblings`, `namesake` |
| `hard_negative` | `yes` if the two records are different people |
| `name_a`, `name_b` | the names exactly as written on each record (any script) |
| `dob_*`, `father_*`, `district_*` | leave blank if that record does not carry the field |
| `expected_decision` | what a careful officer would want: `AUTO_VERIFY`, `PROVISIONAL` or `MANUAL_REVIEW` |

Label the **correct** decision, not what the resolver currently returns. A miss in the matrix is
useful information; relabelling rows to make the test pass hides it.

Decision rules (thresholds in `app/config.py`):

- `AUTO_VERIFY`: name score ≥ 0.92, at least one corroborating field matches exactly, none conflicts.
- `PROVISIONAL`: name score 0.75–0.92, or ≥ 0.92 with nothing to corroborate.
- `MANUAL_REVIEW`: below 0.75, any conflicting field, a different name part, or an unsupported script.
