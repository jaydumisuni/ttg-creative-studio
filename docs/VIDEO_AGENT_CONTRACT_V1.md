# Creative Studio Video Agent Contract V1

Creative Studio owns video editing, timeline rendering, asset authority and
capability declarations. **Hunter, ChatGPT or another authorized AI** is a
client of the same stable tools, not a second video engine.

This extends the pre-existing `src/ttg_creative_studio/cli.py` Hunter job
runner. It does not create an always-on HTTP listener or a Ptah dependency.

## Discovery

```bash
python -B src/ttg_creative_studio/cli.py --catalog
```

The JSON includes operation IDs, required inputs and side effects. An AI
tool adapter can expose those operations as tool/function definitions, while
the local, approved executor actually launches the job runner. Merely
providing a text assistant access to this document does not give it
permission to read machine files or run a process.

## Example workflow for any authorized AI

1. **Discover** `video_capabilities`. It reports actual FFmpeg/ffprobe
   availability. Video-generation backend admission is separate.
2. **Understand** `video_info` or `video_understand`. The first returns
   observed stream metadata, duration, audio-stream count and source SHA256.
   The second samples three real frames and measures pixels. With a
   separately installed, explicit local vision-language model it can also
   describe observed objects and scenes. Without that model it never
   fabricates semantic objects.
3. **Plan** `video_plan` with authored scene descriptions and bounded
   durations. It saves a reviewable storyboard JSON with timestamps. A
   storyboard is not an executed video.
4. **Make and edit** through Creative Studio's existing native `.ttgstudio`
   layer/timeline model. `video_render` converts a real motion project to
   MP4 via the existing renderer and FFmpeg, with source/output checks.
5. **Generative video** is an optional specialist provider. FreeVideo is a
   candidate. It is not installed or qualified by this contract. No local
   heavyweight weights are downloaded to run steps 1–4. After approval,
   a provider adapter can return a verified video artifact for import as
   an editable Studio video/timeline asset.
6. **Review and deliver**: the user or a release policy approves creative
   results, publishing and external sharing. A tool's `done` result alone
   is not customer delivery authorization.

### Sample job: storyboard

```json
{
  "jobId": "video_plan_001",
  "task": "video_plan",
  "output": "D:/creative/plan.json",
  "options": {
    "fps": 24,
    "scenes": [
      {"description": "Product beauty shot on a clean table", "seconds": 2.5},
      {"description": "Close-up of the interface", "seconds": 1.5}
    ]
  }
}
```

### Sample job: measured understanding

```json
{
  "jobId": "video_understand_001",
  "task": "video_understand",
  "input": "D:/creative/source.mp4",
  "output": "D:/creative/source-analysis.json",
  "options": {}
}
```

For optional semantic understanding use:
`"vision_model": "the-id-advertised-by-your-local-server"` and
`"vision_endpoint": "http://127.0.0.1:8000"`. This requires a real
loopback model service; Creative Studio does not install it automatically.

### Sample job: real native rendering

```json
{
  "jobId": "video_render_001",
  "task": "video_render",
  "input": "D:/creative/edited.ttgstudio.json",
  "output": "D:/creative/final.mp4",
  "options": {}
}
```

Run one with:

```bash
python -B src/ttg_creative_studio/cli.py --job job.json --result result.json
```

Successful results include `ok`, `jobId`, `task`, `status`, `meta`,
actual output path, and source details. Failure is a nonzero process exit
and structured error response. Existing image jobs continue unchanged.

## Security and execution constraints

- The AI assistant must be admitted to a **specific approved local executor
  and filesystem scope**. A JSON job alone does not bypass OS/Oracle policy.
- Source media never gets overwritten. Output paths must exist in an
  authorized directory and must not already exist. Jobs cannot arbitrarily
  select a shell command or download models.
- ffprobe/FFmpeg are invoked as bounded subprocess argument arrays, not via
  a shell. The analysis input is capped at 2 GiB, measured video duration at
  30 minutes, decoded pixel count at 16 million, sampled frames at three,
  and storyboard count at twelve.
- The vision interface requires a real local service and rejects redirects;
  its text is recorded as model-supplied, not confirmed fact. Pixel
  measurements remain directly checkable.
- `video_generate` is *not admitted*. Never replace missing FreeVideo
  inference with prerecorded clips while asserting AI-generation success.
- Human/release policy approval remains mandatory for external delivery.
  Creative Studio stays independently usable without Hunter or ChatGPT.

## Future FreeVideo provider

A small adapter should discover the installed FreeVideo backend, check
model availability/licensing and disk quotas, submit a bounded video job,
poll its actual job state, and verify the generated MP4 before import.
Provider-specific weights, VRAM offload settings and model updates stay in
that optional provider; Creative Studio retains ownership of projects,
storyboards, video understanding and final exports.

This separation means Hunter can **learn the shared tool language**, while
Creative Studio remains the canonical source of creative capabilities.
