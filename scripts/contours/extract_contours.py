# /// script
# requires-python = ">=3.9"
# dependencies = [
#   "click",
#   "numpy",
#   "opencv-python",
#   "scipy",
#   "scikit-image",
#   "svgwrite",
#   "batbot",
# ]
#
# [tool.uv.sources]
# batbot = { git = "https://github.com/Kitware/batbot" }
# ///
from __future__ import annotations

import colorsys
import json
import logging
from pathlib import Path

import click
import cv2
import numpy as np
from scipy.ndimage import gaussian_filter1d
from skimage import measure
from skimage.filters import threshold_multiotsu
import svgwrite

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

    for center, weight in zip(centers, counts, strict=False):
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

    if mode == "multi-otsu":
        try:
            return threshold_multiotsu(valid, classes=multi_otsu_classes).tolist()
        except Exception:
            pass

    if mode == "histogram":
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


# -----------------------------------------------------------------------------
# SVG + JSON
# -----------------------------------------------------------------------------


def save_svg(contours, image_shape, output_path: Path):
    h, w = image_shape[:2]
    dwg = svgwrite.Drawing(output_path, size=(w, h))

    for contour, _level in contours:
        pts = contour.tolist()
        if len(pts) < 3:
            continue

        d = [f"M {pts[0][0]},{pts[0][1]}"]
        d += [f"L {x},{y}" for x, y in pts[1:]]
        d.append("Z")

        dwg.add(
            dwg.path(
                d=" ".join(d),
                fill="none",
                stroke="black",
                stroke_width=1.0,
            )
        )

    dwg.save()


def save_svg_colored(contours, image_shape, output_path: Path):
    """Save contours to an SVG with stroke color varying by level."""
    if not contours:
        return

    # Compute color mapping based on contour levels
    levels = np.array([float(level) for _c, level in contours], dtype=float)
    min_level = float(levels.min())
    max_level = float(levels.max())
    level_span = max_level - min_level if max_level != min_level else 1.0

    def level_to_color(level: float) -> str:
        # Normalize to 0–1
        t = (float(level) - min_level) / level_span
        # Map 0–1 to a blue→cyan→green→yellow→red style gradient using HSV
        # Hue 240° (blue) → 0° (red)
        h = (240.0 - 240.0 * t) / 360.0
        r, g, b = colorsys.hsv_to_rgb(h, 1.0, 1.0)
        return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"

    h, w = image_shape[:2]
    dwg = svgwrite.Drawing(output_path, size=(w, h))

    for contour, level in contours:
        pts = contour.tolist()
        if len(pts) < 3:
            continue

        d = [f"M {pts[0][0]},{pts[0][1]}"]
        d += [f"L {x},{y}" for x, y in pts[1:]]
        d.append("Z")

        color = level_to_color(level)

        dwg.add(
            dwg.path(
                d=" ".join(d),
                fill="none",
                stroke=color,
                stroke_width=1.0,
            )
        )

    dwg.save()


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
        "source_image": image_path.name,
        "contour_count": len(contours),
        "contours": [
            {
                "level": float(level),
                "curve": contour.round(3).tolist(),
            }
            for contour, level in contours
        ],
    }
    if segment_index is not None:
        metadata["segment_index"] = segment_index
    if width is not None:
        metadata["width_px"] = width
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
    output_path: Path | None = None,
    debug: bool = False,
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
        raise RuntimeError(f"Could not read {image_path}")

    # Convert to grayscale first
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    if apply_noise_filter and noise_threshold is not None:
        print(f"Applying noise filter: {apply_noise_filter} with threshold: {noise_threshold}")
        # Create mask of pixels above threshold in original image
        # print out min and max of gray
        filtered = gray.copy()
        filtered[filtered < noise_threshold] = 0
        print(gray.mean())
        if debug:
            debug_path = output_path / "filtered.jpg" if output_path else None
            unfiltered_path = output_path / "unfiltered.jpg" if output_path else None
            if debug_path:
                cv2.imwrite(str(debug_path), filtered)
                print("Wrote filtered debug image:", debug_path)
            if unfiltered_path:
                cv2.imwrite(str(unfiltered_path), gray)
                print("Wrote unfiltered debug image:", unfiltered_path)

    data = gray

    levels = compute_auto_levels(
        data,
        mode=levels_mode,
        percentile_values=percentile_values,
        **level_kwargs,
    )

    print(levels)

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


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------


@click.command(context_settings={"show_default": True})
@click.argument(
    "input_path",
    type=click.Path(exists=True),
    metavar="IMAGE_OR_SPECTROGRAM_ASSETS",
)
@click.option("--out-dir", type=click.Path(), default="contours_out")
@click.option(
    "--levels-mode",
    type=click.Choice(["percentile", "histogram", "multi-otsu"]),
    default="percentile",
)
@click.option("--percentiles", multiple=True, default=(60, 70, 80, 90, 92, 94, 96, 98))
@click.option("--min-area", default=30.0)
@click.option("--smoothing-factor", default=0.08)
@click.option("--multi-otsu-classes", default=4)
@click.option("--hist-bins", default=512)
@click.option("--hist-sigma", default=2.0)
@click.option("--hist-variance-threshold", default=400.0)
@click.option("--hist-max-levels", default=5)
@click.option("-v", "--verbose", is_flag=True)
@click.option(
    "--debug-images",
    is_flag=True,
    help="Save debug images (filtered and unfiltered) to the output directory",
)
def main(input_path: str, out_dir, verbose, debug_images, **kwargs):
    logging.basicConfig(level=logging.INFO if verbose else logging.WARNING)

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    path = Path(input_path)

    # If the main argument is a spectrogram_assets JSON, use it to get
    # image paths and segment info. Otherwise treat it as an image path.
    all_segments_data = []

    if path.suffix.lower() == ".json":
        assets_path = path
        with assets_path.open() as f:
            assets_data = json.load(f)

        # noise_filter_threshold is stored as a percentage (0–100) of the
        # image's 8‑bit dynamic range; convert to a 0–255 pixel threshold.
        noise_threshold = None
        noise_threshold_percent = assets_data.get("noise_filter_threshold")
        if noise_threshold_percent is not None:
            noise_threshold = (float(noise_threshold_percent) / 100.0) * 255.0

        # Get compressed paths and widths/starts/stops
        compressed_data = assets_data.get("compressed", {})
        compressed_data.get("paths", [])
        mask_paths = compressed_data.get("masks", [])
        widths = compressed_data.get("widths", [])
        starts = compressed_data.get("starts", [])
        stops = compressed_data.get("stops", [])

        # Resolve paths relative to the assets file location
        assets_dir = assets_path.parent

        # Process each unique compressed image
        processed_images: set[Path] = set()
        for path_str in mask_paths:
            img_path = (assets_dir / path_str).resolve()
            if not img_path.exists():
                logger.warning("Image path does not exist: %s", img_path)
                continue

            # Only process each unique image once
            if img_path in processed_images:
                continue
            processed_images.add(img_path)

            # Extract all contours from the compressed image
            contours, shape = extract_contours(
                img_path,
                output_path=out_dir,
                debug=debug_images,
                levels_mode=kwargs["levels_mode"],
                percentile_values=kwargs["percentiles"],
                min_area=kwargs["min_area"],
                smoothing_factor=kwargs["smoothing_factor"],
                min_intensity=1.0,
                multi_otsu_classes=kwargs["multi_otsu_classes"],
                hist_bins=kwargs["hist_bins"],
                hist_sigma=kwargs["hist_sigma"],
                hist_variance_threshold=kwargs["hist_variance_threshold"],
                hist_max_levels=kwargs["hist_max_levels"],
                noise_threshold=noise_threshold,
                apply_noise_filter=False,
            )

            # Calculate segment boundaries based on widths
            segment_boundaries: list[tuple[float, float]] = []
            cumulative_x = 0.0
            for width in widths:
                segment_boundaries.append((cumulative_x, cumulative_x + width))
                cumulative_x += width

            # Split contours by segment
            segment_contours_list = filter_contours_by_segment(contours, segment_boundaries)

            # Build per-image JSON with segments array
            segments_output: list[dict] = []
            for seg_idx, seg_contours in enumerate(segment_contours_list):
                # freq_min/freq_max: min/max y
                # (frequency axis) over all contour points in this segment
                all_y = (
                    np.concatenate([c[:, 1] for c, _ in seg_contours])
                    if seg_contours
                    else np.array([])
                )
                freq_min = float(np.min(all_y).round(3)) if all_y.size else None
                freq_max = float(np.max(all_y).round(3)) if all_y.size else None

                segment_obj: dict = {
                    "segment_index": seg_idx,
                    "contour_count": len(seg_contours),
                    "freq_min": freq_min,
                    "freq_max": freq_max,
                    "contours": [
                        {
                            "level": float(level),
                            "curve": contour.round(3).tolist(),
                        }
                        for contour, level in seg_contours
                    ],
                }

                if seg_idx < len(widths):
                    segment_obj["width_px"] = widths[seg_idx]
                if seg_idx < len(starts):
                    segment_obj["start_ms"] = starts[seg_idx]
                if seg_idx < len(stops):
                    segment_obj["stop_ms"] = stops[seg_idx]

                segments_output.append(segment_obj)

            image_output = {
                "source_image": img_path.name,
                "segments": segments_output,
            }

            # Save per-image JSON with segments
            json_path = out_dir / f"{img_path.stem}.contours.json"
            with json_path.open("w") as f:
                json.dump(image_output, f, indent=2)

            logger.info(
                "Wrote per-image contour JSON with segments: %s (segments=%d)",
                json_path,
                len(segments_output),
            )

            # Also save the full image SVGs (all segments combined)
            svg_path = out_dir / f"{img_path.stem}.contours.svg"
            save_svg(contours, shape, svg_path)
            logger.info("Wrote full image SVG: %s", svg_path)

            svg_colored_path = out_dir / f"{img_path.stem}.contours.colored.svg"
            save_svg_colored(contours, shape, svg_colored_path)
            logger.info("Wrote full image colored SVG: %s", svg_colored_path)

            # Also save a colored SVG with the noise filter applied, if a
            # noise threshold is available from the spectrogram assets.
            if noise_threshold is not None:
                contours_nf, _shape_nf = extract_contours(
                    img_path,
                    debug=debug_images,
                    output_path=out_dir,
                    levels_mode=kwargs["levels_mode"],
                    percentile_values=kwargs["percentiles"],
                    min_area=kwargs["min_area"],
                    smoothing_factor=kwargs["smoothing_factor"],
                    min_intensity=1.0,
                    multi_otsu_classes=kwargs["multi_otsu_classes"],
                    hist_bins=kwargs["hist_bins"],
                    hist_sigma=kwargs["hist_sigma"],
                    hist_variance_threshold=kwargs["hist_variance_threshold"],
                    hist_max_levels=kwargs["hist_max_levels"],
                    noise_threshold=noise_threshold,
                    apply_noise_filter=True,
                )

                svg_colored_nf_path = out_dir / f"{img_path.stem}.contours.colored.noisefilter.svg"
                save_svg_colored(contours_nf, shape, svg_colored_nf_path)
                logger.info(
                    "Wrote full image colored SVG with noise filter: %s",
                    svg_colored_nf_path,
                )

            # Collect for combined output
            all_segments_data.extend(segments_output)

        # If we processed from spectrogram assets, also create a combined output
        # organized by segments/widths
        if all_segments_data:
            combined_output = {
                "source_spectrogram_assets": str(assets_path.name),
                "segments": sorted(all_segments_data, key=lambda x: x.get("segment_index", 0)),
                "total_segments": len(all_segments_data),
            }

            combined_json_path = out_dir / f"{assets_path.stem}.contours.combined.json"
            with combined_json_path.open("w") as f:
                json.dump(combined_output, f, indent=2)

            logger.info("Wrote combined output: %s", combined_json_path)

    else:
        # Use provided image directly (no segment splitting)
        img_path = path
        contours, shape = extract_contours(
            img_path,
            output_path=out_dir,
            debug=debug_images,
            levels_mode=kwargs["levels_mode"],
            percentile_values=kwargs["percentiles"],
            min_area=kwargs["min_area"],
            smoothing_factor=kwargs["smoothing_factor"],
            min_intensity=1.0,
            multi_otsu_classes=kwargs["multi_otsu_classes"],
            hist_bins=kwargs["hist_bins"],
            hist_sigma=kwargs["hist_sigma"],
            hist_variance_threshold=kwargs["hist_variance_threshold"],
            hist_max_levels=kwargs["hist_max_levels"],
        )

        # Optional debug images for single-image mode (no noise threshold
        # information is available here, so only an unfiltered debug image).
        if debug_images:
            img_color = cv2.imread(str(img_path))
            if img_color is None:
                logger.warning("Could not read image for debug output: %s", img_path)
            else:
                gray = cv2.cvtColor(img_color, cv2.COLOR_BGR2GRAY)
                blurred = cv2.GaussianBlur(gray, (15, 15), 3)

                unfiltered_path = out_dir / f"{img_path.stem}.unfiltered.jpg"
                cv2.imwrite(str(unfiltered_path), blurred)
                logger.info("Wrote unfiltered debug image: %s", unfiltered_path)

        svg_path = out_dir / f"{img_path.stem}.contours.svg"
        json_path = out_dir / f"{img_path.stem}.contours.json"

        save_svg(contours, shape, svg_path)

        svg_colored_path = out_dir / f"{img_path.stem}.contours.colored.svg"
        save_svg_colored(contours, shape, svg_colored_path)

        metadata = contours_to_metadata(contours, img_path)

        with json_path.open("w") as f:
            json.dump(metadata, f, indent=2)

        logger.info("Wrote %s and %s", svg_path, json_path)


if __name__ == "__main__":
    main()
