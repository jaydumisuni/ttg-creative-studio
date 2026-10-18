# Creative Studio Online Video Generation V1

**Product-owned provider integration.** Independent Creative Studio can generate
videos via optional cloud models without installing a local inference checkpoint
or Hunter. Existing Video Lab owns actual video import, editing and exports.

## Status and architecture

- **Now on KRATOS:** lightweight Python/Qt client, job planning, async
  provider submission/status/cancel/download and editable Studio import.
  Model inference is executed by an *external provider* when credentials,
  approved usage and billing are configured, not by KRATOS or this assistant.
- **Later on GT502 or Spark:** provide an optional local FreeVideo adapter and
  *user-initiated* model download after disk/GPU/license qualification. The
  previous full model manifest was around 92 GiB. **No model files are
  downloaded or stored on KRATOS by this change.**
- **Future AI operators:** assistants can be connected later through the
  existing shared video-tool contract. **Hunter is not connected or modified.**

## UI usage

Creative Studio desktop: **Tools → Generate Online Video · Optional Paid**.

Select a supported official model ("Faster / lower-cost candidate" or
"Higher-quality candidate"), duration (2–12 seconds), resolution and
aspect ratio. Enter a text prompt; optionally supply a public HTTPS image
URL. Using a local/private filename is intentionally unsupported until
an approved upload/privacy workflow exists.

External generation may cost money. **Each generation requires both** an
unchecked-by-default approval checkbox and a second confirmation dialog.
This is explicit permission to initiate *one* paid request; it is not a
guaranteed spend cap. Price is determined by Replicate and the selected
model; review current rates first.

A successful submission returns a persistent prediction ID. Use **Check
Status** to check actual remote progress. Use **Cancel Job** after explicit
confirmation or **Save MP4 / Import to Studio** when succeeded. Saving
downloads at most 125 MiB, refuses redirects and untrusted delivery hosts,
verifies the MP4 file signature, refuses overwrites and retains SHA-256
evidence. The normal Video Lab re-probes downloaded video before adding
a regular editable video layer to the project.

Close/reopen recovery: paste the previous prediction ID and check its
status. Credentials and model weights are never stored in a project.

## Provider setup

Replicate is the first optional online adapter:
- Provider: https://replicate.com/
- Official fast model: https://replicate.com/bytedance/seedance-1-pro-fast
- Official quality model: https://replicate.com/bytedance/seedance-1-pro
- Protocol: https://replicate.com/docs/topics/predictions/create-a-prediction

Create/obtain an API token from your own Replicate account and configure
\`REPLICATE_API_TOKEN\` as an environment variable via an approved secret
manager **before launching** Creative Studio. Do not commit tokens to code,
upload screenshots containing them, or send them through jobs. If not
configured, paid generation remains unavailable and the UI states why.

The API uses official model \`POST /v1/models/.../predictions\`, followed by
authenticated prediction status and explicit provider output retrieval.
No background polling loops or unbounded charges are introduced.
Provider usage fees are independent of a ChatGPT subscription.

### Standalone JSON CLI

The earlier shared interface is still available (no assistant configured).
Run \`python -B src/ttg_creative_studio/cli.py --catalog\` for the machine
readable contract. Video operations include \`video_generate\`,
\`video_generation_status\`, \`video_generation_cancel\`, and
\`video_generation_download\`.

Example *preparation*, not a live charge:

\`\`\`json
{
  "task": "video_generate",
  "jobId": "cloud_example",
  "options": {
    "mode": "online",
    "model": "fast",
    "prompt": "A cinematic close-up of a mobile phone on a neutral studio desk",
    "duration": 5,
    "resolution": "480p",
    "aspect_ratio": "16:9",
    "paid_approval": "APPROVE_PAID_VIDEO_GENERATION"
  }
}
\`\`\`

The \`paid_approval\` flag must be supplied only after **explicit approval
for that particular paid request**. Automated clients are not given
permission to set it themselves. Without configured credentials, the
request cannot run even with the flag.

For status:

\`\`\`json
{"task":"video_generation_status",
 "options":{"prediction_id":"<actual-provider-prediction-id>"}}
\`\`\`

For finished output:

\`\`\`json
{"task":"video_generation_download",
 "options":{"prediction_id":"<actual-provider-prediction-id>"},
 "output":"/approved/project/generated-video.mp4"}
\`\`\`

Only the optional online submission is billable. No automatic model
download, system package installation, GPU inference, or paid API call is
performed during tests.

## Evidentiary boundaries

The provider tests are isolated synthetic HTTP fixtures: they exercise
request shapes, paid approval, status, cancellation, download restrictions
and GUI behavior **without making any real calls** or charging money.
They are not proof of a real provider-account session or generated media.

A true production qualification requires an approved provider credential,
appropriate billing controls, a deliberately authorized paid test job,
the provider returning a real video, successful download and editing/
playback on the target machine. Signed release and actual model quality
acceptance remain separate.

FreeVideo's future local model integration is intentionally disabled. GT502
or Spark can be qualified later without reworking Creative Studio's core
video workflow. No Ptah/Hunter changes are part of this implementation.
