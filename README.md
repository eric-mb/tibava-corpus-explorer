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

Persons come from the face clustering plugin: each face detection (sampled every 0.5 s) belongs
to a cluster, and every cluster is treated as one person. `Good Bad Ugly` has no face clustering
results, so person-based patterns can't find hits there.

## Running the app

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run streamlit run app.py
```

## Views

### Pattern Search

Pick a pattern in the sidebar. The pattern is plain Python code, which you can edit and run in
the browser. It runs on all videos of the corpus at once, and each video gets its own interactive
shot timeline:

- one thumbnail per shot, above the shot boundaries
- shots coloured by camera size and labelled with the main person (`CU · A`)
- hits shown as coloured bars below the shots, one colour per group (for example `A↔B` vs. `C↔B`)
- hovering over a hit shows one thumbnail per shot of the sequence; clicking pins the preview
- each timeline starts fitted to the page width; `−` / `Fit` / `+` to zoom

**Save** writes the code to `patterns/<name>.py`. Saved patterns are also used by the
statistics view.

### Corpus Statistics

- camera-size distribution per video and for the whole corpus (by shot count or by screen time)
- for each saved pattern: hits per video, share of shots inside hits, hit length, and camera
  sizes inside hits compared with all shots

### Faces on Screen

One chart per video showing how many faces are detected at each moment (sampled every 0.5 s),
with shot boundaries as faint vertical lines. The caption gives the share of time with at least
one face, and the mean and maximum number of faces.

## Writing patterns

A pattern defines `find(video)` and returns a list of `Hit` objects:

```python
NAME = "Shot-reverse-shot"

def find(video):
    hits = []
    # video.shots[i].main_person, .persons, .scale, .start, .end ...
    hits.append(Hit(shots=[3, 4, 5], persons=[a, b]))
    return hits
```

| Attribute | Meaning |
| --------- | ------- |
| `video.shots` | list of `Shot` |
| `shot.scale` | `Extreme Close-Up`, `Close-Up`, `Medium`, `Full`, `Long` or `None` |
| `shot.persons` | `Counter` of face detections per person (face cluster id) |
| `shot.main_person` | the person detected most often in the shot, or `None` |
| `video.label(person)` | short letter for a person (`A` = most screen time) |

`Hit`, `Shot`, `Video` and `SHOT_SCALES` are available without importing them. `label` and
`group` are optional on a `Hit`: hits are labelled with their person sequence (`A-B-A`) and
coloured by person pair.

> Pattern code is executed with `exec`. This is fine for a local research tool. Don't expose the
> app to untrusted users.

### Included patterns

- **Shot-reverse-shot** (`patterns/shot_reverse_shot.py`): at least 3 consecutive shots that
  alternate between two persons (A-B-A, A-B-A-B, …). There is no maximum length.

## Code layout

```
app.py                  navigation between the views
views/pattern_search.py View 1
views/statistics.py     View 2
views/faces.py          View 3
explorer/data.py        export loader (shots, shot scales, thumbnails, faces, clusters)
explorer/patterns.py    Hit type, loading/saving/running patterns
explorer/timeline.py    HTML/JS timeline component
patterns/*.py           pattern definitions
```
