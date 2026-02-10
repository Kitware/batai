# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "batbot",
#     "click",
#     "opencv-python",
#     "pydantic",
#     "scipy",
#     "scikit-image",
# ]
#
# [tool.uv.sources]
# batbot = { git = "https://github.com/Kitware/batbot" }
# ///
"""Batch convert recordings to spectrogram assets with resume and progress.

Takes a folder of audio recordings and an output folder. For each recording,
runs the BatBot pipeline (same conversion as bats_ai.core.tasks.recording_compute_spectrogram),
saves all output images into a per-recording subfolder, and writes a results JSON
including the recording filename. Supports resume by skipping recordings that
already have results in the output folder.
"""
from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
import json
import logging
from pathlib import Path
import shutil
import tempfile
from typing import Any

import batbot
import click
import cv2
import numpy as np
from pydantic import BaseModel, ConfigDict, Field, field_validator
from scipy import interpolate
from scipy.ndimage import gaussian_filter1d
from skimage import measure
from skimage.filters import threshold_multiotsu

# Suppress batbot's logging so progress output stays clean
logging.getLogger('batbot').setLevel(logging.WARNING)


# ---------------------------------------------------------------------------
# BatBot metadata models (mirrors bats_ai.core.utils.batbot_metadata)
# ---------------------------------------------------------------------------


class SpectrogramMetadata(BaseModel):
    uncompressed_path: list[str] = Field(alias='uncompressed.path')
    compressed_path: list[str] = Field(alias='compressed.path')
    mask_path: list[str] = Field(alias='mask.path')


class UncompressedSize(BaseModel):
    width_px: int = Field(alias='width.px')
    height_px: int = Field(alias='height.px')


class CompressedSize(BaseModel):
    width_px: int = Field(alias='width.px')
    height_px: int = Field(alias='height.px')


class SizeMetadata(BaseModel):
    uncompressed: UncompressedSize
    compressed: CompressedSize


class FrequencyMetadata(BaseModel):
    min_hz: int = Field(alias='min.hz')
    max_hz: int = Field(alias='max.hz')
    pixels_hz: list[int] = Field(alias='pixels.hz')


class Segment(BaseModel):
    curve_hz_ms: list[list[float]] = Field(alias='curve.(hz,ms)')
    start_ms: float = Field(alias='segment start.ms')
    end_ms: float = Field(alias='segment end.ms')
    duration_ms: float = Field(alias='segment duration.ms')
    contour_start_ms: float = Field(alias='contour start.ms')
    contour_end_ms: float = Field(alias='contour end.ms')
    contour_duration_ms: float = Field(alias='contour duration.ms')
    threshold_amp: int = Field(alias='threshold.amp')
    peak_f_ms: float | None = Field(None, alias='peak f.ms')
    fc_ms: float | None = Field(None, alias='fc.ms')
    hi_fc_knee_ms: float | None = Field(None, alias='hi fc:knee.ms')
    lo_fc_heel_ms: float | None = Field(None, alias='lo fc:heel.ms')
    bandwidth_hz: int | None = Field(None, alias='bandwidth.hz')
    hi_f_hz: int | None = Field(None, alias='hi f.hz')
    lo_f_hz: int | None = Field(None, alias='lo f.hz')
    peak_f_hz: int | None = Field(None, alias='peak f.hz')
    fc_hz: int | None = Field(None, alias='fc.hz')
    hi_fc_knee_hz: int | None = Field(None, alias='hi fc:knee.hz')
    lo_fc_heel_hz: int | None = Field(None, alias='lo fc:heel.hz')
    harmonic_flag: bool = Field(False, alias='harmonic.flag')
    harmonic_peak_f_ms: float | None = Field(None, alias='harmonic peak f.ms')
    harmonic_peak_f_hz: int | None = Field(None, alias='harmonic peak f.hz')
    echo_flag: bool = Field(False, alias='echo.flag')
    echo_peak_f_ms: float | None = Field(None, alias='echo peak f.ms')
    echo_peak_f_hz: int | None = Field(None, alias='echo peak f.hz')
    slope_at_hi_fc_knee_khz_per_ms: float | None = Field(None, alias='slope@hi fc:knee.khz/ms')
    slope_at_fc_khz_per_ms: float | None = Field(None, alias='slope@fc.khz/ms')
    slope_at_low_fc_heel_khz_per_ms: float | None = Field(None, alias='slope@low fc:heel.khz/ms')
    slope_at_peak_khz_per_ms: float | None = Field(None, alias='slope@peak.khz/ms')
    slope_avg_khz_per_ms: float | None = Field(None, alias='slope[avg].khz/ms')
    slope_hi_avg_khz_per_ms: float | None = Field(None, alias='slope/hi[avg].khz/ms')
    slope_mid_avg_khz_per_ms: float | None = Field(None, alias='slope/mid[avg].khz/ms')
    slope_lo_avg_khz_per_ms: float | None = Field(None, alias='slope/lo[avg].khz/ms')
    slope_box_khz_per_ms: float | None = Field(None, alias='slope[box].khz/ms')
    slope_hi_box_khz_per_ms: float | None = Field(None, alias='slope/hi[box].khz/ms')
    slope_mid_box_khz_per_ms: float | None = Field(None, alias='slope/mid[box].khz/ms')
    slope_lo_box_khz_per_ms: float | None = Field(None, alias='slope/lo[box].khz/ms')

    @field_validator('curve_hz_ms', mode='before')
    @classmethod
    def validate_curve(cls, v: Any) -> list[list[float]]:
        if isinstance(v, list):
            return v
        return []


class BatbotMetadata(BaseModel):
    model_config = ConfigDict(validate_by_name=True, validate_by_alias=True)
    wav_path: str = Field(alias='wav.path')
    spectrogram: SpectrogramMetadata
    global_threshold_amp: int = Field(alias='global_threshold.amp')
    sr_hz: int = Field(alias='sr.hz')
    duration_ms: float = Field(alias='duration.ms')
    frequencies: FrequencyMetadata
    size: SizeMetadata
    segments: list[Segment]


class CompressedSpectrogramData(BaseModel):
    starts: list[float]
    stops: list[float]
    widths: list[float]


def parse_batbot_metadata(file_path: str | Path) -> BatbotMetadata:
    with open(file_path) as f:
        data = json.load(f)
    return BatbotMetadata(**data)


def convert_to_compressed_spectrogram_data(metadata: BatbotMetadata) -> CompressedSpectrogramData:
    duration_ms = metadata.duration_ms
    starts_ms: list[float] = []
    stops_ms: list[float] = []
    widths_px_compressed: list[float] = []
    segment_times: list[float] = []
    compressed_width = metadata.size.compressed.width_px
    total_time = 0.0

    if metadata.segments:
        for segment in metadata.segments:
            starts_ms.append(segment.start_ms)
            stops_ms.append(segment.end_ms)
            time = segment.end_ms - segment.start_ms
            segment_times.append(time)
            total_time += time
        for time in segment_times:
            width_px = (time / total_time) * compressed_width
            widths_px_compressed.append(width_px)
    else:
        starts_ms = [0]
        stops_ms = [duration_ms]
        widths_px_compressed = [compressed_width]

    return CompressedSpectrogramData(
        starts=starts_ms,
        stops=stops_ms,
        widths=widths_px_compressed,
    )


def convert_to_segment_data(metadata: BatbotMetadata) -> list[dict[str, Any]]:
    segment_data: list[dict[str, Any]] = []
    for index, segment in enumerate(metadata.segments):
        segment_data.append(
            {
                'segment_index': index,
                'curve_hz_ms': segment.curve_hz_ms,
                'char_freq_ms': segment.fc_ms,
                'char_freq_hz': segment.fc_hz,
                'knee_ms': segment.hi_fc_knee_ms,
                'knee_hz': segment.hi_fc_knee_hz,
                'heel_ms': segment.lo_fc_heel_ms,
                'heel_hz': segment.lo_fc_heel_hz,
            }
        )
    return segment_data


# ---------------------------------------------------------------------------
# Contour extraction (mirrors bats_ai.core.utils.contour_utils)
# ---------------------------------------------------------------------------


def _auto_histogram_levels(
    data: np.ndarray,
    bins: int = 512,
    smooth_sigma: float = 2.0,
    variance_threshold: float = 400.0,
    max_levels: int = 5,
) -> list[float]:
    if data.size == 0:
        return []
    hist, edges = np.histogram(data, bins=bins)
    counts = gaussian_filter1d(hist.astype(np.float64), sigma=smooth_sigma)
    centers = (edges[:-1] + edges[1:]) / 2.0
    mask = counts > 0
    counts = counts[mask]
    centers = centers[mask]
    if counts.size == 0:
        return []
    groups = []
    current_centers = []
    current_weights = []
    for center, weight in zip(centers, counts):
        weight = max(float(weight), 1e-9)
        current_centers.append(center)
        current_weights.append(weight)
        values = np.array(current_centers, dtype=np.float64)
        weights = np.array(current_weights, dtype=np.float64)
        mean = np.average(values, weights=weights)
        variance = np.average((values - mean) ** 2, weights=weights)
        if variance > variance_threshold and len(current_centers) > 1:
            last_center = current_centers.pop()
            last_weight = current_weights.pop()
            values = np.array(current_centers, dtype=np.float64)
            weights = np.array(current_weights, dtype=np.float64)
            if weights.sum() > 0:
                groups.append(np.average(values, weights=weights))
            current_centers = [last_center]
            current_weights = [last_weight]
    if current_centers:
        groups.append(np.average(current_centers, weights=current_weights))
    groups = sorted(set(groups))
    if len(groups) <= 1:
        return groups
    groups = groups[1:]
    if max_levels and len(groups) > max_levels:
        idx = np.linspace(0, len(groups) - 1, max_levels, dtype=int)
        groups = [groups[i] for i in idx]
    return groups


def _compute_auto_levels(
    data: np.ndarray,
    mode: str,
    percentile_values: list[float],
    multi_otsu_classes: int,
    min_intensity: float,
    hist_bins: int,
    hist_sigma: float,
    hist_variance_threshold: float,
    hist_max_levels: int,
) -> list[float]:
    valid = data[data >= min_intensity]
    if valid.size == 0:
        return []
    if mode == 'multi-otsu':
        try:
            return threshold_multiotsu(valid, classes=multi_otsu_classes).tolist()
        except Exception:
            pass
    if mode == 'histogram':
        return _auto_histogram_levels(
            valid,
            bins=hist_bins,
            smooth_sigma=hist_sigma,
            variance_threshold=hist_variance_threshold,
            max_levels=hist_max_levels,
        )
    return np.percentile(valid, sorted(percentile_values)).tolist()


def _polygon_area(points: np.ndarray) -> float:
    if len(points) < 3:
        return 0.0
    x, y = points[:, 0], points[:, 1]
    return 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def _smooth_contour_spline(contour: np.ndarray, smoothing_factor: float = 0.1) -> np.ndarray:
    if not np.array_equal(contour[0], contour[-1]):
        contour = np.vstack([contour, contour[0]])
    try:
        tck, _ = interpolate.splprep(
            [contour[:, 0], contour[:, 1]],
            s=len(contour) * smoothing_factor,
            per=True,
        )
        alpha = np.linspace(0, 1, max(len(contour), 100))
        x, y = interpolate.splev(alpha, tck)
        return np.column_stack([x, y])
    except Exception:
        return contour


def _filter_contours_by_segment(
    contours: list[tuple[np.ndarray, float]],
    segment_boundaries: list[tuple[float, float]],
) -> list[list[tuple[np.ndarray, float]]]:
    segment_contours: list[list[tuple[np.ndarray, float]]] = [[] for _ in segment_boundaries]
    for contour, level in contours:
        x_coords = contour[:, 0]
        min_x = np.min(x_coords)
        max_x = np.max(x_coords)
        center_x = np.mean(x_coords)
        for seg_idx, (seg_start, seg_end) in enumerate(segment_boundaries):
            if (seg_start <= center_x < seg_end) or (min_x < seg_end and max_x > seg_start):
                points_in_segment = np.sum((x_coords >= seg_start) & (x_coords < seg_end))
                total_points = len(x_coords)
                if points_in_segment / total_points >= 0.5 or (seg_start <= center_x < seg_end):
                    segment_contours[seg_idx].append((contour, level))
                    break
    return segment_contours


def _extract_contours(
    image_path: Path,
    *,
    levels_mode: str = 'percentile',
    percentile_values: list[float] = (60, 70, 80, 90, 92, 94, 96, 98),
    min_area: float = 30.0,
    smoothing_factor: float = 0.08,
    min_intensity: float = 1.0,
    multi_otsu_classes: int = 4,
    hist_bins: int = 512,
    hist_sigma: float = 2.0,
    hist_variance_threshold: float = 400.0,
    hist_max_levels: int = 5,
) -> tuple[list[tuple[np.ndarray, float]], tuple[int, ...]]:
    img = cv2.imread(str(image_path))
    if img is None:
        raise RuntimeError(f'Could not read {image_path}')
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (15, 15), 3)
    data = blurred
    levels = _compute_auto_levels(
        data,
        mode=levels_mode,
        percentile_values=percentile_values,
        multi_otsu_classes=multi_otsu_classes,
        min_intensity=min_intensity,
        hist_bins=hist_bins,
        hist_sigma=hist_sigma,
        hist_variance_threshold=hist_variance_threshold,
        hist_max_levels=hist_max_levels,
    )
    contours: list[tuple[np.ndarray, float]] = []
    for level in levels:
        for c in measure.find_contours(data, level):
            xy = c[:, ::-1]
            if not np.array_equal(xy[0], xy[-1]):
                xy = np.vstack([xy, xy[0]])
            if _polygon_area(xy) < min_area:
                continue
            smooth = _smooth_contour_spline(xy, smoothing_factor)
            contours.append((smooth, level))
    return sorted(contours, key=lambda x: x[1]), img.shape


def process_spectrogram_assets_for_contours(
    assets: dict[str, Any],
    levels_mode: str = 'percentile',
    percentile_values: list[float] = (60, 70, 80, 90, 92, 94, 96, 98),
    min_area: float = 30.0,
    smoothing_factor: float = 0.08,
    min_intensity: float = 1.0,
    multi_otsu_classes: int = 4,
    hist_bins: int = 512,
    hist_sigma: float = 2.0,
    hist_variance_threshold: float = 400.0,
    hist_max_levels: int = 5,
) -> dict[str, Any]:
    compressed_data = assets.get('compressed', {})
    mask_paths = compressed_data.get('masks', [])
    widths = compressed_data.get('widths', [])
    height = compressed_data.get('height', 0)
    starts = compressed_data.get('starts', [])
    global_freq_min = assets.get('freq_min', 0)
    global_freq_max = assets.get('freq_max', 0)
    stops = compressed_data.get('stops', [])
    all_segments_data: list[dict[str, Any]] = []
    processed_images: set[Path] = set()
    for path_str in mask_paths:
        img_path = Path(path_str).resolve()
        if not img_path.exists():
            continue
        if img_path in processed_images:
            continue
        processed_images.add(img_path)
        contours, shape = _extract_contours(
            img_path,
            levels_mode=levels_mode,
            percentile_values=percentile_values,
            min_area=min_area,
            smoothing_factor=smoothing_factor,
            min_intensity=min_intensity,
            multi_otsu_classes=multi_otsu_classes,
            hist_bins=hist_bins,
            hist_sigma=hist_sigma,
            hist_variance_threshold=hist_variance_threshold,
            hist_max_levels=hist_max_levels,
        )
        segment_boundaries: list[tuple[float, float]] = []
        cumulative_x = 0.0
        for w in widths:
            segment_boundaries.append((cumulative_x, cumulative_x + w))
            cumulative_x += w
        segment_contours_list = _filter_contours_by_segment(contours, segment_boundaries)
        segments_output: list[dict[str, Any]] = []
        width_to_this_seg = 0.0
        for seg_idx, seg_contours in enumerate(segment_contours_list):
            all_y = (
                np.concatenate([c[:, 1] for c, _ in seg_contours]) if seg_contours else np.array([])
            )
            freq_min = float(np.min(all_y).round(3)) if all_y.size else None
            freq_max = float(np.max(all_y).round(3)) if all_y.size else None
            start_time = starts[seg_idx] if seg_idx < len(starts) else 0
            stop_time = stops[seg_idx] if seg_idx < len(stops) else 0
            width = widths[seg_idx] if seg_idx < len(widths) else 0
            time_per_pixel = (stop_time - start_time) / width if width else 0
            mhz_per_pixel = (global_freq_max - global_freq_min) / height if height else 0
            transformed_contours = []
            for contour, level in seg_contours:
                new_curve = [
                    [
                        (point[0] - width_to_this_seg) * time_per_pixel + start_time,
                        global_freq_max - (point[1] * mhz_per_pixel),
                    ]
                    for point in contour
                ]
                transformed_contours.append(
                    {
                        'level': float(level),
                        'curve': new_curve,
                        'index': seg_idx,
                    }
                )
            segment_obj: dict[str, Any] = {
                'segment_index': seg_idx,
                'contour_count': len(seg_contours),
                'freq_min': freq_min,
                'freq_max': freq_max,
                'contours': transformed_contours,
            }
            if seg_idx < len(widths):
                segment_obj['width_px'] = widths[seg_idx]
            if seg_idx < len(starts):
                segment_obj['start_ms'] = starts[seg_idx]
            if seg_idx < len(stops):
                segment_obj['stop_ms'] = stops[seg_idx]
            width_to_this_seg += widths[seg_idx] if seg_idx < len(widths) else 0
            segments_output.append(segment_obj)
        all_segments_data.extend(segments_output)
    return {
        'segments': sorted(all_segments_data, key=lambda x: x.get('segment_index', 0)),
        'total_segments': len(all_segments_data),
    }


def generate_spectrogram_assets(recording_path: str, output_folder: str) -> dict[str, Any]:
    """Run BatBot pipeline and return result dict (paths are under output_folder)."""
    batbot.pipeline(recording_path, output_folder=output_folder)
    metadata_file = Path(recording_path).with_suffix('.metadata.json').name
    metadata_path = Path(output_folder) / metadata_file
    metadata = parse_batbot_metadata(metadata_path)

    uncompressed_paths = [str(p) for p in metadata.spectrogram.uncompressed_path]
    compressed_paths = [str(p) for p in metadata.spectrogram.compressed_path]
    mask_paths = [str(p) for p in metadata.spectrogram.mask_path]

    compressed_metadata = convert_to_compressed_spectrogram_data(metadata)
    segment_curve_data = convert_to_segment_data(metadata)

    return {
        'duration': metadata.duration_ms,
        'freq_min': metadata.frequencies.min_hz,
        'freq_max': metadata.frequencies.max_hz,
        'normal': {
            'paths': uncompressed_paths,
            'width': metadata.size.uncompressed.width_px,
            'height': metadata.size.uncompressed.height_px,
        },
        'compressed': {
            'paths': compressed_paths,
            'masks': mask_paths,
            'width': metadata.size.compressed.width_px,
            'height': metadata.size.compressed.height_px,
            'widths': compressed_metadata.widths,
            'starts': compressed_metadata.starts,
            'stops': compressed_metadata.stops,
            'segments': segment_curve_data,
        },
    }


# ---------------------------------------------------------------------------
# Batch conversion with resume
# ---------------------------------------------------------------------------

RESULTS_FILENAME = 'results.json'
DEFAULT_AUDIO_GLOB = '*.wav'


def _result_path(output_folder: Path, recording_stem: str) -> Path:
    return output_folder / recording_stem / RESULTS_FILENAME


def _already_done(output_folder: Path, recording_stem: str) -> bool:
    return _result_path(output_folder, recording_stem).exists()


def _copy_batbot_output(tmpdir: Path, out_subdir: Path) -> None:
    """Copy every file batbot wrote in tmpdir into out_subdir."""
    out_subdir.mkdir(parents=True, exist_ok=True)
    for f in tmpdir.iterdir():
        if f.is_file():
            shutil.copy2(f, out_subdir / f.name)


def _result_with_basename_paths(result: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of result with all paths replaced by basenames."""
    out = json.loads(json.dumps(result))
    for key in ('normal', 'compressed'):
        if key not in out:
            continue
        for path_key in ('paths', 'masks'):
            if path_key in out[key] and out[key][path_key]:
                out[key][path_key] = [Path(p).name for p in out[key][path_key]]
    return out


def process_one(
    recording_path: Path,
    output_folder: Path,
) -> dict[str, Any]:
    """Convert one recording and save images + results.json. Returns result for this recording."""
    stem = recording_path.stem
    out_subdir = output_folder / stem
    out_subdir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_p = Path(tmpdir)
        temp_audio = tmpdir_p / recording_path.name
        shutil.copy2(recording_path, temp_audio)

        result = generate_spectrogram_assets(str(temp_audio), str(tmpdir_p))

        # Resolve paths so contour extraction can read mask images
        for path_key in ('paths', 'masks'):
            resolved = []
            for p in result['compressed'].get(path_key, []):
                pp = Path(p)
                if not pp.is_absolute():
                    pp = tmpdir_p / pp.name
                resolved.append(str(pp.resolve()))
            result['compressed'][path_key] = resolved

        contours_data = process_spectrogram_assets_for_contours(result)
        result['compressed']['contours'] = contours_data

        _copy_batbot_output(tmpdir_p, out_subdir)

    result_for_json = _result_with_basename_paths(result)
    payload = {
        'recording_filename': recording_path.name,
        'recording_stem': stem,
        **result_for_json,
    }
    results_path = _result_path(output_folder, stem)
    with open(results_path, 'w') as f:
        json.dump(payload, f, indent=2)

    return payload


def gather_recordings(input_folder: Path, pattern: str) -> list[Path]:
    return sorted(input_folder.glob(pattern))


@click.command()
@click.argument(
    'input_folder',
    type=click.Path(exists=True, file_okay=False, path_type=Path),
)
@click.argument(
    'output_folder',
    type=click.Path(path_type=Path),
)
@click.option(
    '--pattern',
    default=DEFAULT_AUDIO_GLOB,
    show_default=True,
    help='Glob pattern for audio files (e.g. "*.wav", "*.WAV").',
)
@click.option(
    '--no-resume',
    is_flag=True,
    help='Ignore existing results and reprocess all recordings.',
)
@click.option(
    '-j',
    '--jobs',
    default=1,
    type=click.IntRange(min=1),
    show_default=True,
    help='Number of recordings to process in parallel.',
)
def main(
    input_folder: Path,
    output_folder: Path,
    pattern: str,
    no_resume: bool,
    jobs: int,
) -> None:
    """Convert a folder of recordings to spectrogram assets with optional resume.

    For each recording in INPUT_FOLDER (matching --pattern), runs the BatBot
    pipeline, writes images and a results JSON (including recording filename)
    into OUTPUT_FOLDER/<recording_stem>/. If OUTPUT_FOLDER/<recording_stem>/results.json
    already exists, that recording is skipped (resume). Use --no-resume to reprocess all.
    Use --jobs N to process N recordings at a time.
    """
    recordings = gather_recordings(input_folder, pattern)
    if not recordings:
        click.echo(f'No files matching "{pattern}" in {input_folder}', err=True)
        raise SystemExit(1)

    output_folder.mkdir(parents=True, exist_ok=True)
    to_do = [r for r in recordings if no_resume or not _already_done(output_folder, r.stem)]
    skipped = len(recordings) - len(to_do)

    click.echo(
        f'Recordings found: {len(recordings)}. \
        To process: {len(to_do)}. \
        Skipped (resume): {skipped}. \
        Jobs: {jobs}.'
    )

    if jobs == 1:
        with click.progressbar(
            to_do,
            label='Converting',
            show_pos=True,
            show_percent=True,
        ) as bar:
            for recording_path in bar:
                try:
                    process_one(recording_path, output_folder)
                except Exception as e:
                    click.echo(f'\nError processing {recording_path}: {e}', err=True)
                    raise
    else:
        failed: list[tuple[Path, BaseException]] = []
        with click.progressbar(
            length=len(to_do),
            label='Converting',
            show_pos=True,
            show_percent=True,
        ) as bar:
            with ProcessPoolExecutor(max_workers=jobs) as executor:
                future_to_path = {
                    executor.submit(process_one, recording_path, output_folder): recording_path
                    for recording_path in to_do
                }
                for future in as_completed(future_to_path):
                    recording_path = future_to_path[future]
                    try:
                        future.result()
                    except Exception as e:
                        failed.append((recording_path, e))
                    bar.update(1)
        if failed:
            for path, e in failed:
                click.echo(f'Error processing {path}: {e}', err=True)
            raise SystemExit(1)

    click.echo(f'Done. Processed {len(to_do)} recordings into {output_folder}.')


if __name__ == '__main__':
    main()
