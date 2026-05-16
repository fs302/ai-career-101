# Benchmark Future Plan

## Current Baseline

- Snapshot: `benchmark/snapshots/minimax_m2_7_50_cases_2026_05_16.json`
- Model: `MiniMax-M2.7`
- Scope: 10 roles x 5 cases, heuristic scoring only, no LLM judge.
- Main finding: mentor-style structure is usable, but tool execution is still too shallow. Tool-dependent roles score lower once `required_tools` is no longer treated as automatically used.

## Next Milestones

### 1. Real Tool Execution Cases

Convert tool-dependent benchmark cases from text-only prompts into executable workflows:

- `vision.describe`: attach representative images for interior design, nutrition, ophthalmology.
- `image.generate`: require generated image artifact path, prompt, aspect ratio, and review notes.
- `translation.zh_en`: require translated text artifact and terminology notes.
- `speech.tts`: require audio URL/path plus translated script.

Scoring should distinguish:

- tool unavailable
- tool mentioned but not executed
- tool executed but artifact unusable
- tool executed and artifact supports the answer

### 2. Artifact Validators

Add validators for common deliverables:

- SRT validator: timecode format, line length, reading speed, empty subtitle checks.
- Image artifact validator: file exists, dimensions, non-empty pixels, prompt metadata.
- Audio artifact validator: file exists, duration, non-zero bytes, transcript alignment.
- Planning artifact validator: required sections, KPI fields, risk fields, next-step fields.

### 3. Role-Specific Rubrics

Move from generic dimensions to role-specific rubrics:

- Medical-adjacent roles: safety boundary and referral quality get higher weight.
- Visual roles: artifact quality, prompt control, originality, and production constraints.
- Translation roles: meaning preservation, compression, uncertainty handling, terminology consistency.
- Business roles: hypothesis quality, metric design, data boundary, operational next steps.

### 4. Snapshot Lifecycle

Benchmark should be run offline or on a schedule, not manually from the UI.

- Keep `/benchmark` as a read-only dashboard.
- Store approved snapshots under `benchmark/snapshots/`.
- Store raw local runs under `data/benchmark_runs/`, ignored by git.
- Promote a local run into `benchmark/snapshots/` only after manual review.

### 5. MiniMax First, Multi-Model Later

Keep the next few iterations MiniMax-only until case quality and tool validation are strong enough. After that, restore a controlled matrix:

- `MiniMax-M2.7`
- `GLM-5.1`
- `qwen3.5-27b`
- `deepseek-v3.2`

Multi-model runs should use the same artifact validators, otherwise model comparisons will be noisy.

### 6. Better Failure Reporting

Expose case-level failures in the Benchmark page:

- lowest case per role
- failed tool calls
- missing artifact reason
- main rubric dimension dragging down the score
- recommended fix linked to role config or tool implementation

## Implementation Order

1. Add benchmark attachment fixtures.
2. Add artifact validators and persist validation output in `case_results`.
3. Update `WorkflowEngine` so benchmark cases can explicitly execute workflow tools without relying on chat uploads.
4. Add a snapshot promotion script.
5. Expand the Benchmark page from role summary to role detail drill-down.
