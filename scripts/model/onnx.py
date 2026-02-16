import json
from pathlib import Path
import random

import cv2
import numpy as np
import onnx
import onnxruntime as ort
import torch
import torchvision

# pip install onnx onnxruntime-gpu


COMPLEXITY = 64


class TransformsInference(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.mean = [0.0932, 0.0255, 0.0512]
        self.stddev = [0.1057, 0.0543, 0.1170]

    def forward(self, imgs):
        import torchvision.transforms.functional as F

        imgs = imgs.permute((0, 3, 1, 2))
        imgs = F.convert_image_dtype(imgs, torch.float32)
        imgs = F.normalize(imgs, mean=self.mean, std=self.stddev)
        return imgs


pytorch_filename = 'save.pth'
onnx_filename = 'save.onnx'

data = torch.load(pytorch_filename, map_location='cpu')
labels = data['labels']
labels_ = {value: key for key, value in labels.items()}
mapping = {'forward': labels, 'backward': labels_}

if True:
    model = torchvision.models.vit_b_16()
    model.heads = torch.nn.Sequential(
        torch.nn.Linear(768, len(labels)),
    )
else:
    model = torchvision.models.mobilenet_v3_large()
    model.classifier = torch.nn.Sequential(
        torch.nn.Linear(960, COMPLEXITY),
        torch.nn.Hardswish(inplace=True),
        torch.nn.Dropout(p=0.2, inplace=True),
        torch.nn.Linear(COMPLEXITY, len(labels)),
    )

model.load_state_dict(data['state'])

transforms = TransformsInference()
model = torch.nn.Sequential(
    transforms,
    model,
    torch.nn.Softmax(dim=1),
)
model.eval()

paths = Path('val').rglob('*.jpg')
paths = [str(path.absolute()) for path in paths]
random.shuffle(paths)
paths = paths[:2]

imgs = []
for path in paths:
    img = cv2.imread(path)
    h, w, c = img.shape
    if w < h:
        continue
    index = random.randint(0, w - h)
    img = img[:, index : index + h, :]
    img = cv2.resize(img, (224, 224), interpolation=cv2.INTER_LANCZOS4)
    imgs.append(img)
imgs = np.array(imgs)

dummy_input = torch.from_numpy(imgs)
input_names = ['input']
output_names = ['output']

with torch.no_grad():
    torch_output = model(dummy_input)
    torch_output = torch_output.numpy()

torch.onnx.export(
    model,
    dummy_input,
    onnx_filename,
    verbose=False,
    input_names=input_names,
    output_names=output_names,
    export_params=True,
    opset_version=15,
    dynamic_axes={
        'input': {0: 'batch_size'},  # variable length axes
        'output': {0: 'batch_size'},
    },
)

device_id = 0
ort_session = ort.InferenceSession(
    onnx_filename,
    providers=[
        (
            'CUDAExecutionProvider',
            {
                'cudnn_conv_use_max_workspace': '1',
                'device_id': device_id,
                'cudnn_conv_algo_search': 'HEURISTIC',
            },
        ),
        'CPUExecutionProvider',
    ],
)
ort_output = ort_session.run(
    None,
    {'input': dummy_input.numpy()},
)
ort_output = ort_output[0]

np.testing.assert_allclose(torch_output, ort_output, rtol=1e-03, atol=3e-02)

torch_preds = np.argmax(torch_output, axis=1).tolist()
ort_preds = np.argmax(ort_output, axis=1).tolist()
assert torch_preds == ort_preds

model = onnx.load(onnx_filename)
meta = model.metadata_props.add()
meta.key = 'labels'
meta.value = json.dumps(mapping)
onnx.save(model, onnx_filename)
