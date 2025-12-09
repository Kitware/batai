import logging

import cv2
import numpy as np
from scipy.ndimage import gaussian_filter1d
from skimage import measure
from skimage.filters import threshold_multiotsu
import svgwrite

logger = logging.getLogger(__name__)


# This function computes the contour levels based on the selected mode.
def auto_histogram_levels(
    data: np.ndarray,
    bins: int = 512,
    smooth_sigma: float = 2.0,
    variance_threshold: float = 400.0,
    max_levels: int = 5,
) -> list[float]:
    """Select intensity levels by grouping histogram bins until variance exceeds a threshold."""
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
                grouped_mean = np.average(values, weights=weights)
                groups.append(grouped_mean)

            current_centers = [last_center]
            current_weights = [last_weight]

    if current_centers:
        values = np.array(current_centers, dtype=np.float64)
        weights = np.array(current_weights, dtype=np.float64)
        grouped_mean = np.average(values, weights=weights)
        groups.append(grouped_mean)

    groups = sorted(set(groups))

    if len(groups) <= 1:
        return groups

    groups = groups[1:]

    if max_levels is not None and len(groups) > max_levels:
        indices = np.linspace(0, len(groups) - 1, max_levels, dtype=int)
        groups = [groups[i] for i in indices]

    def subdivide_high_end(levels: list[float]) -> list[float]:
        if len(levels) < 2:
            return levels
        gaps = np.diff(levels)
        largest_gap_idx = int(np.argmax(gaps))
        remaining_slots = (
            max(0, max_levels - len(levels)) if max_levels is not None else len(levels)
        )
        subdivisions = min(remaining_slots, 2) if remaining_slots > 0 else 0
        subdivided = []
        if subdivisions > 0:
            if largest_gap_idx == len(levels) - 1:
                low = levels[-2]
                high = levels[-1]
                stride = (high - low) / (subdivisions + 1)
                subdivided = [low + stride * (i + 1) for i in range(subdivisions)]
                levels = levels[:-1] + subdivided + [levels[-1]]
        return sorted(levels)

    return subdivide_high_end(groups)


def compute_auto_levels(
    data: np.ndarray,
    mode: str,
    percentile_values,
    multi_otsu_classes: int,
    min_intensity: float,
    hist_bins: int = 512,
    hist_sigma: float = 2.0,
    hist_variance_threshold: float = 400.0,
    hist_max_levels: int = 5,
) -> list[float]:
    """Compute contour levels based on selected mode."""
    percentile_values = list(percentile_values)
    percentile_values.sort()

    valid = data[data >= min_intensity]
    if valid.size == 0:
        return []

    if mode == 'multi-otsu':
        try:
            thresholds = threshold_multiotsu(valid, classes=multi_otsu_classes)
            return thresholds.tolist()
        except Exception:
            # Fallback to simple percentiles if multi-otsu fails
            if len(percentile_values) == 0:
                return []
            return np.percentile(valid, percentile_values).tolist()
    elif mode == 'histogram':
        return auto_histogram_levels(
            valid,
            bins=hist_bins,
            smooth_sigma=hist_sigma,
            variance_threshold=hist_variance_threshold,
            max_levels=hist_max_levels,
        )
    else:  # percentile mode
        if len(percentile_values) == 0:
            return []
        return np.percentile(valid, percentile_values).tolist()


# This function computes the area of a polygon.
def polygon_area(points: np.ndarray) -> float:
    """Return absolute area of a closed polygon given as Nx2 array."""
    if len(points) < 3:
        return 0.0
    x = points[:, 0]
    y = points[:, 1]
    return 0.5 * np.abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


# This function smooths a contour using spline interpolation.
def smooth_contour_spline(contour, smoothing_factor=0.1):
    """Smooth contour using spline interpolation"""
    # Reshape contour
    if contour.ndim != 2 or contour.shape[1] != 2:
        if contour.size % 2 == 0:
            contour = contour.reshape(-1, 2)
        else:
            logger.warning(f'Invalid contour shape: {contour.shape}')
    # contour = contour.reshape(-1, 2)

    # Close the contour by adding first point at end
    if not np.array_equal(contour[0], contour[-1]):
        contour = np.vstack([contour, contour[0]])

    # Calculate cumulative distance along contour
    distances = np.cumsum(np.sqrt(np.sum(np.diff(contour, axis=0) ** 2, axis=1)))
    distances = np.insert(distances, 0, 0)

    # Interpolate using splines
    from scipy import interpolate

    # Create periodic spline
    num_points = max(len(contour), 100)
    alpha = np.linspace(0, 1, num_points)

    # Fit spline
    try:
        tck, u = interpolate.splprep(
            [contour[:, 0], contour[:, 1]], s=len(contour) * smoothing_factor, per=True
        )
        x_smooth, y_smooth = interpolate.splev(alpha, tck)
        smooth_contour = np.column_stack([x_smooth, y_smooth])
    except Exception as e:
        # Fallback to simple smoothing if spline fails
        logger.info(f'Spline fitting failed {e}. Falling back to simple smoothing.')
        smooth_contour = contour

    return smooth_contour


# This function saves the contours to an SVG file.
def save_contours_to_svg(
    contours_with_levels,
    output_path,
    image_shape,
    reference_image=None,
    fill_opacity=0.6,
    stroke_opacity=0.9,
    stroke_width=1.0,
    draw_stroke=True,
    sample_shrink_px=3,
    sample_radius=5,
):
    """Save contours to SVG with filled shapes (optionally matching image colors)."""
    height, width = image_shape[:2]
    dwg = svgwrite.Drawing(output_path, size=(width, height))

    # Default palette if no image supplied
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#F7B267', '#CDB4DB']

    if reference_image is not None and reference_image.shape[:2] != (height, width):
        raise ValueError("reference_image shape does not match image_shape")

    def color_from_image(points, fallback_color):
        if reference_image is None:
            return fallback_color
        polygon = np.round(points).astype(np.int32)
        polygon[:, 0] = np.clip(polygon[:, 0], 0, width - 1)
        polygon[:, 1] = np.clip(polygon[:, 1], 0, height - 1)
        mask = np.zeros((height, width), dtype=np.uint8)
        cv2.fillPoly(mask, [polygon], (255,))

        eroded = mask.copy()
        if sample_shrink_px > 0:
            kernel_size = sample_shrink_px * 2 + 1
            kernel = np.ones((kernel_size, kernel_size), dtype=np.uint8)
            eroded = cv2.erode(mask, kernel, iterations=1)
            if not np.count_nonzero(eroded):
                eroded = mask

        dist = cv2.distanceTransform(eroded, cv2.DIST_L2, 5)
        _, max_val, _, max_loc = cv2.minMaxLoc(dist)

        if max_val <= 0:
            region = reference_image[mask == 255]
            if region.size == 0:
                return fallback_color
            mean_bgr = region.mean(axis=0)
        else:
            cx, cy = max_loc[0], max_loc[1]
            x0 = max(cx - sample_radius, 0)
            x1 = min(cx + sample_radius + 1, width)
            y0 = max(cy - sample_radius, 0)
            y1 = min(cy + sample_radius + 1, height)
            patch = reference_image[y0:y1, x0:x1]
            patch_mask = eroded[y0:y1, x0:x1]
            region = patch[patch_mask > 0]
            if region.size == 0:
                region = reference_image[mask == 255]
            mean_bgr = region.mean(axis=0)

        r, g, b = [int(np.clip(c, 0, 255)) for c in mean_bgr[::-1]]
        return f"#{r:02X}{g:02X}{b:02X}"

    # Draw lower levels first so higher ones sit on top
    contours_with_levels_sorted = sorted(contours_with_levels, key=lambda x: x[1])
    logger.info(f'Sorted contours length: {len(contours_with_levels_sorted)}')

    for i, (contour, level) in enumerate(contours_with_levels_sorted):
        # logger.info(f'Attempting to add path for level {level}')
        pts = contour.tolist()
        if len(pts) < 3:
            continue

        # Build a simple closed path (straight segments). Beziers look nice for strokes
        # but can self-intersect when filled; straight segments are safer for fills.
        d = [f"M {pts[0][0]},{pts[0][1]}"]
        for j in range(1, len(pts)):
            d.append(f"L {pts[j][0]},{pts[j][1]}")
        d.append("Z")
        path_data = " ".join(d)

        fallback = colors[i % len(colors)]
        fill_color = color_from_image(np.array(pts), fallback)

        path = dwg.path(
            d=path_data,
            fill=fill_color,
            fill_opacity=fill_opacity,
            stroke=fill_color if draw_stroke else 'none',
            stroke_opacity=stroke_opacity,
            stroke_width=stroke_width,
        )

        # Helps when there are holes; keeps visual sane without hierarchy bookkeeping
        path.update({'fill-rule': 'evenodd'})

        dwg.add(path)

    dwg.save()
    logger.info(f"Saved smooth filled contours to {output_path}")


def extract_marching_squares_contours(
    image_path,
    output_path='marching_squares.svg',
    levels=None,
    gaussian_kernel=(15, 15),
    gaussian_sigma=3,
    min_area=500,
    smoothing_factor=0.08,
    levels_mode='percentile',
    percentile_values=(90, 95, 98),
    min_intensity=1.0,
    multi_otsu_classes=4,
    hist_bins=512,
    hist_sigma=2.0,
    hist_variance_threshold=400.0,
    hist_max_levels=5,
    save_to_file=True,
    verbose=True,
):
    """Extract contours using marching squares (skimage.find_contours)."""
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    blurred = cv2.GaussianBlur(gray, gaussian_kernel, gaussian_sigma)

    if levels is None:
        mask = blurred > 0
        if not np.any(mask):
            return []
        levels = compute_auto_levels(
            blurred[mask],
            mode=levels_mode,
            percentile_values=percentile_values,
            multi_otsu_classes=multi_otsu_classes,
            min_intensity=min_intensity,
            hist_bins=hist_bins,
            hist_sigma=hist_sigma,
            hist_variance_threshold=hist_variance_threshold,
            hist_max_levels=hist_max_levels,
        )
        if verbose:
            logger.info(f"Marching squares levels ({levels_mode}): {levels}")

    marching_contours = []

    for level in levels:
        raw_contours = measure.find_contours(blurred, level=level)
        for contour in raw_contours:
            # skimage returns (row, col); flip to (x, y)
            contour_xy = contour[:, ::-1]
            if not np.array_equal(contour_xy[0], contour_xy[-1]):
                contour_xy = np.vstack([contour_xy, contour_xy[0]])

            if polygon_area(contour_xy) < min_area:
                continue

            smooth = smooth_contour_spline(contour_xy, smoothing_factor=smoothing_factor)
            marching_contours.append((smooth, level))

    if marching_contours and save_to_file:
        logger.info(f'Saving contours to {output_path}')
        save_contours_to_svg(marching_contours, output_path, img.shape, reference_image=img)

    return sorted(marching_contours, key=lambda x: x[1], reverse=True)
