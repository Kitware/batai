import io
import logging
import math
import os
import tempfile

from PIL import Image
from celery import shared_task
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.files import File

from bats_ai.core.models import (
    CompressedSpectrogram,
    Configuration,
    Recording,
    RecordingAnnotation,
    Species,
    Spectrogram,
    SpectrogramImage,
)
from bats_ai.utils.spectrogram_utils import generate_spectrogram_assets, predict_from_compressed

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('NABatDataRetrieval')


@shared_task
def image_compute_checksum(image_id: int):
    image = Image.objects.get(pk=image_id)
    image.compute_checksum()
    image.save()


@shared_task
def recording_compute_spectrogram(recording_id: int):
    recording = Recording.objects.get(pk=recording_id)

    with tempfile.TemporaryDirectory() as tmpdir:
        results = generate_spectrogram_assets(recording.audio_file, tmpdir)
        # Create or get Spectrogram
        spectrogram, _ = Spectrogram.objects.get_or_create(
            recording=recording,
            defaults={
                'width': results['normal']['width'],
                'height': results['normal']['height'],
                'duration': results['duration'],
                'frequency_min': results['freq_min'],
                'frequency_max': results['freq_max'],
            },
        )
        # Create SpectrogramImage objects for each normal image
        for idx, img_path in enumerate(results['normal']['paths']):
            with open(img_path, 'rb') as f:
                SpectrogramImage.objects.get_or_create(
                    content_type=ContentType.objects.get_for_model(spectrogram),
                    object_id=spectrogram.id,
                    index=idx,
                    defaults={
                        'image_file': File(f, name=os.path.basename(img_path)),
                        'type': 'spectrogram',
                    },
                )

        # Create or get CompressedSpectrogram
        compressed = results['compressed']
        compressed_obj, _ = CompressedSpectrogram.objects.get_or_create(
            recording=recording,
            spectrogram=spectrogram,
            defaults={
                'length': compressed['width'],
                'widths': compressed['widths'],
                'starts': compressed['starts'],
                'stops': compressed['stops'],
                'cache_invalidated': False,
            },
        )

        # Save compressed images
        for idx, img_path in enumerate(compressed['paths']):
            with open(img_path, 'rb') as f:
                SpectrogramImage.objects.get_or_create(
                    content_type=ContentType.objects.get_for_model(compressed_obj),
                    object_id=compressed_obj.id,
                    index=idx,
                    defaults={
                        'image_file': File(f, name=os.path.basename(img_path)),
                        'type': 'compressed',
                    },
                )

        config = Configuration.objects.first()
        if config and config.run_inference_on_upload:
            predict_results = predict_from_compressed(compressed_obj)
            label = predict_results['label']
            score = predict_results['score']
            confs = predict_results['confs']
            confidences = [{'label': key, 'value': float(value)} for key, value in confs.items()]
            sorted_confidences = sorted(confidences, key=lambda x: x['value'], reverse=True)
            output = {
                'label': label,
                'score': float(score),
                'confidences': sorted_confidences,
            }
            species = Species.objects.filter(species_code=label)

            recording_annotation = RecordingAnnotation.objects.create(
                recording=compressed_obj.recording,
                owner=compressed_obj.recording.owner,
                comments='Compressed Spectrogram Generation Prediction',
                model='model.mobilenet.onnx',
                confidence=output['score'],
                additional_data=output,
            )
            recording_annotation.species.set(species)
            recording_annotation.save()

        return {'spectrogram_id': spectrogram.id, 'compressed_id': compressed_obj.id}

def _fully_local_inference(image_file, use_mlflow_model):
    import json

    import onnx
    import onnxruntime as ort
    import tqdm

    img = Image.open(image_file)

    if not use_mlflow_model:
        relative = ('..',) * 3
        asset_path = os.path.abspath(os.path.join(__file__, *relative, 'assets'))

        onnx_filename = os.path.join(asset_path, 'model.mobilenet.onnx')
        assert os.path.exists(onnx_filename)

        session = ort.InferenceSession(
            onnx_filename,
            providers=[
                (
                    'CUDAExecutionProvider',
                    {
                        'cudnn_conv_use_max_workspace': '1',
                        'device_id': 0,
                        'cudnn_conv_algo_search': 'HEURISTIC',
                    },
                ),
                'CPUExecutionProvider',
            ],
        )
    else:
        import mlflow
        import mlflow.onnx

        MODEL_URI = 'models:/prototype/1'
        mlflow.set_tracking_uri(settings.MLFLOW_ENDPOINT)
        model = mlflow.onnx.load_model(model_uri=MODEL_URI)
        session = ort.InferenceSession(
            model.SerializeToString(),
            providers=[
                (
                    'CUDAExecutionProvider',
                    {
                        'cudnn_conv_use_max_workspace': '1',
                        'device_id': 0,
                        'cudnn_conv_algo_search': 'HEURISTIC',
                    },
                ),
                'CPUExecutionProvider',
            ],
        )

    img = np.array(img)

    h, w, c = img.shape
    ratio_y = 224 / h
    ratio_x = ratio_y * 0.5
    raw = cv2.resize(img, None, fx=ratio_x, fy=ratio_y, interpolation=cv2.INTER_LANCZOS4)

    h, w, c = raw.shape
    if w <= h:
        canvas = np.zeros((h, h + 1, 3), dtype=raw.dtype)
        canvas[:, :w, :] = raw
        raw = canvas
        h, w, c = raw.shape

    inputs_ = []
    for index in range(0, w - h, 100):
        inputs_.append(raw[:, index : index + h, :])
    inputs_.append(raw[:, -h:, :])
    inputs_ = np.array(inputs_)

    chunksize = 1
    chunks = np.array_split(inputs_, np.arange(chunksize, len(inputs_), chunksize))
    outputs = []
    for chunk in tqdm.tqdm(chunks, desc='Inference'):
        outputs_ = session.run(
            None,
            {'input': chunk},
        )
        outputs.append(outputs_[0])
    outputs = np.vstack(outputs)
    outputs = outputs.mean(axis=0)

    model = onnx.load(onnx_filename)
    mapping = json.loads(model.metadata_props[0].value)
    labels = [mapping['forward'][str(index)] for index in range(len(mapping['forward']))]

    prediction = np.argmax(outputs)
    label = labels[prediction]
    score = outputs[prediction]

    confs = dict(zip(labels, outputs))

    return label, score, confs


def predict_compressed(image_file):
    # 0: use the local file and do inference with that
    # 1: get the file from mlflow and do inference locally
    # 2: do inference from deployed mlflow model
    inference_mode = int(os.getenv('INFERENCE_MODE', 0))
    if inference_mode == 1:
        pass
    elif inference_mode == 2:
        pass
    else:
        return _fully_local_inference(image_file, False)


def train_body(experiment_name: str):
    import mlflow
    from mlflow.models import infer_signature
    from sklearn import datasets
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import accuracy_score
    from sklearn.model_selection import train_test_split

    X, y = datasets.load_iris(return_X_y=True)

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    params = {
        'solver': 'lbfgs',
        'max_iter': 1000,
        'multi_class': 'auto',
        'random_state': 8888,
    }

    lr = LogisticRegression(**params)
    lr.fit(X_train, y_train)

    y_pred = lr.predict(X_test)

    accuracy = accuracy_score(y_test, y_pred)

    mlflow.set_tracking_uri(settings.MLFLOW_ENDPOINT)
    mlflow.set_experiment(experiment_name)

    print(mlflow.get_tracking_uri())
    print(mlflow.get_artifact_uri())

    mlflow.end_run()
    with mlflow.start_run():
        mlflow.log_params(params)
        mlflow.log_metric('accuracy', accuracy)
        mlflow.set_tag('Training Info', 'Basic LR model for iris data')

        signature = infer_signature(X_train, lr.predict(X_train))
        _ = mlflow.sklearn.log_model(
            sk_model=lr,
            artifact_path='iris_model',
            signature=signature,
            input_example=X_train,
            registered_model_name='tracking-quickstart',
        )


@shared_task
def example_train(experiment_name: str):
    train_body(experiment_name)
