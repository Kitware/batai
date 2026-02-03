"""
Management command to create new recordings by copying existing ones with new names.

Useful for generating test data: copies metadata and audio file from existing
recordings, assigns a new name and optional tags (default: test, foo, bar).
Reuses the source recording's spectrogram images and compressed spectrogram
(no recompute); copies RecordingAnnotations to the new recording.
"""

import logging
import random

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from bats_ai.core.models import (
    CompressedSpectrogram,
    Recording,
    RecordingAnnotation,
    RecordingTag,
    Spectrogram,
    SpectrogramImage,
)

logger = logging.getLogger(__name__)

DEFAULT_TAGS = ['test', 'foo', 'bar']


def _link_spectrogram_and_annotations(source_recording, new_recording):
    spectrograms = list(Spectrogram.objects.filter(recording=source_recording).order_by('-created'))
    if not spectrograms:
        return
    source_spectrogram = spectrograms[0]

    ct_spectrogram = ContentType.objects.get_for_model(Spectrogram)
    ct_compressed = ContentType.objects.get_for_model(CompressedSpectrogram)

    # New Spectrogram (same dimensions)
    new_spectrogram = Spectrogram.objects.create(
        recording=new_recording,
        width=source_spectrogram.width,
        height=source_spectrogram.height,
        duration=source_spectrogram.duration,
        frequency_min=source_spectrogram.frequency_min,
        frequency_max=source_spectrogram.frequency_max,
    )
    # Link same image files: create SpectrogramImage rows pointing to source paths
    for src_img in source_spectrogram.images.filter(type='spectrogram').order_by('index'):
        new_img = SpectrogramImage(
            content_type=ct_spectrogram,
            object_id=new_spectrogram.id,
            type='spectrogram',
            index=src_img.index,
            image_file=ContentFile(b' ', name='placeholder'),
        )
        new_img.save()
        old_path = new_img.image_file.name
        SpectrogramImage.objects.filter(pk=new_img.pk).update(image_file=src_img.image_file.name)
        if old_path and default_storage.exists(old_path):
            default_storage.delete(old_path)

    # CompressedSpectrogram if present (most recent only)
    compressed_qs = CompressedSpectrogram.objects.filter(recording=source_recording).order_by(
        '-created'
    )[:1]
    for src_comp in compressed_qs:
        new_comp = CompressedSpectrogram.objects.create(
            recording=new_recording,
            spectrogram=new_spectrogram,
            length=src_comp.length,
            starts=src_comp.starts,
            stops=src_comp.stops,
            widths=src_comp.widths,
            cache_invalidated=src_comp.cache_invalidated,
        )
        for src_img in src_comp.images.filter(type='compressed').order_by('index'):
            new_img = SpectrogramImage(
                content_type=ct_compressed,
                object_id=new_comp.id,
                type='compressed',
                index=src_img.index,
                image_file=ContentFile(b' ', name='placeholder'),
            )
            new_img.save()
            old_path = new_img.image_file.name
            SpectrogramImage.objects.filter(pk=new_img.pk).update(
                image_file=src_img.image_file.name
            )
            if old_path and default_storage.exists(old_path):
                default_storage.delete(old_path)

    # Copy RecordingAnnotations
    for src_ann in RecordingAnnotation.objects.filter(recording=source_recording):
        new_ann = RecordingAnnotation.objects.create(
            recording=new_recording,
            owner=new_recording.owner,
            comments=src_ann.comments,
            model=src_ann.model,
            confidence=src_ann.confidence,
            additional_data=src_ann.additional_data,
            submitted=src_ann.submitted,
        )
        new_ann.species.set(src_ann.species.all())


class Command(BaseCommand):
    help = (
        'Create new recordings by copying existing ones with new names. '
        'Optionally apply tags (default: test, foo, bar).'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=1,
            help='Number of new recordings to create (default: 1)',
        )
        parser.add_argument(
            '--tags',
            type=str,
            default=','.join(DEFAULT_TAGS),
            help='Comma-separated tags to apply (default: test,foo,bar)',
        )
        parser.add_argument(
            '--owner',
            type=str,
            help='Username of the owner for the new recordings\
            (default: use source recording owner)',
        )

    def handle(self, *args, **options):
        count = options['count']
        tags_raw = options['tags'] or ','.join(DEFAULT_TAGS)
        tag_texts = [t.strip() for t in tags_raw.split(',') if t.strip()]
        if not tag_texts:
            tag_texts = DEFAULT_TAGS
        owner_username = options.get('owner')

        if count < 1:
            raise CommandError('--count must be at least 1.')

        recordings = list(Recording.objects.all().order_by('id'))
        if not recordings:
            raise CommandError('No existing recordings found. Create or import some first.')

        owner = None
        if owner_username:
            try:
                owner = User.objects.get(username=owner_username)
            except User.DoesNotExist:
                raise CommandError(f'User not found: {owner_username}')

        created = []
        for i in range(count):
            source = recordings[i % len(recordings)]
            if owner is None:
                owner = source.owner

            new_name = f'Copy of {source.name} ({i + 1})'
            self.stdout.write(
                f'Creating copy {i + 1}/{count}: {new_name} from recording id={source.pk}'
            )

            try:
                with transaction.atomic():
                    # Copy file content (works for local and remote storage)
                    source.audio_file.open('rb')
                    try:
                        file_content = source.audio_file.read()
                    finally:
                        source.audio_file.close()

                    # Preserve extension if present
                    ext = ''
                    if source.audio_file.name and '.' in source.audio_file.name:
                        ext = '.' + source.audio_file.name.rsplit('.', 1)[-1]
                    save_name = new_name + ext if ext else new_name

                    new_recording = Recording(
                        name=new_name,
                        owner=owner,
                        audio_file=ContentFile(file_content, name=save_name),
                        recorded_date=source.recorded_date,
                        recorded_time=source.recorded_time,
                        equipment=source.equipment,
                        comments=source.comments,
                        recording_location=source.recording_location,
                        grts_cell_id=source.grts_cell_id,
                        grts_cell=source.grts_cell,
                        public=source.public,
                        software=source.software,
                        detector=source.detector,
                        species_list=source.species_list,
                        site_name=source.site_name,
                        unusual_occurrences=source.unusual_occurrences,
                    )
                    new_recording.save()

                    # Apply a random subset of tags to this recording
                    k = random.randint(1, len(tag_texts))
                    chosen = random.sample(tag_texts, k=k)
                    for text in chosen:
                        tag, _ = RecordingTag.objects.get_or_create(user=owner, text=text)
                        new_recording.tags.add(tag)

                    # Reuse source spectrogram images and copy annotations (no recompute)
                    _link_spectrogram_and_annotations(source, new_recording)

                    created.append(new_recording)
                    self.stdout.write(
                        self.style.SUCCESS(f'  Created recording id={new_recording.pk}')
                    )
                    self.stdout.write('  Linked spectrogram images and copied annotations.')

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  Failed: {e}'))
                logger.exception('Error copying recording', exc_info=e)

        self.stdout.write('')
        tag_str = ', '.join(tag_texts)
        self.stdout.write(
            self.style.SUCCESS(f'Done: created {len(created)} recording(s) with tags: {tag_str}')
        )
