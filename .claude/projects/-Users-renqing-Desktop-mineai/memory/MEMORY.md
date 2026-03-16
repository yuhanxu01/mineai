# MineAI Project Memory

## Project Overview
- **Type**: Django + React SPA (single-file template)
- **Main template**: `templates/index.html` (~5400 lines, all-in-one React with Babel CDN)
- **Backend**: Django REST Framework, SQLite, Token auth
- **LLM**: Zhipu AI GLM (glm-4.7-flash)

## Architecture
- React SPA with hash routing (`#/`, `#/login`, `#/app/<slug>`)
- Root component handles auth and routing
- Each app is a full React component (MemoryForgeApp, OCRStudioApp, PaperLabApp, KGApp)
- Platform homepage = `PlatformHome` component

## Key Apps
- `memoryforge` - Novel writing assistant (hierarchical memory nodes)
- `ocr_studio` - OCR processing
- `paper_lab` - Academic research / paper reading
- `knowledge_graph` - Knowledge graph visualization
- `novel_share` - Published novel sharing (redirects to /share/)

## Hub Model (`hub/models.py`)
- `App`: name, slug, description, icon, color, is_active, order
- API: GET `/api/platform/apps/` → active apps list

## Token Usage API (`accounts/views.py` MeView)
Returns: `usage.{prompt_count, input_tokens, output_tokens, total_tokens, daily_*}`
Returns: `quota.{daily_prompt_count, daily_input_tokens, daily_output_tokens}` (null if own key or staff)

## Dashboard (PlatformHome) - implemented in worktree sharp-engelbart
- Full dashboard with: token stats, app grid with customizable colors, theme panel
- Theme system: 4 dark presets (dark_gold, dark_blue, dark_green, dark_purple) + custom accent
- Theme stored in localStorage as `mf_tid` and `mf_accent`
- App colors stored in localStorage as `mf_app_colors: {slug: color}`
- Search bar + AI recommendation (streams to `/api/core/chat-stream/`)
- Theme init script runs before React to prevent flash

## CSS Variables (`:root`)
- `--bg` through `--bg5`: background layers (darkest to lightest)
- `--fg`, `--fg2`, `--fg3`: foreground/text
- `--gold`, `--gold2`, `--gold-dim`: primary accent
- `--red`, `--green`, `--blue`, `--purple`, `--cyan`, `--orange`: status colors
- `--border`, `--border2`: borders
- Fonts: `--serif` (Noto Serif SC), `--sans` (Noto Sans SC), `--mono` (JetBrains Mono)

## User Preferences
- Communicates in Chinese (zh-CN)
- Prefers concise, focused responses
