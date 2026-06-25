# Hunter Creative Engine V1

TTG Creative Studio is both a human desktop creative app and a Hunter-callable creative engine.

This first engine layer gives Hunter a safe CLI/job-runner interface without forcing the human PyQt app to open.

## Current job runner

Entry:

```powershell
python .\src\ttg_creative_studio\cli.py --job .\examples\hunter_jobs\resize_image.example.json --result .\outputs\resize_result.json
```

Supported tasks in V1:

- `image_info`
- `resize_image`
- `convert_image`
- `remove_background`

## Job JSON shape

```json
{
  "jobId": "creative_job_001",
  "task": "resize_image",
  "input": "D:/path/input.png",
  "output": "D:/path/output.png",
  "options": {
    "width": 1080,
    "overwrite": false,
    "quality": 95
  }
}
```

## Safety rules

- The engine does not overwrite source files.
- Output folders are created automatically.
- Existing output files are blocked unless `overwrite` is true.
- The CLI returns a JSON result and can also write a result JSON file.
- Client delivery still needs Hunter/staff approval.

## How Hunter should use it

Hunter should create a job JSON, call the CLI through the local executor, wait for the result JSON, then store/link the output back to the chat/case/job.

Hunter should not run heavy image/video work inside Cloudflare Workers.

## Next planned engine jobs

- `clean_image`
- `apply_brand_template`
- `generate_event_poster`
- `render_gif_or_intro`
- `prepare_social_ad`
- video timeline/keyframe renderer
