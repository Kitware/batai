from __future__ import annotations

import json
import logging
from pathlib import Path

from django.conf import settings
from django.contrib.gis.geos import GEOSGeometry
from django.core.management.base import BaseCommand, CommandError

from bats_ai.core.models import Species, SpeciesRange

logger = logging.getLogger(__name__)


DEFAULT_GEOJSON = settings.BASE_DIR / "bats_ai" / "core" / "data" / "species.geojson"


class Command(BaseCommand):
    help = (
        "Load species range polygons from a GeoJSON FeatureCollection. "
        "Each feature's properties.name must match an existing Species.species_code."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "geojson_path",
            nargs="?",
            type=str,
            default=None,
            help=f"Path to GeoJSON file (default: {DEFAULT_GEOJSON})",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete all SpeciesRange rows before loading.",
        )

    def handle(self, *args, **options):
        path = Path(options["geojson_path"] or DEFAULT_GEOJSON).resolve()
        if not path.is_file():
            raise CommandError(f"GeoJSON file not found: {path}")

        raw = path.read_text(encoding="utf-8")
        try:
            doc = json.loads(raw)
        except json.JSONDecodeError as e:
            raise CommandError(f"Invalid JSON: {e}") from e

        if doc.get("type") != "FeatureCollection":
            raise CommandError(
                'Expected a GeoJSON FeatureCollection ("type": "FeatureCollection").'
            )

        features = doc.get("features") or []
        if not features:
            raise CommandError("No features in FeatureCollection.")

        clear = options["clear"]

        matched = 0
        skipped_unknown = 0
        errors: list[str] = []

        if clear:
            deleted, _ = SpeciesRange.objects.all().delete()
            self.stdout.write(
                self.style.WARNING(f"Cleared {deleted} existing species range row(s).")
            )

        for i, feature in enumerate(features):
            props = feature.get("properties") or {}
            code = props.get("name")
            if not code or not str(code).strip():
                errors.append(f"Feature {i}: missing properties.name")
                continue
            code = str(code).strip().upper()

            geom_json = feature.get("geometry")
            if not geom_json:
                errors.append(f"Feature {i} ({code}): missing geometry")
                continue

            try:
                geom = GEOSGeometry(json.dumps(geom_json))
            except Exception as e:
                errors.append(f"Feature {i} ({code}): invalid geometry: {e}")
                continue

            if geom.srid in (None, 0):
                geom.srid = 4326
            elif geom.srid != 4326:
                geom.transform(4326)

            species = Species.objects.filter(species_code__iexact=code).first()
            if species is None:
                skipped_unknown += 1
                warning_str = f"No Species with species_code matching {code} (feature {i})"
                logger.warning(warning_str)
                errors.append(warning_str)
                continue

            fid = props.get("id")
            source_feature_id = str(fid) if fid is not None else ""

            SpeciesRange.objects.update_or_create(
                species=species,
                defaults={
                    "geom": geom,
                    "source_feature_id": source_feature_id,
                },
            )
            matched += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Processed {len(features)} feature(s): {matched} matched"
                + (f", {skipped_unknown} unknown species code(s)" if skipped_unknown else "")
            )
        )
        for msg in errors:
            self.stdout.write(self.style.ERROR(msg))
