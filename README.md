# TIB-AV-A Corpus Explorer

A [Streamlit](https://streamlit.io/) app for exploring a corpus of videos annotated with
[TIB AV-Analytics (TIB-AV-A)](https://service.tib.eu/tibava), a web platform for
AI-assisted video analysis.

This repository is also a **vibe coding demonstration**: the app is built step by step through
prompts to an AI coding assistant (Claude Code). Every prompt is recorded in
[PROMPTS.md](PROMPTS.md), and the output of each step is committed on its own, so the git history
shows how the project grew one prompt at a time.

## Data

The `exports/` folder holds one ZIP archive per video, exported from TIB-AV-A. Each archive contains:

| File                     | Content                                                    |
| ------------------------ | ---------------------------------------------------------- |
| `meta.yml`               | Export metadata                                            |
| `video.yml`              | Video information                                          |
| `timelines.yml`          | Timelines and their annotation segments                    |
| `plugin_runs.yml`        | Analysis plugins that were run on the video                |
| `plugin_run_results.yml` | Results produced by those plugin runs                      |
| `data/*.zip`             | Data files for the plugin results                          |

## Status

Work in progress. Setup and usage instructions will be added once the app exists.
