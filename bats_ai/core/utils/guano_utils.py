from __future__ import annotations

import contextlib
from datetime import datetime
from pathlib import Path
import re

from guano import GuanoFile


def parse_datetime(datetime_str: str) -> datetime | None:
    """Parse datetime string from GUANO metadata.

    Tries multiple formats:
    1. Custom format: '%Y%m%dT%H%M%S'
    2. ISO format

    Args:
        datetime_str: String representation of datetime

    Returns:
        datetime object or None if parsing fails
    """
    if datetime_str:
        try:
            # Try parsing using the custom format
            return datetime.strptime(datetime_str, "%Y%m%dT%H%M%S")
        except ValueError:
            try:
                # Try parsing using ISO format
                return datetime.fromisoformat(datetime_str)
            except ValueError:
                # If both formats fail, return None
                return None
    return None


def extract_metadata_from_filename(filename: str) -> dict:
    # Remove file extension if present
    filename_without_ext = Path(filename).stem

    regex_pattern = re.compile(r"^(\d+)_(.+)_(\d{8})_(\d{6})(?:_(.*))?$")
    match = regex_pattern.match(filename_without_ext)

    if not match:
        return {}

    # Extract matched groups
    cell_id = match.group(1)
    label_name = match.group(2)
    date_str = match.group(3)
    timestamp_str = match.group(4)

    metadata = {}

    # Extract grid cell ID
    if cell_id:
        with contextlib.suppress(ValueError):
            metadata["nabat_grid_cell_grts_id"] = str(int(cell_id))

    # Extract date and time
    if date_str and len(date_str) == 8 and timestamp_str and len(timestamp_str) == 6:
        try:
            # Convert YYYYMMDD to date components
            year = int(date_str[0:4])
            month = int(date_str[4:6])
            day = int(date_str[6:8])

            # Convert HHMMSS to time components
            hour = int(timestamp_str[0:2])
            minute = int(timestamp_str[2:4])
            second = int(timestamp_str[4:6])

            # Create datetime object
            activation_time = datetime(year, month, day, hour, minute, second)
            metadata["nabat_activation_start_time"] = activation_time
        except (ValueError, IndexError):
            pass

    # Extract quadrant if labelName is a valid quadrant
    if label_name and label_name.upper() in ["SW", "NE", "NW", "SE"]:
        metadata["quadrant"] = label_name.upper()

    return metadata


def extract_guano_metadata(file_path: str | Path, check_filename: bool = False) -> dict:
    """Extract GUANO metadata from a WAV file.

    Args:
        file_path: Path to the WAV file with GUANO metadata

    Returns:
        Dictionary containing extracted NABat metadata fields:
        - nabat_grid_cell_grts_id: str | None
        - nabat_latitude: float | None
        - nabat_longitude: float | None
        - nabat_site_name: str | None
        - nabat_activation_start_time: datetime | None
        - nabat_activation_end_time: datetime | None
        - nabat_software_type: str | None
        - nabat_species_list: list[str] | None
        - nabat_comments: str | None
        - nabat_detector_type: str | None
        - nabat_unusual_occurrences: str | None

    Raises:
        Exception: If the file cannot be read or processed
    """
    file_path = Path(file_path)

    # Read GUANO metadata from the file
    gfile = GuanoFile(str(file_path))

    # Extract required NABat fields
    nabat_fields = {
        "nabat_grid_cell_grts_id": gfile.get("NABat|Grid Cell GRTS ID", None),
        "nabat_latitude": gfile.get("NABat|Latitude", None),
        "nabat_longitude": gfile.get("NABat|Longitude", None),
        "nabat_site_name": gfile.get("NABat|Site Name", None),
    }

    # Fix longitude if positive (individuals don't put the - in the longitude)
    # GUANO metadata is supposed to be WGS84, but some individuals don't put the - in the longitude.
    if nabat_fields["nabat_longitude"]:
        try:
            longitude = float(nabat_fields["nabat_longitude"])
            if longitude > 0:
                nabat_fields["nabat_longitude"] = longitude * -1
            else:
                nabat_fields["nabat_longitude"] = longitude
        except (ValueError, TypeError):
            nabat_fields["nabat_longitude"] = None

    # Convert latitude to float if present
    if nabat_fields["nabat_latitude"]:
        try:
            nabat_fields["nabat_latitude"] = float(nabat_fields["nabat_latitude"])
        except (ValueError, TypeError):
            nabat_fields["nabat_latitude"] = None

    # Extract additional fields with conditionals
    additional_fields = {
        "nabat_activation_start_time": (
            parse_datetime(gfile.get("NABat|Activation start time", None))
            if "NABat|Activation start time" in gfile
            else None
        ),
        "nabat_activation_end_time": (
            parse_datetime(gfile.get("NABat|Activation end time", None))
            if "NABat|Activation end time" in gfile
            else None
        ),
        "nabat_software_type": gfile.get("NABat|Software type", None),
        "nabat_species_list": (
            [s.strip() for s in gfile.get("NABat|Species List", "").split(",") if s.strip()]
            if gfile.get("NABat|Species List", "")
            else None
        ),
        "nabat_comments": gfile.get("NABat|Comments", None),
        "nabat_detector_type": gfile.get("NABat|Detector type", None),
        "nabat_unusual_occurrences": gfile.get("NABat|Unusual occurrences", "") or None,
    }

    # Combine all extracted fields
    metadata = {**nabat_fields, **additional_fields}

    # If GUANO metadata is missing key fields, try to extract from filename
    # as fallback
    file_path_obj = Path(file_path)
    if check_filename:
        filename_metadata = extract_metadata_from_filename(file_path_obj.name)
        # Only fill in missing values from filename, don't overwrite existing
        # GUANO metadata
        if filename_metadata:
            # Fill in grid cell ID if missing
            grid_cell_id = filename_metadata.get("nabat_grid_cell_grts_id")
            if not metadata.get("nabat_grid_cell_grts_id") and grid_cell_id:
                metadata["nabat_grid_cell_grts_id"] = grid_cell_id

            # Fill in activation start time if missing
            activation_time = filename_metadata.get("nabat_activation_start_time")
            if not metadata.get("nabat_activation_start_time") and activation_time:
                metadata["nabat_activation_start_time"] = activation_time

            # Store quadrant if found (for potential use in getting location)
            if filename_metadata.get("quadrant"):
                metadata["quadrant"] = filename_metadata["quadrant"]

    return metadata
