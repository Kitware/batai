import logging
from pathlib import Path

from django.contrib.auth.models import User
from django.contrib.gis.geos import Point
from django.core.files import File
from django.core.management.base import BaseCommand
from django.utils import timezone

from bats_ai.core.models import Recording
from bats_ai.core.tasks.tasks import recording_compute_spectrogram
from bats_ai.core.utils.guano_utils import extract_guano_metadata

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Import WAV files from a directory, extract GUANO metadata, and create recordings'

    def add_arguments(self, parser):
        parser.add_argument(
            'directory',
            type=str,
            help='Directory path containing WAV files to import',
        )
        parser.add_argument(
            '--owner',
            type=str,
            help='Username of the owner for the recordings (defaults to first superuser)',
        )
        parser.add_argument(
            '-p',
            '--public',
            action='store_true',
            help='Make imported recordings public',
        )
        parser.add_argument(
            '-l',
            '--limit',
            type=int,
            help='Limit the number of WAV files to import (useful for testing)',
        )

    def handle(self, *args, **options):
        directory_path = Path(options['directory'])
        owner_username = options.get('owner')
        is_public = options.get('public', False)
        limit = options.get('limit')

        # Validate directory
        if not directory_path.exists():
            self.stdout.write(self.style.ERROR(f'Directory does not exist: {directory_path}'))
            return

        if not directory_path.is_dir():
            self.stdout.write(self.style.ERROR(f'Path is not a directory: {directory_path}'))
            return

        # Get or find owner
        if owner_username:
            try:
                owner = User.objects.get(username=owner_username)
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'User not found: {owner_username}'))
                return
        else:
            # Default to first superuser
            owner = User.objects.filter(is_superuser=True).first()
            if not owner:
                self.stdout.write(
                    self.style.ERROR(
                        'No superuser found. Please specify --owner or create a superuser.'
                    )
                )
                return
            self.stdout.write(self.style.WARNING(f'Using default owner: {owner.username}'))

        # Find all WAV files
        wav_files = list(
            directory_path.rglob(
                '*.wav',
            )
        )

        if not wav_files:
            self.stdout.write(
                self.style.WARNING(f'No WAV files found in directory: {directory_path}')
            )
            return

        # Apply limit if specified
        total_files = len(wav_files)
        if limit and limit > 0:
            wav_files = wav_files[:limit]
            self.stdout.write(
                self.style.SUCCESS(
                    f'Found {total_files} WAV file(s), importing first {len(wav_files)}'
                )
            )
        else:
            self.stdout.write(self.style.SUCCESS(f'Found {len(wav_files)} WAV file(s) to import'))

        # Process each file
        successful = 0
        failed = 0

        for idx, wav_file in enumerate(wav_files, 1):
            self.stdout.write(f'\n[{idx}/{len(wav_files)}] Processing: {wav_file.name}')

            try:
                # Extract GUANO metadata
                self.stdout.write('  Extracting GUANO metadata...')
                metadata = extract_guano_metadata(wav_file, check_filename=True)

                # Extract date and time from metadata or file modification time
                recorded_date = None
                recorded_time = None

                if metadata.get('nabat_activation_start_time'):
                    dt = metadata['nabat_activation_start_time']
                    recorded_date = dt.date()
                    recorded_time = dt.time()
                else:
                    # Use file modification time as fallback
                    mtime = timezone.datetime.fromtimestamp(
                        wav_file.stat().st_mtime, tz=timezone.get_current_timezone()
                    )
                    recorded_date = mtime.date()
                    recorded_time = mtime.time()
                    self.stdout.write(
                        self.style.WARNING(
                            '  No activation start time in metadata, using file modification time'
                        )
                    )

                # Create Point from latitude/longitude if available
                point = None
                if metadata.get('nabat_latitude') and metadata.get('nabat_longitude'):
                    point = Point(metadata['nabat_longitude'], metadata['nabat_latitude'])

                # Get grid cell ID
                grts_cell_id = None
                if metadata.get('nabat_grid_cell_grts_id'):
                    try:
                        grts_cell_id = int(metadata['nabat_grid_cell_grts_id'])
                    except (ValueError, TypeError):
                        pass

                # Convert species list to string if present
                species_list_str = None
                if metadata.get('nabat_species_list'):
                    species_list_str = ','.join(metadata['nabat_species_list'])

                # Create recording
                self.stdout.write('  Creating recording...')
                with open(wav_file, 'rb') as f:
                    recording = Recording(
                        name=wav_file.name,
                        owner=owner,
                        audio_file=File(f, name=wav_file.name),
                        recorded_date=recorded_date,
                        recorded_time=recorded_time,
                        equipment=None,  # Not in GUANO metadata
                        grts_cell_id=grts_cell_id,
                        recording_location=point,
                        public=is_public,
                        comments=metadata.get('nabat_comments'),
                        detector=metadata.get('nabat_detector_type'),
                        software=metadata.get('nabat_software_type'),
                        site_name=metadata.get('nabat_site_name'),
                        species_list=species_list_str,
                        unusual_occurrences=metadata.get('nabat_unusual_occurrences'),
                    )
                    recording.save()

                self.stdout.write(self.style.SUCCESS(f'  Created recording ID: {recording.pk}'))

                # Generate spectrogram synchronously
                self.stdout.write('  Generating spectrogram...')
                try:
                    result = recording_compute_spectrogram(recording.pk)
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'  Spectrogram generated (ID: {result.get("spectrogram_id")})'
                        )
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'  Failed to generate spectrogram: {str(e)}')
                    )
                    logger.exception('Error generating spectrogram', exc_info=e)
                    raise e

                successful += 1
                self.stdout.write(self.style.SUCCESS(f'  ✓ Successfully imported: {wav_file.name}'))

            except Exception as e:
                failed += 1
                self.stdout.write(
                    self.style.ERROR(f'  ✗ Failed to import {wav_file.name}: {str(e)}')
                )
                logger.exception('Error importing file', exc_info=e)

        # Summary
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(
            self.style.SUCCESS(f'Import complete: {successful} successful, {failed} failed')
        )
