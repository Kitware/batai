import logging
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from scipy.ndimage import gaussian_filter1d
from skimage import measure
from skimage.filters import threshold_multiotsu

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Level selection
# -----------------------------------------------------------------------------


def auto_histogram_levels(
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


def compute_auto_levels(
    data: np.ndarray,
    mode: str,
    percentile_values,
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
        return auto_histogram_levels(
            valid,
            bins=hist_bins,
            smooth_sigma=hist_sigma,
            variance_threshold=hist_variance_threshold,
            max_levels=hist_max_levels,
        )

    return np.percentile(valid, sorted(percentile_values)).tolist()


# -----------------------------------------------------------------------------
# Geometry
# -----------------------------------------------------------------------------


def polygon_area(points: np.ndarray) -> float:
    if len(points) < 3:
        return 0.0
    x, y = points[:, 0], points[:, 1]
    return 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def smooth_contour_spline(contour: np.ndarray, smoothing_factor=0.1) -> np.ndarray:
    from scipy import interpolate

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


def filter_contours_by_segment(
    contours, segment_boundaries: list[tuple[float, float]]
) -> list[list[tuple[np.ndarray, float]]]:
    """Filter contours by segment boundaries based on x-coordinates.

    Args:
        contours: List of (contour, level) tuples
        segment_boundaries: List of (start_x, end_x) tuples for each segment

    Returns:
        List of lists, where each inner list contains contours for that segment
    """
    segment_contours: list[list[tuple[np.ndarray, float]]] = [[] for _ in segment_boundaries]

    for contour, level in contours:
        # Get x-coordinates of all points in the contour
        x_coords = contour[:, 0]
        min_x = np.min(x_coords)
        max_x = np.max(x_coords)
        center_x = np.mean(x_coords)

        # Find which segment(s) this contour belongs to
        # A contour belongs to a segment if its center or a
        # significant portion is within the segment
        for seg_idx, (seg_start, seg_end) in enumerate(segment_boundaries):
            # Check if contour overlaps with this segment
            # Consider it part of the segment if center is within or significant overlap
            if (seg_start <= center_x < seg_end) or (min_x < seg_end and max_x > seg_start):
                # Check if most of the contour is within this segment
                points_in_segment = np.sum((x_coords >= seg_start) & (x_coords < seg_end))
                total_points = len(x_coords)

                # If at least 50% of points are in this segment, or center is in segment
                if points_in_segment / total_points >= 0.5 or (seg_start <= center_x < seg_end):
                    segment_contours[seg_idx].append((contour, level))
                    break  # Assign to first matching segment to avoid duplicates

    return segment_contours


def contours_to_metadata(
    contours, image_path: Path, segment_index: int | None = None, width: float | None = None
):
    metadata = {
        'source_image': image_path.name,
        'contour_count': len(contours),
        'contours': [
            {
                'level': float(level),
                'curve': contour.round(3).tolist(),
            }
            for contour, level in contours
        ],
    }
    if segment_index is not None:
        metadata['segment_index'] = segment_index
    if width is not None:
        metadata['width_px'] = width
    return metadata


def apply_transparency_mask(mat, threshold_percent):
    t = np.clip(threshold_percent, 0, 100) / 100.0

    if t <= 0:
        return np.ones_like(mat, dtype=np.uint8)
    if t >= 1:
        return np.zeros_like(mat, dtype=np.uint8)

    return (mat > t).astype(np.uint8)


# -----------------------------------------------------------------------------
# Core extraction
# -----------------------------------------------------------------------------


def extract_contours(
    image_path: Path,
    *,
    levels_mode: str,
    percentile_values,
    min_area: float,
    smoothing_factor: float,
    noise_threshold: float | None = None,
    apply_noise_filter: bool = False,
    **level_kwargs,
):
    img = cv2.imread(str(image_path))
    if img is None:
        raise RuntimeError(f'Could not read {image_path}')

    # Convert to grayscale first
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    if apply_noise_filter and noise_threshold is not None:
        # Create mask of pixels above threshold in original image
        # print out min and max of gray
        gray = np.where(gray < noise_threshold, 0, gray)
        blurred = cv2.GaussianBlur(gray, (15, 15), 3)
    else:
        blurred = cv2.GaussianBlur(gray, (15, 15), 3)
    data = blurred

    levels = compute_auto_levels(
        data,
        mode=levels_mode,
        percentile_values=percentile_values,
        **level_kwargs,
    )

    contours = []
    for level in levels:
        for c in measure.find_contours(data, level):
            xy = c[:, ::-1]
            if not np.array_equal(xy[0], xy[-1]):
                xy = np.vstack([xy, xy[0]])

            if polygon_area(xy) < min_area:
                continue

            smooth = smooth_contour_spline(xy, smoothing_factor)
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
    noise_threshold: float | None = None,
    apply_noise_filter: bool = False,
):
    compressed_data = assets.get('compressed', {})
    compressed_data.get('paths', [])
    mask_paths = compressed_data.get('masks', [])
    widths = compressed_data.get('widths', [])
    height = compressed_data.get('height', 0)
    starts = compressed_data.get('starts', [])
    global_freq_min = assets.get('freq_min', 0)
    global_freq_max = assets.get('freq_max', 0)
    stops = compressed_data.get('stops', [])
    all_segments_data = []

    processed_images: set[Path] = set()
    for path_str in mask_paths:
        img_path = Path(path_str).resolve()
        if not img_path.exists():
            logger.warning('Image path does not exist: %s', img_path)
            continue

        # Only process each unique image once
        if img_path in processed_images:
            continue
        processed_images.add(img_path)

        # Extract all contours from the compressed image
        contours, shape = extract_contours(
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
            noise_threshold=noise_threshold,
            apply_noise_filter=False,
        )
        segment_boundaries: list[tuple[float, float]] = []
        cumulative_x = 0.0
        for width in widths:
            segment_boundaries.append((cumulative_x, cumulative_x + width))
            cumulative_x += width

        # Split contours by segment
        segment_contours_list = filter_contours_by_segment(contours, segment_boundaries)

        # Build per-image JSON with segments array
        segments_output: list[dict] = []
        width_to_this_seg = 0
        for seg_idx, seg_contours in enumerate(segment_contours_list):
            # freq_min/freq_max: min/max y (frequency axis) over all contour points in this segment
            all_y = (
                np.concatenate([c[:, 1] for c, _ in seg_contours]) if seg_contours else np.array([])
            )
            freq_min = float(np.min(all_y).round(3)) if all_y.size else None
            freq_max = float(np.max(all_y).round(3)) if all_y.size else None
            start_time = starts[seg_idx]
            stop_time = stops[seg_idx]
            width = widths[seg_idx]
            time_per_pixel = (stop_time - start_time) / width
            mhz_per_pixel = (global_freq_max - global_freq_min) / height
            transformed_contours = []
            contour_index = 0
            for contour, level in seg_contours:
                # contour is (N, 2): each row is one point [x, y]
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
                contour_index += 1
            segment_obj: dict = {
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

            width_to_this_seg += widths[seg_idx]
            segments_output.append(segment_obj)
        # Collect for combined output
        all_segments_data.extend(segments_output)

    # If we processed from spectrogram assets, also create a combined output
    # organized by segments/widths
    combined_output = {
        'segments': sorted(all_segments_data, key=lambda x: x.get('segment_index', 0)),
        'total_segments': len(all_segments_data),
    }

    return combined_output
