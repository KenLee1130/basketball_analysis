"""Download and segment full-game videos for analysis."""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


FULL_GAME_DIR = Path(__file__).resolve().parent
DEFAULT_DOWNLOAD_DIR = FULL_GAME_DIR / "downloads"
DEFAULT_SEGMENT_DIR = FULL_GAME_DIR / "segments"
DEFAULT_OUTPUT_TEMPLATE = "%(title).200B [%(id)s].%(ext)s"
MIN_YT_DLP_YOUTUBE_VERSION = (2025, 11, 12)


def parse_resolution(value: str) -> str | int:
    """Accept either 'best' or a positive integer height."""
    if value.lower() == "best":
        return "best"

    try:
        resolution = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "Resolution must be 'best' or a positive integer like 720."
        ) from exc

    if resolution <= 0:
        raise argparse.ArgumentTypeError("Resolution must be greater than zero.")

    return resolution


def parse_time_to_seconds(value: str) -> float:
    """Parse seconds, MM:SS, or HH:MM:SS[.mmm] into total seconds."""
    raw_value = value.strip()
    if not raw_value:
        raise argparse.ArgumentTypeError("Time value cannot be empty.")

    try:
        if ":" not in raw_value:
            seconds = float(raw_value)
        else:
            parts = raw_value.split(":")
            if len(parts) not in {2, 3}:
                raise ValueError

            parts_as_float = [float(part) for part in parts]
            if len(parts_as_float) == 2:
                minutes, seconds_part = parts_as_float
                seconds = (minutes * 60) + seconds_part
            else:
                hours, minutes, seconds_part = parts_as_float
                seconds = (hours * 3600) + (minutes * 60) + seconds_part
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "Time must be in seconds, MM:SS, or HH:MM:SS format."
        ) from exc

    if seconds < 0:
        raise argparse.ArgumentTypeError("Time cannot be negative.")

    return seconds


def seconds_to_ffmpeg_time(seconds: float) -> str:
    """Format seconds for ffmpeg CLI arguments."""
    return f"{seconds:.3f}".rstrip("0").rstrip(".")


def seconds_to_file_label(seconds: float) -> str:
    """Format seconds for filenames."""
    total_milliseconds = int(round(seconds * 1000))
    hours, remainder = divmod(total_milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, milliseconds = divmod(remainder, 1000)
    return f"{hours:02d}-{minutes:02d}-{secs:02d}-{milliseconds:03d}"


def require_command(command_name: str) -> str:
    """Ensure an external dependency is available on PATH."""
    resolved = shutil.which(command_name)
    if resolved is None:
        raise RuntimeError(
            f"Required command '{command_name}' was not found on PATH."
        )
    return resolved


def parse_yt_dlp_version(version_text: str) -> tuple[int, int, int] | None:
    """Parse version text like 2026.03.17 into a comparable tuple."""
    cleaned = version_text.strip()
    parts = cleaned.split(".")
    if len(parts) < 3 or not all(part.isdigit() for part in parts[:3]):
        return None
    return tuple(int(part) for part in parts[:3])


def get_yt_dlp_version(yt_dlp_path: str) -> tuple[int, int, int] | None:
    """Read the installed yt-dlp version."""
    result = subprocess.run(
        [yt_dlp_path, "--version"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return parse_yt_dlp_version(result.stdout)


def detect_js_runtime() -> str | None:
    """Pick the best available JS runtime for recent yt-dlp YouTube support."""
    for runtime in ("deno", "node", "quickjs", "bun"):
        if shutil.which(runtime):
            return runtime
    return None


def build_yt_dlp_failure_hint(command_output: str) -> str:
    """Return a targeted help message for common YouTube extractor failures."""
    lower_output = command_output.lower()
    if (
        "precondition check failed" in lower_output
        or "signature extraction failed" in lower_output
        or "only images are available" in lower_output
        or "requested format is not available" in lower_output
    ):
        return (
            "\n\nThis looks like a YouTube extractor compatibility problem, not a bug in "
            "the wrapper itself.\n"
            "Recommended fixes:\n"
            "1. Update yt-dlp to a current release.\n"
            "2. Use a build that includes yt-dlp-ejs.\n"
            "3. Ensure a JS runtime is available. This machine already has Node, so a "
            "newer yt-dlp can use it.\n"
            "4. If the video still resists download, retry with browser cookies via "
            "`--cookies-from-browser chrome` or another browser.\n"
        )
    return ""


def run_command(command: list[str]) -> str:
    """Run a subprocess and return combined output for logging/parsing."""
    result = subprocess.run(command, capture_output=True, text=True)
    combined_output = "\n".join(
        chunk for chunk in (result.stdout.strip(), result.stderr.strip()) if chunk
    )

    if combined_output:
        print(combined_output)

    if result.returncode != 0:
        raise RuntimeError(
            "Command failed:\n"
            f"{' '.join(command)}\n\n"
            f"{combined_output or 'No error output was produced.'}"
            f"{build_yt_dlp_failure_hint(combined_output)}"
        )

    return combined_output


def build_format_selector(resolution: str | int) -> str:
    """Create a yt-dlp format selector with an optional max resolution."""
    if resolution == "best":
        return "bestvideo*+bestaudio/best"

    return (
        f"bestvideo*[height<=?{resolution}]+bestaudio/"
        f"best[height<=?{resolution}]"
    )


def find_downloaded_path(command_output: str) -> Path | None:
    """Locate the downloaded path from yt-dlp output."""
    for line in reversed(command_output.splitlines()):
        stripped = line.strip()
        if not stripped.startswith("/"):
            continue
        try:
            if Path(stripped).exists():
                return Path(stripped)
        except OSError:
            continue
    return None


def download_video(
    url: str,
    resolution: str | int,
    output_dir: Path,
    filename_template: str,
    overwrite: bool,
    cookies_from_browser: str | None,
    cookies_file: str | None,
) -> Path:
    """Download a single YouTube video with yt-dlp."""
    yt_dlp_path = require_command("yt-dlp")
    require_command("ffmpeg")
    yt_dlp_version = get_yt_dlp_version(yt_dlp_path)
    js_runtime = detect_js_runtime()

    output_dir.mkdir(parents=True, exist_ok=True)

    command = [
        yt_dlp_path,
        "--no-playlist",
        "--no-progress",
        "--newline",
        "--restrict-filenames",
        "--merge-output-format",
        "mp4",
        "-f",
        build_format_selector(resolution),
        "-P",
        str(output_dir),
        "-o",
        filename_template,
        "--print",
        "after_move:filepath",
    ]

    if cookies_from_browser:
        command.extend(["--cookies-from-browser", cookies_from_browser])

    if cookies_file:
        command.extend(["--cookies", cookies_file])

    if (
        yt_dlp_version is not None
        and yt_dlp_version >= MIN_YT_DLP_YOUTUBE_VERSION
        and js_runtime is not None
    ):
        command.extend(["--js-runtimes", js_runtime])

    command.append("--force-overwrites" if overwrite else "--no-overwrites")
    command.append(url)

    if yt_dlp_version is not None and yt_dlp_version < MIN_YT_DLP_YOUTUBE_VERSION:
        min_version_text = ".".join(str(part) for part in MIN_YT_DLP_YOUTUBE_VERSION)
        print(
            "Warning: detected yt-dlp version "
            f"{'.'.join(str(part) for part in yt_dlp_version)}. "
            f"YouTube downloads are much more reliable on {min_version_text}+."
        )

    command_output = run_command(command)
    downloaded_path = find_downloaded_path(command_output)

    if downloaded_path is None:
        raise RuntimeError(
            "yt-dlp finished, but the downloaded file path could not be determined."
        )

    print(f"\nDownloaded video saved to:\n{downloaded_path}")
    return downloaded_path


def build_segment_output_path(
    input_path: Path,
    output_path: str | None,
    output_dir: Path,
    start_time: float,
    end_time: float,
) -> Path:
    """Choose the final clip path."""
    if output_path:
        return Path(output_path).expanduser().resolve()

    output_dir.mkdir(parents=True, exist_ok=True)
    start_label = seconds_to_file_label(start_time)
    end_label = seconds_to_file_label(end_time)
    return output_dir / f"{input_path.stem}_{start_label}_to_{end_label}.mp4"


def segment_video(
    input_path: str,
    start_time: float,
    end_time: float,
    output_path: str | None,
    output_dir: Path,
    overwrite: bool,
) -> Path:
    """Create an MP4 clip between the requested timestamps."""
    ffmpeg_path = require_command("ffmpeg")

    source_path = Path(input_path).expanduser().resolve()
    if not source_path.exists():
        raise FileNotFoundError(f"Input video does not exist: {source_path}")

    if end_time <= start_time:
        raise ValueError("End time must be greater than start time.")

    target_path = build_segment_output_path(
        input_path=source_path,
        output_path=output_path,
        output_dir=output_dir,
        start_time=start_time,
        end_time=end_time,
    )
    target_path.parent.mkdir(parents=True, exist_ok=True)

    command = [
        ffmpeg_path,
        "-y" if overwrite else "-n",
        "-i",
        str(source_path),
        "-ss",
        seconds_to_ffmpeg_time(start_time),
        "-to",
        seconds_to_ffmpeg_time(end_time),
        "-map",
        "0:v:0",
        "-map",
        "0:a?",
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-movflags",
        "+faststart",
        str(target_path),
    ]

    run_command(command)
    print(f"\nSegment saved to:\n{target_path}")
    return target_path


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line parser."""
    parser = argparse.ArgumentParser(
        description="Download YouTube videos and cut local clips for analysis."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    download_parser = subparsers.add_parser(
        "download",
        help="Download a YouTube video with yt-dlp.",
    )
    download_parser.add_argument("--url", required=True, help="YouTube video URL")
    download_parser.add_argument(
        "--resolution",
        default="best",
        type=parse_resolution,
        help="Target maximum height like 720, or 'best'.",
    )
    download_parser.add_argument(
        "--output_dir",
        default=str(DEFAULT_DOWNLOAD_DIR),
        help="Folder to save the downloaded video.",
    )
    download_parser.add_argument(
        "--filename_template",
        default=DEFAULT_OUTPUT_TEMPLATE,
        help="yt-dlp output template.",
    )
    download_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite an existing file if the same name is produced.",
    )
    download_parser.add_argument(
        "--cookies-from-browser",
        help="Pass browser cookies to yt-dlp, e.g. chrome, firefox, brave, chromium.",
    )
    download_parser.add_argument(
        "--cookies",
        help="Path to a cookies.txt file for yt-dlp.",
    )

    segment_parser = subparsers.add_parser(
        "segment",
        help="Cut a local video into a smaller MP4 clip with ffmpeg.",
    )
    segment_parser.add_argument(
        "--input",
        required=True,
        help="Path to the local source video.",
    )
    segment_parser.add_argument(
        "--start",
        required=True,
        type=parse_time_to_seconds,
        help="Clip start time: seconds, MM:SS, or HH:MM:SS[.mmm].",
    )
    segment_parser.add_argument(
        "--end",
        required=True,
        type=parse_time_to_seconds,
        help="Clip end time: seconds, MM:SS, or HH:MM:SS[.mmm].",
    )
    segment_parser.add_argument(
        "--output",
        help="Optional full output path for the clip.",
    )
    segment_parser.add_argument(
        "--output_dir",
        default=str(DEFAULT_SEGMENT_DIR),
        help="Folder for generated clips when --output is omitted.",
    )
    segment_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite the target clip if it already exists.",
    )

    return parser


def main() -> None:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "download":
        download_video(
            url=args.url,
            resolution=args.resolution,
            output_dir=Path(args.output_dir).expanduser().resolve(),
            filename_template=args.filename_template,
            overwrite=args.overwrite,
            cookies_from_browser=args.cookies_from_browser,
            cookies_file=args.cookies,
        )
        return

    if args.command == "segment":
        segment_video(
            input_path=args.input,
            start_time=args.start,
            end_time=args.end,
            output_path=args.output,
            output_dir=Path(args.output_dir).expanduser().resolve(),
            overwrite=args.overwrite,
        )
        return

    parser.error(f"Unsupported command: {args.command}")
