from pathlib import Path
import random
from random import randint, uniform
import tempfile
import uuid

from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand
from faker import Faker
import numpy as np
from scipy.io import wavfile

from bats_ai.core.models import Species
from bats_ai.core.models.nabat import NABatRecording, NABatRecordingAnnotation
from bats_ai.tasks.nabat.tasks import generate_compress_spectrogram, generate_spectrogram

fake = Faker()

MIN_AUDIO_DURATION = 2
MAX_AUDIO_DURATION = 6
SAMPLE_RATE = 250_000

CHIRP_MIN_FREQ = 23_000
CHIRP_MAX_FREQ = 70_000
CHIRP_MIN_BANDWIDTH = 20_000
CHIRP_MAX_BANDWIDTH = 40_000
CHIRP_MIN_DURATION = 0.005
CHIRP_MAX_DURATION = 0.018
CHIRP_MIN_INTERVAL = 0.200
CHIRP_MAX_INTERVAL = 0.350

# Bounding box for contiguous United States
US_MIN_LAT = 24.396308
US_MAX_LAT = 49.384358
US_MIN_LON = -125.0
US_MAX_LON = -66.93457


def generate_chirp(start_freq, end_freq, duration, sample_rate):
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    chirp = np.sin(2 * np.pi * np.linspace(start_freq, end_freq, len(t)) * t)
    return chirp


def generate_wav_file(filepath, duration):
    total_samples = int(SAMPLE_RATE * duration)
    audio = np.zeros(total_samples, dtype=np.float32)

    t = 0.0
    while t < duration:
        interval = uniform(CHIRP_MIN_INTERVAL, CHIRP_MAX_INTERVAL)
        chirp_duration = uniform(CHIRP_MIN_DURATION, CHIRP_MAX_DURATION)
        if t + chirp_duration > duration:
            break

        start_freq = uniform(CHIRP_MIN_FREQ, CHIRP_MAX_FREQ - CHIRP_MIN_BANDWIDTH)
        end_freq = start_freq + uniform(CHIRP_MIN_BANDWIDTH, CHIRP_MAX_BANDWIDTH)
        chirp = generate_chirp(start_freq, end_freq, chirp_duration, SAMPLE_RATE)

        start_index = int(t * SAMPLE_RATE)
        end_index = start_index + len(chirp)
        if end_index <= total_samples:
            audio[start_index:end_index] += chirp
        t += interval

    audio = np.int16(audio / np.max(np.abs(audio)) * 32767)
    wavfile.write(filepath, SAMPLE_RATE, audio)


def generate_random_point_us():
    lat = uniform(US_MIN_LAT, US_MAX_LAT)
    lon = uniform(US_MIN_LON, US_MAX_LON)
    return Point(lon, lat)


class Command(BaseCommand):
    help = 'Generate fake NABatRecording data with spectrograms and optional annotations'

    def add_arguments(self, parser):
        parser.add_argument('count', type=int, help='Number of recordings to generate')
        parser.add_argument(
            '--annotations',
            nargs=2,
            type=int,
            metavar=('NUM', 'VARIANCE'),
            help='Number of annotations to generate per file with variance (e.g. 5 2 for 3-7 annotations)',
        )

    def handle(self, *args, **options):
        count = options['count']
        annotation_config = options.get('annotations')

        species = list(Species.objects.all())
        if not species:
            self.stderr.write(self.style.ERROR('No Species objects found.'))
            return

        # Generate a pool of fake users
        fake_users = [(uuid.uuid4(), fake.email()) for _ in range(5)]

        with tempfile.TemporaryDirectory() as tmp_dir:
            for i in range(count):
                filename = f'recording_{i}.wav'
                wav_path = Path(tmp_dir) / filename
                duration = uniform(MIN_AUDIO_DURATION, MAX_AUDIO_DURATION)

                generate_wav_file(wav_path, duration)

                nabat_recording = NABatRecording.objects.create(
                    name=filename,
                    recording_location=generate_random_point_us(),
                    recording_id=random.randint(1000000, 9999999),
                    survey_event_id=random.randint(1000, 9999),
                    public=True,
                    nabat_auto_species=random.choice(species),
                    nabat_manual_species=random.choice(species),
                )

                with open(wav_path, 'rb') as wav_file:
                    spectrogram = generate_spectrogram(nabat_recording, wav_file)

                generate_compress_spectrogram(nabat_recording.pk, spectrogram.pk)

                # Optionally add annotations
                if annotation_config:
                    base, variance = annotation_config
                    num_annotations = max(0, randint(base - variance, base + variance))
                    for _ in range(num_annotations):
                        user_id, user_email = random.choice(fake_users)
                        annotation = NABatRecordingAnnotation.objects.create(
                            nabat_recording=nabat_recording,
                            comments=fake.sentence(),
                            user_id=user_id,
                            user_email=user_email,
                            model='fake_model_v1',
                            confidence=round(uniform(0.5, 1.0), 2),
                        )
                        annotation.species.set(
                            random.sample(species, k=random.randint(1, min(3, len(species))))
                        )

                self.stdout.write(
                    self.style.SUCCESS(f'Created NABatRecording {nabat_recording.pk}')
                )
