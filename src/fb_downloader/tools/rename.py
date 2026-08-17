"""
Rename already-downloaded files to the current naming scheme.

Older downloads were named after the account ("20260728_えり夫がハマる褒められ
ごはん_Video_erigohan.mp4"). This walks directories, reads the description text
saved next to each video, and renames the whole set to
"<download date>_<subject of the video>".

One command renames the current folder and every subfolder below it:

    fbdl-rename            # or: python3 -m fb_downloader.tools.rename
    fbdl-rename -n         # preview first
    fbdl-rename --undo .fbdl-rename-undo.json

Only files whose name starts with a YYYYMMDD_ date are touched, since that is
what fbdl produces; --all lifts that restriction.
"""

import argparse
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..core.models import VideoInfo, VideoQuality
from ..utils.filename import FileNameGenerator

logger = logging.getLogger(__name__)

# Files fbdl produces for one video
MEDIA_SUFFIXES = (".mp4", ".m4a", ".webm", ".mkv", ".mov")
COMPANION_SUFFIXES = (".txt", "_yt.srt", ".srt", ".description")

DATE_PREFIX = re.compile(r"^(\d{8})_")

# Written before renaming so the operation can always be reversed
DEFAULT_UNDO_LOG = ".fbdl-rename-undo.json"


class RenamePlan:
    """One video and the new name derived from its description"""

    def __init__(self, media: Path, members: List[Path], new_stem: str):
        self.media = media
        self.members = members
        self.new_stem = new_stem

    @property
    def old_stem(self) -> str:
        return self.media.stem

    def targets(self) -> List[Tuple[Path, Path]]:
        """(source, destination) for every file belonging to this video"""
        moves = []
        for member in self.members:
            suffix = member.name.replace(self.old_stem, "", 1)
            moves.append((member, member.with_name(f"{self.new_stem}{suffix}")))
        return moves


def _download_date(media: Path) -> str:
    """The day the file was downloaded.

    fbdl stamps that date into the name, so the existing prefix is the most
    faithful record; otherwise fall back to when the file appeared on disk.
    """
    match = DATE_PREFIX.match(media.stem)
    if match:
        return match.group(1)

    stat = media.stat()
    created = getattr(stat, "st_birthtime", stat.st_mtime)
    return datetime.fromtimestamp(created).strftime("%Y%m%d")


def _members_of(media: Path) -> List[Path]:
    """The media file plus its description and subtitle siblings"""
    members = [media]
    for suffix in COMPANION_SUFFIXES:
        companion = media.with_name(f"{media.stem}{suffix}")
        if companion.exists() and companion != media:
            members.append(companion)
    return members


def _read_description(members: List[Path]) -> str:
    for member in members:
        if member.suffix == ".txt":
            try:
                return member.read_text(encoding="utf-8", errors="replace").strip()
            except OSError as e:
                logger.warning(f"Cannot read {member}: {e}")
    return ""


def _unique_stem(stem: str, directory: Path, taken: Dict[Path, str], keep: List[Path]) -> str:
    """Avoid colliding with an existing file or with another planned rename"""

    def collides(candidate: str) -> bool:
        for suffix in MEDIA_SUFFIXES:
            path = directory / f"{candidate}{suffix}"
            if path in taken:
                return True
            if path.exists() and path not in keep:
                return True
        return False

    if not collides(stem):
        return stem

    for index in range(2, 1000):
        candidate = f"{stem}_{index}"
        if not collides(candidate):
            return candidate

    return stem


def build_plans(
    roots: List[Path], recursive: bool = True, dated_only: bool = True
) -> Tuple[List[RenamePlan], List[Path]]:
    """Work out the new name for every video found under the given roots"""
    plans: List[RenamePlan] = []
    skipped: List[Path] = []
    taken: Dict[Path, str] = {}

    media_files: List[Path] = []
    for root in roots:
        if root.is_file():
            media_files.append(root)
            continue
        pattern = "**/*" if recursive else "*"
        media_files.extend(
            path
            for path in sorted(root.glob(pattern))
            if path.is_file() and path.suffix.lower() in MEDIA_SUFFIXES
        )

    if dated_only:
        # Every fbdl download starts with its date. Without this guard a run
        # over ~/Movies would also rewrite unrelated collections that happen
        # to keep a same-named .txt beside each video.
        media_files = [path for path in media_files if DATE_PREFIX.match(path.stem)]

    total = len(media_files)
    for index, media in enumerate(sorted(set(media_files)), 1):
        members = _members_of(media)
        description = _read_description(members)
        if not description:
            # Without the post body there is nothing to name the file after
            skipped.append(media)
            continue

        print(f"[{index}/{total}] {media.name}", file=sys.stderr)

        video_info = VideoInfo(
            url="",
            quality=VideoQuality.STANDARD,
            description=description,
        )
        generated = FileNameGenerator.generate(video_info, date_str=_download_date(media))
        new_stem = Path(generated).stem

        if new_stem == media.stem:
            continue

        new_stem = _unique_stem(new_stem, media.parent, taken, keep=members)
        for suffix in MEDIA_SUFFIXES:
            taken[media.parent / f"{new_stem}{suffix}"] = new_stem

        plans.append(RenamePlan(media, members, new_stem))

    return plans, skipped


def apply_moves(moves: List[Tuple[Path, Path]]) -> Tuple[int, int]:
    """Perform (source, destination) renames; returns (done, failed)"""
    done = failed = 0
    for source, destination in moves:
        if not source.exists():
            logger.warning(f"Missing, skipped: {source}")
            failed += 1
            continue
        if destination.exists():
            logger.warning(f"Target already exists, skipped: {destination}")
            failed += 1
            continue
        try:
            source.rename(destination)
            done += 1
        except OSError as e:
            logger.error(f"Failed to rename {source.name}: {e}")
            failed += 1
    return done, failed


def save_plan(plans: List[RenamePlan], path: Path) -> None:
    """Write the moves to disk: what was reviewed is what gets applied.

    It doubles as the undo record — the pairs can be replayed in reverse.
    """
    moves = [
        {"from": str(source), "to": str(destination)}
        for plan in plans
        for source, destination in plan.targets()
    ]
    try:
        path.write_text(json.dumps(moves, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as e:
        logger.warning(f"Could not write the undo log to {path}: {e}")


def load_plan(path: Path) -> List[Tuple[Path, Path]]:
    """Read back a saved plan"""
    data = json.loads(path.read_text(encoding="utf-8"))
    return [(Path(entry["from"]), Path(entry["to"])) for entry in data]


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="fbdl-rename",
        description=(
            "Rename downloaded videos to '<download date>_<subject>', "
            "reading the subject from the description saved next to each file."
        ),
        epilog=(
            "Examples:\n"
            "  fbdl-rename                      # rename this folder and every subfolder\n"
            "  fbdl-rename ~/Movies ~/Desktop   # rename the given trees\n"
            "  fbdl-rename -n                   # preview without touching anything\n"
            "  fbdl-rename --undo .fbdl-rename-undo.json   # put the old names back"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("paths", nargs="*", default=["."], help="Directories to scan (default: .)")
    parser.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        help="Show what would change and stop",
    )
    parser.add_argument(
        "--no-recursive", action="store_true", help="Do not descend into subdirectories"
    )
    parser.add_argument(
        "--no-claude",
        action="store_true",
        help="Never call 'claude -p'; use only titles declared in the post body",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help=(
            "Also rename videos that do not start with a YYYYMMDD_ date. "
            "Off by default so unrelated collections are left alone"
        ),
    )
    parser.add_argument(
        "--plan",
        metavar="FILE",
        default=DEFAULT_UNDO_LOG,
        help=f"Where to record the renames for --undo (default: {DEFAULT_UNDO_LOG})",
    )
    parser.add_argument(
        "--undo", metavar="FILE", help="Reverse the renames recorded in a plan FILE"
    )
    ns = parser.parse_args(argv if argv is not None else sys.argv[1:])

    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

    if ns.undo:
        moves = [(dst, src) for src, dst in load_plan(Path(ns.undo).expanduser())]
        done, failed = apply_moves(moves)
        print(f"Reverted {done} file(s), {failed} skipped.")
        return 0 if not failed else 1

    if ns.no_claude:
        FileNameGenerator.USE_CLAUDE = False

    roots = [Path(p).expanduser() for p in (ns.paths or ["."])]
    missing = [root for root in roots if not root.exists()]
    if missing:
        for root in missing:
            print(f"No such path: {root}", file=sys.stderr)
        return 1

    plans, skipped = build_plans(roots, recursive=not ns.no_recursive, dated_only=not ns.all)

    if not plans:
        print("\nNothing to rename.")
    else:
        current_dir = None
        print()
        for plan in plans:
            if plan.media.parent != current_dir:
                current_dir = plan.media.parent
                print(f"{current_dir}")
            print(f"  {plan.old_stem}")
            print(f"    -> {plan.new_stem}   [{len(plan.members)} file(s)]")

    if skipped:
        print(f"\n{len(skipped)} file(s) skipped (no description text alongside):")
        for path in skipped[:10]:
            print(f"  {path}")
        if len(skipped) > 10:
            print(f"  ... and {len(skipped) - 10} more")

    if ns.dry_run:
        print(f"\nDry run: {len(plans)} video(s) would be renamed. Re-run without -n to do it.")
        return 0

    if not plans:
        return 0

    # Record before renaming: the log is what makes --undo possible
    if ns.plan:
        save_plan(plans, Path(ns.plan).expanduser())

    moves = [move for plan in plans for move in plan.targets()]
    done, failed = apply_moves(moves)
    print(f"\nRenamed {done} file(s) across {len(plans)} video(s), {failed} skipped.")
    if ns.plan:
        print(f"Undo with: fbdl-rename --undo {ns.plan}")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
