"""Preparation functions for v1_train."""

import os
import pickle

import click
import numba
import numpy as np

WORKERS = 8
SUBSAMPLE = 1

# pip install click numba


def load_image(path):
    import cv2

    img = cv2.imread(path)

    assert img is not None

    return img


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


@numba.njit(fastmath=True, nogil=True)
def worker_mean_numba(img):
    t, c = img.shape
    pixels = 0
    means = np.zeros(c, dtype=np.float64)
    for index in range(0, t, SUBSAMPLE):
        pixel = img[index]
        if pixel.sum() > 0:
            pixels += 1
            means += pixel
    return pixels, means


@numba.njit(fastmath=True, nogil=True)
def worker_stddev_numba(img, mean):
    t, c = img.shape
    stddevs = np.zeros(c, dtype=np.float64)
    for index in range(0, t, SUBSAMPLE):
        pixel = img[index]
        if pixel.sum() > 0:
            stddevs += (pixel - mean) ** 2
    return stddevs


def worker_mean(path):
    img = load_image(path)

    img_shape = img.shape
    h, w, c = img_shape

    img = img.reshape(-1, c)
    pixels, means = worker_mean_numba(img)

    data = {
        'shape': img_shape,
        'pixels': pixels,
        'means': means,
    }
    return path, data


def worker_stddev(inputs):
    path, mean = inputs

    img = load_image(path)

    img_shape = img.shape
    h, w, c = img_shape

    img = img.reshape(-1, c)
    stddevs = worker_stddev_numba(img, mean)

    data = {
        'stddevs': stddevs,
    }
    return path, data


def compute_mean_stddev():
    from pathlib import Path
    import pickle

    import tqdm

    datas_cache = 'data.pkl'
    print(f'Ensuring pixel mean values are in {datas_cache}')

    paths = Path('spectrograms').rglob('*.jpg')
    paths = [str(path.absolute()) for path in paths]

    sizes = [os.path.getsize(path) for path in paths]
    ordering = np.argsort(sizes)
    paths = np.array(paths)[ordering].tolist()

    if os.path.exists(datas_cache):
        datas = pickle.load(open(datas_cache, 'rb'))
    else:
        datas = {}

    inputs = [path for path in paths if 'means' not in datas.get(path, {})]
    chunks = np.array_split(inputs, 10)  # Work on the list in chunks of 10%
    for index, chunk in tqdm.tqdm(enumerate(chunks), total=len(chunks)):
        if index < 8:
            workers = WORKERS
        else:
            # For last 20%, slow down by a factor of 2
            workers = WORKERS // 2
        parallel(
            worker_mean,
            chunk,
            datas,
            workers=max(1, workers),
            threaded=False,
            desc='mean',
        )
        pickle.dump(datas, open(datas_cache, 'wb'))

    print(f'Ensuring pixel stddev values are in {datas_cache}')
    means = np.zeros(3, dtype=np.float64)
    pixels = 0

    for path in paths:
        data = datas[path]
        means += data['means']
        pixels += data['pixels']

    mean = means / pixels
    mean = mean.astype(np.float32)

    inputs = [path for path in paths if 'stddevs' not in datas.get(path, {})]
    chunks = np.array_split(inputs, 10)  # Work on the list in chunks of 10%
    for index, chunk in tqdm.tqdm(enumerate(chunks), total=len(chunks)):
        if index < 8:
            workers = WORKERS // 2
        else:
            # For last 20%, slow down by a factor of 4
            workers = WORKERS // 4
        chunk_ = [(path, mean) for path in chunk]
        parallel(
            worker_stddev,
            chunk_,
            datas,
            workers=max(1, workers),
            threaded=False,
            desc='stddev',
        )
        pickle.dump(datas, open(datas_cache, 'wb'))

    stddevs = np.zeros(3, dtype=np.float64)

    for path in paths:
        data = datas[path]

        stddevs += data['stddevs']

    stddev = stddevs / pixels
    stddev = np.sqrt(stddev)
    stddev = stddev.astype(np.float32)

    mean_ = mean / 255.0
    stddev_ = stddev / 255.0

    stats = {
        'mean': {
            'absolute': tuple(mean),
            'percent': tuple(mean_),
        },
        'stddev': {
            'absolute': tuple(stddev),
            'percent': tuple(stddev_),
        },
    }
    stats_cache = 'stats.pkl'
    pickle.dump(stats, open(stats_cache, 'wb'))
    print(f'Saved recommended pixel values to {stats_cache}')

    print_global_recommendations()


def print_global_recommendations():
    stats_cache = 'stats.pkl'
    stats = pickle.load(open(stats_cache, 'rb'))

    mean = stats['mean']['absolute']
    mean_ = stats['mean']['percent']
    stddev = stats['stddev']['absolute']
    stddev_ = stats['stddev']['percent']

    print('\n' + '-' * 60)
    print('Recommended values')
    print(
        f'\t  Absolute: ({mean[0]:0.04f}, {mean[1]:0.04f}, {mean[2]:0.04f}) '
        f'+/- ({stddev[0]:0.04f}, {stddev[1]:0.04f}, {stddev[2]:0.04f})'
    )
    print(
        f'\tPercentage: (  {mean_[0]:0.04f},   {mean_[1]:0.04f},   {mean_[2]:0.04f}) '
        f'+/- ( {stddev_[0]:0.04f},  {stddev_[1]:0.04f},  {stddev_[2]:0.04f})'
    )
    print('-' * 60)


def compute_partition(split=0.8):
    import os
    from pathlib import Path
    import random
    import shutil

    from PIL import Image
    import tqdm

    paths = Path('spectrograms').rglob('*.jpg')
    paths = [str(path.absolute()) for path in paths]

    labels = {}
    for path in paths:
        path_ = path.split('/')
        label = path_[-2]
        if label not in labels:
            labels[label] = []
        labels[label].append(path)

    data = []
    for label in tqdm.tqdm(labels):
        paths = labels[label]
        pixels = 0
        for path in paths:
            image = Image.open(path)
            w, h = image.size
            assert h == 300
            pixels += w

        data.append((len(paths), pixels, label))

    data = sorted(data)
    print(data)

    train_path = 'train'
    val_path = 'val'
    if not os.path.exists(train_path):
        os.mkdir(train_path)
    if not os.path.exists(val_path):
        os.mkdir(val_path)

    random.seed(1)
    for label in tqdm.tqdm(sorted(labels)):
        train_path_ = os.path.join(train_path, label)
        val_path_ = os.path.join(val_path, label)

        if not os.path.exists(train_path_):
            os.mkdir(train_path_)
        if not os.path.exists(val_path_):
            os.mkdir(val_path_)

        paths = labels[label]
        random.shuffle(paths)

        assert len(paths) > 1
        index = max(1, int(round(len(paths) * split)))

        train_paths = paths[:index]
        val_paths = paths[index:]
        assert len(train_paths) > 0
        assert len(val_paths) > 0
        assert len(set(train_paths) & set(val_paths)) == 0

        for src in train_paths:
            _, filename = os.path.split(src)
            dst = os.path.join(train_path_, filename)
            shutil.copyfile(src, dst)

        for src in val_paths:
            _, filename = os.path.split(src)
            dst = os.path.join(val_path_, filename)
            shutil.copyfile(src, dst)


@click.group(name='preparation')
def main():
    pass


@main.command('compute')
def compute():
    compute_mean_stddev()


@main.command('recommendation')
def recommendation():
    print_global_recommendations()


@main.command('partition')
def partition():
    compute_partition()


if __name__ == '__main__':
    import sys

    sys.exit(main())  # pragma: no cover
