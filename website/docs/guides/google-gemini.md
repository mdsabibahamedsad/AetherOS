---
sidebar_position: 16
title: "Google Gemini"
description: "Use Aetheros with Google Gemini — native AI Studio API, API-key setup, OAuth option, tool calling, streaming, and quota guidance"
---

# Google Gemini

Aetheros supports Google Gemini as a native provider using the **Google AI Studio / Gemini API** — not the OpenAI-compatible endpoint. This lets Aetheros translate its internal OpenAI-shaped message and tool loop into Gemini's native `generateContent` API while preserving tool calling, streaming, multimodal inputs, and Gemini-specific response metadata.

Aetheros also supports a separate **Google Gemini (OAuth)** provider that uses the same Cloud Code Assist backend as Google's Gemini CLI. Use the API-key provider (`gemini`) for the lowest-risk official API path.

## Prerequisites

- **Google AI Studio API key** — create one at [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
- **Billing-enabled Google Cloud project** — recommended for agent use. Gemini's free tier is too small for long-running agent sessions because Aetheros may make several model calls per user turn.
- **Aetheros installed** — no extra Python package is required for the native Gemini provider.

:::tip API key path
Set `GOOGLE_API_KEY` or `GEMINI_API_KEY`. Aetheros checks both names for the `gemini` provider.
:::

## Quick Start

```bash
# Add your Gemini API key
echo "GOOGLE_API_KEY=..." >> ~/.aetheros/.env

# Select Gemini as your provider
aetheros model
# → Choose "More providers..." → "Google AI Studio"
# → Aetheros checks your key tier and shows Gemini models
# → Select a model

# Start chatting
aetheros chat
```

If you prefer direct config editing, use the native Gemini API base URL:

```yaml
model:
  default: gemini-3-flash-preview
  provider: gemini
  base_url: https://generativelanguage.googleapis.com/v1beta
```

## Configuration

After running `aetheros model`, your `~/.aetheros/config.yaml` will contain:

```yaml
model:
  default: gemini-3-flash-preview
  provider: gemini
  base_url: https://generativelanguage.googleapis.com/v1beta
```

And in `~/.aetheros/.env`:

```bash
GOOGLE_API_KEY=...
```

### Native Gemini API

The recommended endpoint is:

```text
https://generativelanguage.googleapis.com/v1beta
```

Aetheros detects this endpoint and creates its native Gemini adapter. Internally, Aetheros still keeps the agent loop in OpenAI-shaped messages, then translates each request to Gemini's native schema:

- `messages[]` → Gemini `contents[]`
- system prompts → Gemini `systemInstruction`
- tool schemas → Gemini `functionDeclarations`
- tool results → Gemini `functionResponse` parts
- streaming responses → OpenAI-shaped stream chunks for the Aetheros loop

:::note Gemini 3 thought signatures
For Gemini 3 tool use, Aetheros preserves the `thoughtSignature` values attached to function-call parts and replays them on the next tool turn. That covers the validation-critical path for multi-step agent workflows.

Gemini 3 may also attach thought signatures to other response parts. Aetheros' native adapter is optimized for agent tool loops today, so it does not yet replay every non-tool-call signature with full part-level fidelity.
:::

### Prefer the Native Endpoint

Google also exposes an OpenAI-compatible endpoint:

```text
https://generativelanguage.googleapis.com/v1beta/openai/
```

For Aetheros agent sessions, prefer the native Gemini endpoint above. Aetheros includes a native Gemini adapter so it can map multi-turn tool use, tool-call results, streaming, multimodal inputs, and Gemini response metadata directly onto Gemini's `generateContent` API. The OpenAI-compatible endpoint is still useful when you specifically need OpenAI API compatibility.

If you previously set `GEMINI_BASE_URL` to the `/openai` URL, remove it or change it:

```bash
GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta
```

### OAuth Provider

Aetheros also has a `google-gemini-cli` provider:

```bash
aetheros model
# → Choose "Google Gemini (OAuth)"
```

This uses browser PKCE login and the Cloud Code Assist backend. It can be useful for users who want Gemini CLI-style OAuth, but Aetheros shows an explicit warning because Google may treat use of the Gemini CLI OAuth client from third-party software as a policy violation. For production or lowest-risk usage, prefer the API-key provider above.

## Available Models

The `aetheros model` picker shows Gemini models maintained in Aetheros' provider registry. Common choices include:

| Model | ID | Notes |
|-------|----|-------|
| Gemini 3.1 Pro Preview | `gemini-3.1-pro-preview` | Most capable preview model when available |
| Gemini 3 Pro Preview | `gemini-3-pro-preview` | Strong reasoning and coding model |
| Gemini 3 Flash Preview | `gemini-3-flash-preview` | Recommended default balance of speed and capability |
| Gemini 3.1 Flash Lite Preview | `gemini-3.1-flash-lite-preview` | Fastest / lowest-cost option when available |

Model availability changes over time. If a model disappears or is not enabled for your key, run `aetheros model` again and pick one from the current list.

:::info Model IDs
Use Gemini's native model IDs such as `gemini-3-flash-preview`, not OpenRouter-style IDs like `google/gemini-3-flash-preview`, when `provider: gemini`.
:::

### Latest Aliases

Google publishes moving aliases for the Pro and Flash Gemini families. `gemini-pro-latest` and `gemini-flash-latest` are useful when you want Google to advance the model automatically without changing your Aetheros config.

| Alias | Currently tracks | Notes |
|-------|------------------|-------|
| `gemini-pro-latest` | Latest Gemini Pro model | Best when you want Google's current Pro default |
| `gemini-flash-latest` | Latest Gemini Flash model | Best when you want Google's current Flash default |

```yaml
model:
  default: gemini-pro-latest
  provider: gemini
  base_url: https://generativelanguage.googleapis.com/v1beta
```

If you need strict reproducibility, prefer explicit model IDs such as `gemini-3.1-pro-preview` or `gemini-3-flash-preview`.

### Gemma via the Gemini API

Google also exposes Gemma models through the Gemini API. Aetheros recognizes these as Google models, but hides very low-throughput Gemma entries from the default model picker so new users do not accidentally select an evaluation-tier model for a long-running agent session.

Useful evaluation IDs include:

| Model | ID | Notes |
|-------|----|-------|
| Gemma 4 31B IT | `gemma-4-31b-it` | Larger Gemma model; useful for compatibility and quality evaluation |
| Gemma 4 26B A4B IT | `gemma-4-26b-a4b-it` | Smaller active-parameter variant when available |

These models are best treated as evaluation options on Gemini API keys. Google's Gemma API pricing is free-tier-only and the usage caps are low compared with production Gemini models, so sustained Aetheros agent use should normally move to a paid Gemini model, a self-hosted deployment, or another provider with appropriate quota.

To use a Gemma model that is hidden from the picker, set it directly:

```yaml
model:
  default: gemma-4-31b-it
  provider: gemini
  base_url: https://generativelanguage.googleapis.com/v1beta
```

## Switching Models Mid-Session

Use the `/model` command during a conversation:

```text
/model gemini-3-flash-preview
/model gemini-flash-latest
/model gemini-3-pro-preview
/model gemini-pro-latest
/model gemma-4-31b-it
/model gemini-3.1-flash-lite-preview
```

If you have not configured Gemini yet, exit the session and run `aetheros model` first. `/model` switches among already-configured providers and models; it does not collect new API keys.

## Diagnostics

```bash
aetheros doctor
```

The doctor checks:

- Whether `GOOGLE_API_KEY` or `GEMINI_API_KEY` is available
- Whether Gemini OAuth credentials exist for `google-gemini-cli`
- Whether configured provider credentials can be resolved

For OAuth quota usage, run this inside a Aetheros session:

```text
/gquota
```

`/gquota` applies to the `google-gemini-cli` OAuth provider, not the AI Studio API-key provider.

## Gateway (Messaging Platforms)

Gemini works with all Aetheros gateway platforms (Telegram, Discord, Slack, WhatsApp, LINE, Feishu, etc.). Configure Gemini as your provider, then start the gateway normally:

```bash
aetheros gateway setup
aetheros gateway start
```

The gateway reads `config.yaml` and uses the same Gemini provider configuration.

## Troubleshooting

### "Gemini native client requires an API key"

Aetheros could not find a usable API key. Add one of these to `~/.aetheros/.env`:

```bash
GOOGLE_API_KEY=...
# or
GEMINI_API_KEY=...
```

Then run `aetheros model` again.

### "This Google API key is on the free tier"

Aetheros probes Gemini API keys during setup. Free-tier quotas can be exhausted after a handful of agent turns because tool use, retries, compression, and auxiliary tasks may require multiple model calls.

Enable billing on the Google Cloud project attached to your key, regenerate the key if needed, then run:

```bash
aetheros model
```

### "404 model not found"

The selected model is not available for your account, region, or key. Run `aetheros model` again and pick another Gemini model from the current list.

### Gemma model is not shown in `aetheros model`

Aetheros may hide low-throughput Gemma models from the picker by default. If you intentionally want to evaluate one, set the model ID directly in `~/.aetheros/config.yaml`.

### "429 quota exceeded" on Gemma

Gemma models exposed through the Gemini API are useful for evaluation, but their Gemini API free-tier caps are low. Use them for compatibility testing, then switch to a paid Gemini model or another provider for sustained agent sessions.

### OpenAI-compatible endpoint is configured

Check `~/.aetheros/.env` for:

```bash
GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
```

Change it to the native endpoint or remove the override:

```bash
GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta
```

### OAuth login warning

The `google-gemini-cli` provider uses a Gemini CLI / Cloud Code Assist OAuth flow. Aetheros warns before starting it because this is distinct from the official AI Studio API-key path. Use `provider: gemini` with `GOOGLE_API_KEY` for the official API-key integration.

### Tool calling fails with schema errors

Upgrade Aetheros and rerun `aetheros model`. The native Gemini adapter sanitizes tool schemas for Gemini's stricter function-declaration format; older builds or custom endpoints may not.

## Related

- [AI Providers](/integrations/providers)
- [Configuration](/user-guide/configuration)
- [Fallback Providers](/user-guide/features/fallback-providers)
- [AWS Bedrock](/guides/aws-bedrock) — native cloud-provider integration using AWS credentials
