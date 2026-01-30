import logging
from pathlib import Path
import tempfile

from django.contrib.gis.geos import LineString, Point, Polygon
import requests

from bats_ai.core.models import Configuration, ProcessingTask, PulseMetadata, Species
from bats_ai.core.models.nabat import NABatRecording, NABatRecordingAnnotation
from bats_ai.core.utils.batbot_metadata import generate_spectrogram_assets
from bats_ai.utils.spectrogram_utils import (
    generate_nabat_compressed_spectrogram,
    generate_nabat_spectrogram,
    predict_from_compressed,
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

        compressed_obj = generate_nabat_compressed_spectrogram(
            nabat_recording, spectrogram, compressed
        )
        segment_index_map = {}
        for segment in compressed['contours']['segments']:
            pulse_metadata_obj, _ = PulseMetadata.objects.get_or_create(
                recording=compressed_obj.recording,
                index=segment['segment_index'],
                defaults={
                    'contours': segment['contours'],
                    'bounding_box': Polygon(
                        (
                            (segment['start_ms'], segment['freq_max']),
                            (segment['stop_ms'], segment['freq_max']),
                            (segment['stop_ms'], segment['freq_min']),
                            (segment['start_ms'], segment['freq_min']),
                            (segment['start_ms'], segment['freq_max']),
                        )
                    ),
                },
            )
            segment_index_map[segment['segment_index']] = pulse_metadata_obj
        for segment in compressed['segments']:
            if segment['segment_index'] not in segment_index_map:
                PulseMetadata.objects.get_or_create(
                    recording=compressed_obj.recording,
                    index=segment['segment_index'],
                    defaults={
                        'curve': LineString([Point(x[1], x[0]) for x in segment['curve_hz_ms']]),
                        'char_freq': Point(segment['char_freq_ms'], segment['char_freq_hz']),
                        'knee': Point(segment['knee_ms'], segment['knee_hz']),
                        'heel': Point(segment['heel_ms'], segment['heel_hz']),
                    },
                )
            else:
                pulse_metadata_obj = segment_index_map[segment['segment_index']]
                pulse_metadata_obj.curve = LineString(
                    [Point(x[1], x[0]) for x in segment['curve_hz_ms']]
                )
                pulse_metadata_obj.char_freq = Point(
                    segment['char_freq_ms'], segment['char_freq_hz']
                )
                pulse_metadata_obj.knee = Point(segment['knee_ms'], segment['knee_hz'])
                pulse_metadata_obj.heel = Point(segment['heel_ms'], segment['heel_hz'])
                pulse_metadata_obj.save()

        try:
            config = Configuration.objects.first()
            # TODO: Disabled until prediction is in batbot
            if config and config.run_inference_on_upload and False:
                self.update_state(
                    state='Progress',
                    meta={'description': 'Running Prediction on Spectrogram'},
                )

                predict_results = predict_from_compressed(compressed_obj)
                label = predict_results['label']
                score = predict_results['score']
                confs = predict_results['confs']
                confidences = [
                    {'label': key, 'value': float(value)} for key, value in confs.items()
                ]
                sorted_confidences = sorted(confidences, key=lambda x: x['value'], reverse=True)
                output = {
                    'label': label,
                    'score': float(score),
                    'confidences': sorted_confidences,
                }
                species = Species.objects.filter(species_code=label)

                nabat_recording_annotation = NABatRecordingAnnotation.objects.create(
                    nabat_recording=compressed_obj.nabat_recording,
                    comments='Compressed Spectrogram Generation Prediction',
                    model='model.mobilenet.onnx',
                    confidence=output['score'],
                    additional_data=output,
                )
                nabat_recording_annotation.species.set(species)
                nabat_recording_annotation.save()

        except Exception as e:
            logger.error(f'Error Performing Prediction: {e}')
            processing_task.status = ProcessingTask.Status.ERROR
            processing_task.error = f'Error performing prediction: {e}'
            processing_task.save()
            raise

        processing_task.status = ProcessingTask.Status.COMPLETE
        processing_task.save()
