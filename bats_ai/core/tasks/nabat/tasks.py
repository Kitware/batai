import logging
from pathlib import Path
import tempfile

import requests

from bats_ai.core.models import ProcessingTask
from bats_ai.core.models.nabat import NABatRecording
from bats_ai.core.utils.batbot_metadata import generate_spectrogram_assets
from bats_ai.utils.spectrogram_utils import (
    generate_nabat_compressed_spectrogram,
    generate_nabat_spectrogram,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('NABatDataRetrieval')


def generate_spectrograms(
    self, nabat_recording: NABatRecording, presigned_url: str, processing_task: ProcessingTask
):
    with tempfile.TemporaryDirectory() as tmpdir:
        audio_file = None
        try:
            file_response = requests.get(presigned_url, stream=True)
            if file_response.status_code == 200:
                audio_file = Path(f'{tmpdir}/audio_file.wav')
                with open(audio_file, 'wb') as temp_file:
                    for chunk in file_response.iter_content(chunk_size=8192):
                        temp_file.write(chunk)
        except Exception as e:
            logger.error(f'Error Downloading Presigned URL: {e}')
            processing_task.status = ProcessingTask.Status.ERROR
            processing_task.error = f'Error Downloading Presigned URL: {e}'
            processing_task.save()
            raise

        # Generate spectrogram assets
        logger.info('Generating spectrograms...')
        self.update_state(
            state='Progress',
            meta={'description': 'Generating Spectrograms'},
        )

        results = generate_spectrogram_assets(audio_file, tmpdir)

        self.update_state(
            state='Progress',
            meta={'description': 'Converting Spectrograms to Models'},
        )

        spectrogram = generate_nabat_spectrogram(nabat_recording, results)

        compressed = results['compressed']

        generate_nabat_compressed_spectrogram(nabat_recording, spectrogram, compressed)

        processing_task.status = ProcessingTask.Status.COMPLETE
        processing_task.save()
