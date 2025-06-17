# Community-Adaptive-Talk-Engine
Community Adaptive Talk Engine

## Configuration

The bot reads settings from environment variables or an optional `Config.json`.
Set the following variables when running in Codex or other environments:

```
DISCORD_BOT_TOKEN=<your discord token>
GEMINI_TOKEN=<your gemini token>
YOUR_DISCORD_ID=<your user id>
MEMORY_CHANNEL=<channel id for long term memory>
```

If `Config.json` is present, its values will override missing environment
variables.
