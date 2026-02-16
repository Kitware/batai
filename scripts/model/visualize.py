import json
import os
from pathlib import Path
import pickle

import cv2
import matplotlib.pyplot as plt
import numpy as np
import onnx
from sklearn import metrics
import matplotlib.patches as patches
import torch
import tqdm

# pip install matplotlib

NUM_GPUS = 4
WORKERS = 8
ONNX_BATCH_SIZE = 10

CUSTOM_LABEL = 'NOISE'


class Dataset(torch.utils.data.Dataset):
    def __init__(self, paths):
        self.paths = paths

    def __getitem__(self, index):
        path = self.paths[index]

        img = cv2.imread(path)

        return path, img

    def __len__(self):
        return len(self.paths)


def parallel(
    func,
    inputs,
    outputs,
    workers=WORKERS,
    assignment=False,
    threaded=False,
    quiet=True,
    desc=None,
):
    import concurrent.futures

    import tqdm

    if len(inputs) == 0:
        return None

    if threaded:
        executor_cls = concurrent.futures.ThreadPoolExecutor
    else:
        executor_cls = concurrent.futures.ProcessPoolExecutor

    workers = min(len(inputs), workers)

    with tqdm.tqdm(total=len(inputs), disable=quiet, desc=desc) as progress:
        with executor_cls(max_workers=workers) as executor:
            futures = [executor.submit(func, input_) for input_ in inputs]
            for future in concurrent.futures.as_completed(futures):
                key, data = future.result()
                if key is None:
                    outputs.update(data)
                elif assignment:
                    outputs[int(key)] = data
                else:
                    if key not in outputs:
                        outputs[key] = {}
                    outputs[key].update(data)
                progress.update(1)


def worker(inputs):
    import onnxruntime as ort

    position, paths, onnx_filename, device_id = inputs

    def _collate_func(batch):
        paths = [item[0] for item in batch]
        imgs = np.array([item[1] for item in batch])
        return paths, imgs

    dataset = Dataset(paths)
    dataloader = torch.utils.data.DataLoader(
        dataset,
        batch_size=1,
        num_workers=WORKERS,
        collate_fn=_collate_func,
    )

    session = ort.InferenceSession(
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

    chunksize = ONNX_BATCH_SIZE
    predictions = {}
    for paths, inputs in tqdm.tqdm(dataloader, desc=f'Device: {device_id}', position=position):
        b, h, w, c = inputs.shape
        assert len(paths) == 1
        assert b == 1

        ratio_y = 224 / 300
        ratio_x = ratio_y * 0.5
        raw = cv2.resize(inputs[0], None, fx=ratio_x, fy=ratio_y, interpolation=cv2.INTER_LANCZOS4)

        inputs_ = []
        h, w, c = raw.shape
        if w <= h:
            canvas = np.zeros((h, h + 1, 3), dtype=raw.dtype)
            canvas[:, :w, :] = raw
            raw = canvas
            h, w, c = raw.shape

        for index in range(0, w - h, 100):
            inputs_.append(raw[:, index : index + h, :])
        inputs_ = np.array(inputs_)

        chunks = np.array_split(inputs_, np.arange(chunksize, len(inputs_), chunksize))
        outputs = []
        for chunk in chunks:
            outputs_ = session.run(
                None,
                {'input': chunk},
            )
            outputs.append(outputs_[0])
        outputs = np.vstack(outputs)
        outputs = outputs.mean(axis=0)
        predictions.update(dict(zip(paths, [outputs])))

    return None, predictions


def shade_regions(display, ax, plot):
    regions = sorted(set([value[:2] for value in display]))
    color = (1.0, 0.0, 0.0, 0.2)
    errors = 0
    for region in regions:
        indices = [
            index
            for index, value in enumerate(display)
            if value[:2] == region
        ]
        min_index = min(indices)
        max_index = max(indices)

        if min_index > 0:
            errors += plot.confusion_matrix[min_index:min_index + len(indices), :min_index].sum()

            rect = patches.Rectangle(
                (0 - 0.48, min_index - 0.52), 
                min_index, 
                len(indices), 
                linewidth=1, 
                edgecolor='none', 
                facecolor=color,
            )
            ax.add_patch(rect)

        if max_index < len(display) - 1:
            errors += plot.confusion_matrix[min_index:min_index + len(indices), max_index + 1:].sum()

            rect = patches.Rectangle(
                (max_index + 1 - 0.48, max_index + 1 - len(indices) - 0.52), 
                len(display) - max_index - 1, 
                len(indices), 
                linewidth=1, 
                edgecolor='none', 
                facecolor=color,
            )
            ax.add_patch(rect)

    diff = errors / plot.confusion_matrix.sum()
    return diff


print('Visualizing the performance')

tag = 'val'

# predictions_onnx_model = 'model.vit.onnx'
# predictions_cache = f'predictions.{tag}.vit.pkl'

predictions_onnx_model = 'model.mobilenet.onnx'
predictions_cache = f'predictions.{tag}.mobilenet.pkl'

paths = Path(tag).rglob('*.jpg')
paths = [str(path.absolute()) for path in paths]

model = onnx.load(predictions_onnx_model)
mapping = json.loads(model.metadata_props[0].value)

labels = []
for path in paths:
    path_ = path.split('/')
    label = path_[-2]
    labels.append(label)

targets = np.array([mapping['backward'][label] for label in labels])

if not os.path.exists(predictions_cache):
    print('\trunning inference on tiles')
    chunks = np.array_split(paths, NUM_GPUS)

    inputs = [
        (index, chunk.tolist(), predictions_onnx_model, index % NUM_GPUS)
        for index, chunk in enumerate(chunks)
    ]
    predictions = {}
    parallel(
        worker,
        inputs,
        predictions,
        quiet=True,
    )

    pickle.dump(predictions, open(predictions_cache, 'wb'))

custom_index = mapping['backward'].get(CUSTOM_LABEL, None)

if custom_index is None:
    print('\troundR negative class not found')
    fig, axes = plt.subplots(1, 3, figsize=(45, 15))
    ax11, ax12, ax13 = axes
else:
    print('\troundR negative class found')
    fig, axes = plt.subplots(2, 4, figsize=(60, 30))
    ax11, ax12, ax13, ax14 = axes[0]
    ax21, ax22, ax23, ax24 = axes[1]

    ax14.axis('off')

    for ax in [ax21, ax23]:
        ax.set_autoscalex_on(False)
        ax.set_autoscaley_on(False)
        ax.set_xlim([-0.01, 1.01])
        ax.set_ylim([-0.01, 1.01])
        ax.set_xticks(np.arange(0.0, 1.1, 0.1))
        ax.set_yticks(np.arange(0.0, 1.1, 0.1))

##########################################################################################

predictions_cache = f'predictions.{tag}.mobilenet.pkl'
print(f'\tloading predictions from {predictions_cache}')
predictions = pickle.load(open(predictions_cache, 'rb'))
confs1 = np.array([predictions[path] for path in paths])

predictions_cache = f'predictions.{tag}.vit.pkl'
print(f'\tloading predictions from {predictions_cache}')
predictions = pickle.load(open(predictions_cache, 'rb'))
confs2 = np.array([predictions[path] for path in paths])

# confs = (confs1 + confs2) * 0.5
# confs = confs1
confs = confs2
preds = np.argmax(confs, axis=1)

print('\tplotting confusion matrices')
labels = list(range(len(mapping['forward'])))
display = [mapping['forward'][str(index)] for index in range(len(mapping['forward']))]

accuracy = metrics.accuracy_score(targets, preds)
top_2 = metrics.top_k_accuracy_score(targets, confs, k=2)
top_3 = metrics.top_k_accuracy_score(targets, confs, k=3)
top_5 = metrics.top_k_accuracy_score(targets, confs, k=5)
mcc = metrics.matthews_corrcoef(targets, preds)

plot = metrics.ConfusionMatrixDisplay.from_predictions(
    targets,
    preds,
    labels=labels,
    display_labels=display,
    xticks_rotation='vertical',
    ax=ax11,
    values_format='d',
    text_kw={
        'fontsize': 7.0,
    },
)
w, h = plot.confusion_matrix.shape
for row in range(h):
    for col in range(w):
        if plot.confusion_matrix[row, col] == 0:
            plot.text_[row, col].set_text('')

diff = shade_regions(display, ax11, plot)
stats = (
    f'Accuracy Top-1 = {1e2 * accuracy:0.02f}% | '
    f'Top-2 = {1e2 * top_2:0.02f}% | '
    f'Top-3 = {1e2 * top_3:0.02f}% | '
    f'Top-5 = {1e2 * top_5:0.02f}% | '
    f'MCC = {mcc:0.04f}\n'
    f'Shaded Region Accuracy Top-1 = {1e2 * (accuracy + diff):0.04f}'
)
ax11.set_title(f'Confusion Matrix\n{stats}\n[Absolute Values]', y=1.06)

totals0 = plot.confusion_matrix.sum(axis=0)
totals1 = plot.confusion_matrix.sum(axis=1)
plot.ax_.set_xticklabels([f'({value}) {label}' for value, label in zip(totals0, display)])
plot.ax_.set_yticklabels([f'({value}) {label}' for value, label in zip(totals1, display)])

ax12.set_title(f'Confusion Matrix (True Normalized)\n{stats}\n[Percentage Values]', y=1.06)
plot = metrics.ConfusionMatrixDisplay.from_predictions(
    targets,
    preds,
    labels=labels,
    display_labels=display,
    normalize='true',
    xticks_rotation='vertical',
    ax=ax12,
    values_format='0.01f',
    text_kw={
        'fontsize': 5.0,
    },
)
w, h = plot.confusion_matrix.shape
for row in range(h):
    for col in range(w):
        value = plot.confusion_matrix[row, col]
        if value == 0:
            plot.text_[row, col].set_text('')
        else:
            plot.text_[row, col].set_text(f'{100 * value:0.1f}')
shade_regions(display, ax12, plot)

ax13.set_title(f'Confusion Matrix (Predicted Normalized)\n{stats}\n[Percentage Values]', y=1.06)
plot = metrics.ConfusionMatrixDisplay.from_predictions(
    targets,
    preds,
    labels=labels,
    display_labels=display,
    normalize='pred',
    xticks_rotation='vertical',
    ax=ax13,
    values_format='0.01f',
    text_kw={
        'fontsize': 5.0,
    },
)
w, h = plot.confusion_matrix.shape
for row in range(h):
    for col in range(w):
        value = plot.confusion_matrix[row, col]
        if value == 0:
            plot.text_[row, col].set_text('')
        else:
            plot.text_[row, col].set_text(f'{100 * value:0.1f}')

shade_regions(display, ax13, plot)

if custom_index is not None:
    print('\tplotting roundR negative class performance')
    targets_ = [target == custom_index for target in targets]
    confs_ = [conf[custom_index] for conf in confs]
    precision, recall, thresholds_pr = metrics.precision_recall_curve(targets_, confs_)
    thresholds_pr = np.append(thresholds_pr, [1.0])

    for i in range(1, len(precision)):
        precision[i] = max(precision[i], precision[i - 1])

    temp_precision = np.min(precision)
    flags = precision <= temp_precision
    flags_ = np.logical_not(flags)
    temp_recall = np.min(recall[flags])
    temp_threshold = np.max(thresholds_pr[flags])

    precision = np.append([0.0, temp_precision], precision[flags_])
    recall = np.append([temp_recall, temp_recall], recall[flags_])
    thresholds_pr = np.append([0.0, temp_threshold], thresholds_pr[flags_])

    # ap = metrics.average_precision_score(targets_, confs_)
    ap = np.trapz(precision[::-1], x=recall[::-1])
    best_index_pr = np.argmin(
        np.linalg.norm(np.vstack((1.0 - precision, 1.0 - recall)), ord=2, axis=0)
    )
    op_pr = thresholds_pr[best_index_pr]

    ax21.set_title('RoundR Negative Precision-Recall Curve', y=1.09)
    metrics.PrecisionRecallDisplay(precision=precision, recall=recall).plot(
        ax=ax21,
        label=f'MobileNetV3 [AP = {1e2 * ap:0.2f}% | OP = {op_pr:0.04f}]',
    )
    ax21.plot(
        [recall[best_index_pr]],
        [precision[best_index_pr]],
        color='xkcd:gold',
        marker='D',
    )
    ax21.plot([0.9, 0.9], [0.0, 1.0], color='black', linestyle='--', alpha=0.1)
    ax21.legend(
        bbox_to_anchor=(0.0, 1.02, 1.0, 0.102),
        loc=3,
        ncol=2,
        mode='expand',
        borderaxespad=0.0,
    )

    preds_ = (confs_ >= op_pr).astype(np.uint8)
    confusion = metrics.confusion_matrix(targets_, preds_)
    accuracy = metrics.accuracy_score(targets_, preds_)
    f1 = metrics.f1_score(targets_, preds_)
    mcc = metrics.matthews_corrcoef(targets_, preds_)
    stats = (
        f'OP = {op_pr:0.04f} | Accuracy = {1e2 * accuracy:0.02f}% '
        f'| F1 = {f1:0.04f} | MCC = {mcc:0.04f}'
    )
    ax22.set_title(f'RoundR Negative Confusion Matrix\n{stats}', y=1.23)
    metrics.ConfusionMatrixDisplay(confusion).plot(
        ax=ax22,
        values_format=',',
        text_kw={
            'fontsize': 20.0,
        },
    )

    fpr, tpr, thresholds_roc = metrics.roc_curve(targets_, confs_)
    auc = metrics.roc_auc_score(targets_, confs_)
    ax23.set_title('RoundR Negative ROC Curve', y=1.09)
    best_index_roc = np.argmin(np.linalg.norm(np.vstack((fpr, 1.0 - tpr)), ord=2, axis=0))
    op_roc = thresholds_roc[best_index_roc]
    metrics.RocCurveDisplay(fpr=fpr, tpr=tpr).plot(
        ax=ax23,
        label=f'MobileNetV3 [AUC = {1e2 * auc:0.2f}% | OP = {op_roc:0.04f}]',
    )
    ax23.plot([fpr[best_index_roc]], [tpr[best_index_roc]], color='xkcd:gold', marker='D')
    ax23.legend(
        bbox_to_anchor=(0.0, 1.02, 1.0, 0.102),
        loc=3,
        ncol=2,
        mode='expand',
        borderaxespad=0.0,
    )

    preds_ = (confs_ >= op_roc).astype(np.uint8)
    confusion = metrics.confusion_matrix(targets_, preds_)
    accuracy = metrics.accuracy_score(targets_, preds_)
    f1 = metrics.f1_score(targets_, preds_)
    mcc = metrics.matthews_corrcoef(targets_, preds_)
    stats = (
        f'OP = {op_roc:0.04f} | Accuracy = {1e2 * accuracy:0.02f}% '
        f'| F1 = {f1:0.04f} | MCC = {mcc:0.04f}'
    )
    ax24.set_title(f'RoundR Negative Confusion Matrix\n{stats}', y=1.23)
    metrics.ConfusionMatrixDisplay(confusion).plot(
        ax=ax24,
        values_format=',',
        text_kw={
            'fontsize': 20.0,
        },
    )

performance_path = f'performance.{tag}.png'
plt.savefig(performance_path, dpi=150, bbox_inches='tight')
plt.close()
print(f'Saved performance plot: {performance_path}')

# error_path = f'/data/errors/roundC{roundC}/{tag}'

# src_paths = []
# dst_paths = []
# error_paths = []
# error_labels = []
# for target, pred, path in sorted(zip(targets, preds, paths)):
#     if target != pred:
#         src_path = path
#         src_filename = os.path.split(src_path)[1]

#         dst_path = f'{error_path}/{src_filename}'
#         dst_path = dst_path.replace(
#             f'.{EXT}', (f'_target_{target}' f'_pred_{pred}' f'.{EXT}')
#         )

#         src_paths.append(src_path)
#         dst_paths.append(dst_path)

#         error_paths.append(path)
#         error_labels.append(mapping['forward'][str(int(target))])

# if errors:
#     print(f'Writing classification errors to: {error_path}')

#     if os.path.exists(error_path):
#         shutil.rmtree(error_path)
#     os.makedirs(error_path)

#     for src_path, dst_path in tqdm.tqdm(list(zip(src_paths, dst_paths))):
#         shutil.copyfile(src_path, dst_path)

# return error_paths, error_labels
