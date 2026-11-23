"""Loading TIB-AV-A video exports into a simple, pattern-friendly data model.

An export is a ZIP archive with YAML metadata at the top level and one nested
ZIP per data object in ``data/``. Annotation timelines (e.g. "Shot Scales")
store their segments in ``data/<timeline id>.zip``; plugin results reference
their data via ``plugin_run_results.yml``.
"""

from __future__ import annotations

import io
import zipfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import yaml

try:  # the C loader is much faster for the large bbox/face files
    _Loader = yaml.CSafeLoader
except AttributeError:  # pragma: no cover
    _Loader = yaml.SafeLoader

EXPORTS_DIR = Path(__file__).resolve().parent.parent / "exports"

SHOT_SCALES = ["Extreme Close-Up", "Close-Up", "Medium", "Full", "Long"]


@dataclass
class Face:
    id: str
    time: float
    cluster: str | None  # face cluster id = person identity
    x: float
    y: float
    w: float
    h: float
    score: float
    image_id: str | None = None


@dataclass
class Shot:
    index: int
    start: float
    end: float
    scale: str | None = None  # one of SHOT_SCALES
    movement: str | None = None
    faces: list[Face] = field(default_factory=list)
    thumbnail_id: str | None = None

    @property
    def duration(self) -> float:
        return self.end - self.start

    @property
    def persons(self) -> Counter:
        """Number of face detections per person (cluster id) in this shot."""
        return Counter(f.cluster for f in self.faces if f.cluster is not None)

    @property
    def main_person(self) -> str | None:
        """The person seen most often in the shot (ties: larger total face area)."""
        if not self.persons:
            return None
        area: Counter = Counter()
        for f in self.faces:
            if f.cluster is not None:
                area[f.cluster] += f.w * f.h
        return max(self.persons, key=lambda p: (self.persons[p], area[p]))


@dataclass
class Video:
    name: str
    path: Path
    duration: float
    fps: float
    shots: list[Shot]
    faces: list[Face]
    # person (cluster id) -> short label "A", "B", ... ordered by screen time
    person_labels: dict[str, str]
    has_faces: bool
    _images: dict[str, tuple[str, str]] = field(default_factory=dict, repr=False)

    def label(self, person: str | None) -> str:
        return "–" if person is None else self.person_labels.get(person, "?")

    def image(self, image_id: str | None) -> bytes | None:
        """Raw JPEG bytes of a thumbnail or face crop."""
        if image_id is None or image_id not in self._images:
            return None
        data_id, member = self._images[image_id]
        with zipfile.ZipFile(self.path) as outer:
            with zipfile.ZipFile(io.BytesIO(outer.read(f"data/{data_id}.zip"))) as inner:
                return inner.read(member)

    def images(self, image_ids: list[str | None]) -> dict[str, bytes]:
        """Batch variant of :meth:`image` that opens each archive only once."""
        by_data: dict[str, list[str]] = {}
        for iid in image_ids:
            if iid and iid in self._images:
                by_data.setdefault(self._images[iid][0], []).append(iid)
        out: dict[str, bytes] = {}
        with zipfile.ZipFile(self.path) as outer:
            for data_id, iids in by_data.items():
                with zipfile.ZipFile(io.BytesIO(outer.read(f"data/{data_id}.zip"))) as inner:
                    for iid in iids:
                        out[iid] = inner.read(self._images[iid][1])
        return out

    def person_face(self, person: str) -> str | None:
        """Image id of a representative (largest) face crop for a person."""
        faces = [f for f in self.faces if f.cluster == person and f.image_id]
        if not faces:
            return None
        return max(faces, key=lambda f: f.w * f.h * f.score).image_id


def _yaml(data: bytes):
    return yaml.load(data, Loader=_Loader)


class _Export:
    def __init__(self, path: Path):
        self.zf = zipfile.ZipFile(path)

    def top(self, name: str):
        return _yaml(self.zf.read(name))

    def inner(self, data_id: str) -> zipfile.ZipFile | None:
        name = f"data/{data_id}.zip"
        if name not in self.zf.namelist():
            return None
        return zipfile.ZipFile(io.BytesIO(self.zf.read(name)))

    def inner_yaml(self, data_id: str, member: str):
        inner = self.inner(data_id)
        if inner is None or member not in inner.namelist():
            return None
        return _yaml(inner.read(member))


def _overlap(a0: float, a1: float, b0: float, b1: float) -> float:
    return max(0.0, min(a1, b1) - max(a0, b0))


def _assign_labels(shots: list[Shot], timeline: list[dict] | None, attr: str) -> None:
    """Give each shot the label of the annotation segment overlapping it most."""
    if not timeline:
        return
    for shot in shots:
        best, best_ov = None, 0.0
        for seg in timeline:
            ov = _overlap(shot.start, shot.end, seg["start"], seg["end"])
            if ov > best_ov and seg.get("labels"):
                best, best_ov = seg["labels"][0].split("::")[-1], ov
        setattr(shot, attr, best)


def load_video(path: str | Path) -> Video:
    path = Path(path)
    ex = _Export(path)
    video_meta = ex.top("video.yml")
    runs = {r["id"]: r["type"] for r in ex.top("plugin_runs.yml")}
    results = ex.top("plugin_run_results.yml") or []
    timelines = ex.top("timelines.yml") or []

    def result_ids(plugin: str, rtype: str) -> list[str]:
        return [
            r["data_id"]
            for r in results
            if runs.get(r["plugin_run_id"]) == plugin and r["type"] == rtype
        ]

    # --- shots -----------------------------------------------------------
    shots: list[Shot] = []
    for data_id in result_ids("shotdetection", "SHOTS"):
        d = ex.inner_yaml(data_id, "shots_data.yml")
        shots = [Shot(i, s["start"], s["end"]) for i, s in enumerate(d["shots"])]

    # --- shot scale / movement annotation timelines ----------------------
    for tl in timelines:
        if tl.get("type") != "ANNOTATION":
            continue
        attr = {"Shot Scales": "scale", "Shot Movements": "movement"}.get(tl["name"])
        if attr:
            d = ex.inner_yaml(tl["id"], "annotation_data.yml")
            _assign_labels(shots, d and d.get("annotations"), attr)

    images: dict[str, tuple[str, str]] = {}

    # --- thumbnails: pick the frame closest to each shot's middle ---------
    for data_id in result_ids("thumbnail", "IMAGES"):
        d = ex.inner_yaml(data_id, "images_data.yml")
        thumbs = sorted(d["images"], key=lambda im: im["time"])
        for im in thumbs:
            images[im["id"]] = (data_id, f"{im['id']}.{im['ext']}")
        times = [im["time"] for im in thumbs]
        for shot in shots:
            mid = (shot.start + shot.end) / 2
            j = min(range(len(times)), key=lambda k: abs(times[k] - mid)) if times else None
            shot.thumbnail_id = thumbs[j]["id"] if j is not None else None

    # --- faces + clusters ------------------------------------------------
    faces: list[Face] = []
    face_cluster: dict[str, str] = {}
    for data_id in result_ids("face_clustering", "CLUSTER"):
        for c in ex.inner_yaml(data_id, "cluster_data.yml")["cluster"]:
            for face_id in c.get("embedding_ref_ids") or []:
                face_cluster[face_id] = c["id"]

    face_image: dict[str, str] = {}
    for data_id in result_ids("face_clustering", "IMAGES"):
        for im in ex.inner_yaml(data_id, "images_data.yml")["images"]:
            images[im["id"]] = (data_id, f"{im['id']}.{im['ext']}")
            if im.get("ref_id"):
                face_image[im["ref_id"]] = im["id"]

    for data_id in result_ids("face_clustering", "TYPE_BBOXES"):
        for b in ex.inner_yaml(data_id, "bboxes_data.yml")["bboxes"]:
            fid = b["ref_id"]
            faces.append(
                Face(
                    id=fid,
                    time=b["time"],
                    cluster=face_cluster.get(fid),
                    x=b["x"], y=b["y"], w=b["w"], h=b["h"],
                    score=b.get("det_score", 1.0),
                    image_id=face_image.get(fid),
                )
            )

    # assign faces to shots (faces are sampled every 0.5 s)
    for f in faces:
        for s in shots:
            if s.start <= f.time <= s.end:
                s.faces.append(f)
                break

    counts = Counter(f.cluster for f in faces if f.cluster is not None)
    labels = {}
    for i, (cid, _) in enumerate(counts.most_common()):
        labels[cid] = _letters(i)

    return Video(
        name=video_meta.get("name") or path.stem,
        path=path,
        duration=float(video_meta.get("duration") or (shots[-1].end if shots else 0)),
        fps=float(video_meta.get("fps") or 25),
        shots=shots,
        faces=faces,
        person_labels=labels,
        has_faces=bool(faces),
        _images=images,
    )


def _letters(i: int) -> str:
    """0 -> A, 25 -> Z, 26 -> AA, ..."""
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def list_exports(directory: Path = EXPORTS_DIR) -> list[Path]:
    return sorted(directory.glob("*.zip"), key=lambda p: p.stem.lower())
