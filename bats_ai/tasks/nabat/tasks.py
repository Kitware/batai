import io
import tempfile

from PIL import Image
from celery import shared_task
import cv2
from django.core.files import File
import numpy as np
import scipy

from bats_ai.core.models import Species
from bats_ai.core.models.nabat import (
    AcousticBatch,
    AcousticBatchAnnotation,
    NABatCompressedSpectrogram,
    NABatSpectrogram,
)


def generate_compressed(spectrogram: NABatSpectrogram):
    img = spectrogram.image_np

    threshold = 0.5
    while True:
        canvas = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        canvas = canvas.astype(np.float32)

        is_light = np.median(canvas) > 128.0
        if is_light:
            canvas = 255.0 - canvas

        amplitude = canvas.max(axis=0)
        amplitude -= amplitude.min()
        amplitude /= amplitude.max()
        amplitude[amplitude < threshold] = 0.0
        amplitude[amplitude > 0] = 1.0
        amplitude = amplitude.reshape(1, -1)

        canvas -= canvas.min()
        canvas /= canvas.max()
        canvas *= 255.0
        canvas *= amplitude
        canvas = np.around(canvas).astype(np.uint8)

        mask = canvas.max(axis=0)
        mask = scipy.signal.medfilt(mask, 3)
        mask[0] = 0
        mask[-1] = 0

        starts = []
        stops = []
        for index in range(1, len(mask) - 1):
            value_pre = mask[index - 1]
            value = mask[index]
            value_post = mask[index + 1]
            if value != 0:
                if value_pre == 0:
                    starts.append(index)
                if value_post == 0:
                    stops.append(index)
        assert len(starts) == len(stops)

        starts = [val - 40 for val in starts]  # 10 ms buffer
        stops = [val + 40 for val in stops]  # 10 ms buffer
        ranges = list(zip(starts, stops))

        while True:
            found = False
            merged = []
            index = 0
            while index < len(ranges) - 1:
                start1, stop1 = ranges[index]
                start2, stop2 = ranges[index + 1]

                start1 = min(max(start1, 0), len(mask))
                start2 = min(max(start2, 0), len(mask))
                stop1 = min(max(stop1, 0), len(mask))
                stop2 = min(max(stop2, 0), len(mask))

                if stop1 >= start2:
                    found = True
                    merged.append((start1, stop2))
                    index += 2
                else:
                    merged.append((start1, stop1))
                    index += 1
                if index == len(ranges) - 1:
                    merged.append((start2, stop2))
            ranges = merged
            if not found:
                for index in range(1, len(ranges)):
                    start1, stop1 = ranges[index - 1]
                    start2, stop2 = ranges[index]
                    assert start1 < stop1
                    assert start2 < stop2
                    assert start1 < start2
                    assert stop1 < stop2
                    assert stop1 < start2
                break

        segments = []
        starts_ = []
        stops_ = []
        domain = img.shape[1]
        widths = []
        total_width = 0
        for start, stop in ranges:
            segment = img[:, start:stop]
            segments.append(segment)

            starts_.append(int(round(spectrogram.duration * (start / domain))))
            stops_.append(int(round(spectrogram.duration * (stop / domain))))
            widths.append(stop - start)
            total_width += stop - start

            # buffer = np.zeros((len(img), 20, 3), dtype=img.dtype)
            # segments.append(buffer)
        # segments = segments[:-1]

        if len(segments) > 0:
            break

        threshold -= 0.05
        if threshold < 0:
            segments = None
            break

    if segments is None:
        canvas = img.copy()
    else:
        canvas = np.hstack(segments)

    canvas = Image.fromarray(canvas, 'RGB')
    buf = io.BytesIO()
    canvas.save(buf, format='JPEG', quality=80)
    buf.seek(0)

    # Use temporary files
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
        temp_file_name = temp_file.name
        canvas.save(temp_file_name)

        # Read the temporary file
        with open(temp_file_name, 'rb') as f:
            temp_file_content = f.read()

    # Wrap the content in BytesIO
    buf = io.BytesIO(temp_file_content)
    name = f'{spectrogram.pk}_spectrogram_compressed.jpg'
    image_file = File(buf, name=name)

    return total_width, image_file, widths, starts_, stops_


@shared_task
def generate_compress_spectrogram(acoustic_batch_id: int, spectrogram_id: int):
    acoustic_batch = AcousticBatch.objects.get(pk=acoustic_batch_id)
    spectrogram = NABatSpectrogram.objects.get(pk=spectrogram_id)
    length, image_file, widths, starts, stops = generate_compressed(spectrogram)
    found = NABatCompressedSpectrogram.objects.filter(
        acoustic_batch=acoustic_batch_id, spectrogram=spectrogram
    )
    if found.exists():
        existing = found.first()
        existing.length = length
        existing.image_file = image_file
        existing.widths = widths
        existing.starts = starts
        existing.stops = stops
        existing.cache_invalidated = False
        existing.save()
    else:
        existing = NABatCompressedSpectrogram.objects.create(
            acoustic_batch=acoustic_batch,
            spectrogram=spectrogram,
            image_file=image_file,
            length=length,
            widths=widths,
            starts=starts,
            stops=stops,
            cache_invalidated=False,
        )
    return existing


@shared_task
def acousting_batch_initialize(batch_id: int, api_token: str):
    print(batch_id)
    # Need to get the information from the server using the api_token and the batch_id
    # 1. Use the batch_id and api_token to gather information about the AcousticBatch using graphQL endpoint
    # 2. Create the AcousticBatch object, using the batch_id and values from the server
    # 3. Use an additional GraphQL query to get the S3 Pre-Signed file URL for the recording object
    # 4. Download the files from S3 and use it to convert into a spectrogram that can be saved to the system
    # 5. Use the spectrogram to generate a compressed spectrogram
    # 6. Use the compressed spectrogram to predict the species

    # Eventual compressed generation
    # cmaps = [
    #     None,  # Default (dark) spectrogram
    #     'light',  # Light spectrogram
    # ]
    # spectrogram_id = None
    # for cmap in cmaps:
    #     with colormap(cmap):
    #         spectrogram_id_temp = NABatSpectrogram.generate(acoustic_batch, cmap)
    #         if cmap is None:
    #             spectrogram_id = spectrogram_id_temp
    # if spectrogram_id is not None:
    #     compressed_spectro = generate_compress_spectrogram(spectrogram_id)
    #     predict(compressed_spectro.pk)


@shared_task
def predict(compressed_spectrogram_id: int):
    compressed_spectrogram = NABatCompressedSpectrogram.objects.get(pk=compressed_spectrogram_id)
    label, score, confs = compressed_spectrogram.predict()
    confidences = [{'label': key, 'value': float(value)} for key, value in confs.items()]
    sorted_confidences = sorted(confidences, key=lambda x: x['value'], reverse=True)
    output = {
        'label': label,
        'score': float(score),
        'confidences': sorted_confidences,
    }
    species = Species.objects.filter(species_code=label)

    acoustic_batch_annotation = AcousticBatchAnnotation.objects.create(
        recording=compressed_spectrogram.recording,
        comments='Compressed Spectrogram Generation Prediction',
        model='model.mobilenet.onnx',
        confidence=output['score'],
        additional_data=output,
    )
    acoustic_batch_annotation.species.set(species)
    acoustic_batch_annotation.save()
    return label, score, confs
