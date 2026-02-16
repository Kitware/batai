import io
import os
from pathlib import Path
import random
import sys
import warnings

import cv2
import numpy as np
from sklearn.metrics import matthews_corrcoef as metric_func
import torch
from torch.utils import tensorboard
import torchvision
import torchvision.transforms.functional as F
import tqdm

# pip install tensorboard opencv-python-headless scikit-learn torch torchvision tqdm

torch._C._jit_set_profiling_mode(False)
torch._C._jit_set_profiling_executor(False)

torch.backends.cudnn.benchmark = True


class Data:
    def __init__(self, labels, train, val):
        self.labels = labels
        self.train = train
        self.val = val


class Transforms(torch.nn.Module):
    def __init__(
        self,
        mean=(0.0, 0.0, 0.0),
        stddev=(1.0, 1.0, 1.0),
        noise=True,
    ):
        super().__init__()
        self.noise = noise

        self.mean = mean
        self.stddev = stddev

        self.jitter = torchvision.transforms.ColorJitter(
            brightness=np.mean(self.stddev),
            contrast=np.mean(self.stddev),
            saturation=np.mean(self.stddev),
            hue=0.0,
        )
        self.poster = torchvision.transforms.RandomPosterize(bits=2)
        self.blur = torchvision.transforms.GaussianBlur(3)

    def forward(self, imgs):
        imgs = imgs.permute((0, 3, 1, 2))

        imgs = F.center_crop(imgs, [224])

        if self.noise:
            imgs = self.jitter(imgs)

            imgs = self.poster(imgs)

            cond = torch.rand(1)
            if cond[0] <= 0.5:
                imgs = self.blur(imgs)

        imgs = F.convert_image_dtype(imgs, torch.float16)
        imgs = F.normalize(imgs, mean=self.mean, std=self.stddev)

        return imgs


class Dataset(torch.utils.data.Dataset):
    def __init__(
        self,
        paths,
        ratio=1,
        sample=True,
        epochs=None,
        mean=(0.0, 0.0, 0.0),
        stddev=(1.0, 1.0, 1.0),
        noise=True,
    ):
        self.paths = paths
        self.keys = sorted(self.paths.keys())
        self.transforms = Transforms(
            mean=mean,
            stddev=stddev,
            noise=noise,
        )
        self.transforms = torch.jit.script(self.transforms)
        self.epoch = 0
        self.gen = torch.Generator()

        if ratio < 0:
            ratio = 1

        counts = {}
        index = 0
        self.mapping = {}
        self.assignments = {}
        for target in self.keys:
            if self.paths[target] is not None:
                total = len(self.paths[target])
                counts[target] = total
                for paths_index in range(total):
                    assignment = (target, paths_index)
                    self.mapping[index] = assignment
                    self.assignments[assignment] = index
                    index += 1

        self.smallest = max(1, min(counts.values())) * ratio

        self.weights = torch.tensor([1.0] * len(self.keys))
        for key in self.keys:
            value = counts.get(key, None)
            if value in [None, 0]:
                continue
            self.weights[key] = min(10.0, max(1.0, self.smallest / value))

        if sample:
            self.total = sum([min(count, self.smallest) for count in counts.values()])
            self.views = {}
        else:
            self.total = sum(counts.values())
            self.views = None

        if epochs:
            for epoch in range(epochs + 1):
                self.ensure_view(epoch)

    def transform(self, index):
        if self.views is None:
            return index

        self.ensure_view(self.epoch)

        return self.views[self.epoch][index]

    def ensure_view(self, epoch):
        if self.views is None:
            return

        if epoch not in self.views:
            accumulator = []
            for target in self.keys:
                self.gen.manual_seed(target + epoch)

                if self.paths[target] is not None:
                    total = len(self.paths[target])
                    values = torch.randperm(total, generator=self.gen).tolist()
                    # values = torch.arange(total).tolist()
                    trim = min(len(values), self.smallest)
                    values = values[:trim]

                    for value in values:
                        assignment = (target, value)
                        accumulator.append(self.assignments[assignment])

            values = torch.randperm(len(accumulator), generator=self.gen).tolist()
            # values = torch.arange(len(accumulator)).tolist()
            self.views[epoch] = [accumulator[value] for value in values]

    def __getitem__(self, index):
        index = self.transform(index)

        target, paths_index = self.mapping[index]
        path = self.paths[target][paths_index]

        raw = cv2.imread(path)

        h, w, c = raw.shape
        stretch = random.uniform(0.9, 1.1)
        window = int(h * 2 * stretch)
        if w < window:
            canvas = np.zeros((h, window, 3), dtype=raw.dtype)
            margin = window - w
            index = random.randint(0, margin)
            canvas[:, index : index + w, :] = raw
        else:
            index = random.randint(0, w - window)
            canvas = raw[:, index : index + window, :]

        img = cv2.resize(canvas, (224, 224), interpolation=cv2.INTER_LANCZOS4)

        return img, target

    def __len__(self):
        return self.total

    def set_epoch(self, epoch):
        self.epoch = epoch


class Sampler(torch.utils.data.distributed.DistributedSampler):
    def set_epoch(self, epoch):
        super().set_epoch(epoch)
        self.dataset.set_epoch(epoch)


class Trainer:
    def __init__(
        self,
        data,
        model: torch.nn.Module,
        criterion,
        optimizer: torch.optim.Optimizer,
        save: str,
        samples: int = 3,
        log_dir=None,
    ) -> None:
        self.data = data
        self.model = model
        self.criterion = criterion
        self.optimizer = optimizer
        self.save = save
        self.samples = samples

        self.epoch = 0
        self.loss = None
        self.metric = None

        self.scaler = torch.amp.GradScaler()
        self.gpu_id = int(os.environ['LOCAL_RANK'])
        self.reporter = self.gpu_id == 0

        # Send to device
        self.device = f'cuda:{self.gpu_id}'
        self.model = self.model.to(self.device)
        self.data.train.dataset.transforms = self.data.train.dataset.transforms.to(self.device)
        self.data.val.dataset.transforms = self.data.val.dataset.transforms.to(self.device)
        self.weights = self.data.train.dataset.weights.to(self.device)

        # Load save
        self._load_save()

        # Setup DDP
        self.model = torch.nn.parallel.DistributedDataParallel(self.model, device_ids=[self.device])

        # Setup Tensorboard
        if self.reporter:
            self.writer = tensorboard.SummaryWriter(log_dir=log_dir)
        else:
            self.writer = None

    def _save_save(self, epoch, loss, metric, saturated=False):
        data = {
            'state': self.model.module.state_dict(),
            'labels': dict(enumerate(self.data.labels)),
            'epoch': epoch,
            'loss': loss,
            'metric': metric,
        }
        torch.save(data, self.save)
        print('', file=sys.stderr)
        saturated_str = '[saturated] ' if saturated else ''
        print(
            f'\nSaved at validation loss {loss:0.03f} '
            f'(MCC {100.0 * metric:0.1f}) '
            f'{saturated_str}'
            f'to {self.save}'
        )

    def _load_save(self):
        if not os.path.exists(self.save):
            return

        print(f'Loading from {self.save}')
        data = torch.load(self.save, map_location=self.device)

        state = data.get('state', None)
        if state:
            self.model.load_state_dict(state)
        labels = data.get('labels', None)
        if labels:
            assert self.data.labels == sorted(labels.values())
        self.epoch = data.get('epoch', 0)

        print('Loaded previous loss and metric')
        self.loss = data.get('loss', None)
        self.metric = data.get('metric', None)

        print(
            f'[G{self.gpu_id}] Resuming from epoch {self.epoch} '
            f'[lr={self._get_lr():0.05f}, val loss {self.loss:0.03f}, '
            f'MCC {100 * self.metric:0.1f}]'
        )

    def _run_backward(self, inputs, targets, transform_func):
        self.optimizer.zero_grad(set_to_none=True)

        outputs, loss = self._run_forward(inputs, targets, transform_func)

        self.scaler.scale(loss).backward()
        self.scaler.step(self.optimizer)

        self.scaler.update()

        return outputs, loss

    def _run_forward(self, inputs, targets, transform_func):
        inputs = inputs.to(self.device, non_blocking=True)
        targets = targets.to(self.device, non_blocking=True)

        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', category=UserWarning)
            with torch.cuda.amp.autocast(dtype=torch.float16):
                outputs = self.model(transform_func(inputs))
                loss = self.criterion(outputs, targets, weight=self.weights)

        return outputs, loss

    def _run_epoch(self, epoch, global_progress):
        self.data.train.sampler.set_epoch(epoch)
        self.data.val.sampler.set_epoch(epoch)

        self.model.train()

        with tqdm.tqdm(total=len(self.data.train), disable=not self.reporter) as progress:
            loss = 0.0
            total = 0
            targets = None
            preds = None
            metric = 0.0

            for inputs_, targets_ in self.data.train:
                outputs_, loss_ = self._run_backward(
                    inputs_, targets_, self.data.train.dataset.transforms
                )

                loss += 100.0 * loss_.item() * len(inputs_)  # multiply by 100 for easier monitoring
                total += len(inputs_)

                _, preds_ = torch.max(torch.nn.functional.softmax(outputs_, dim=1), 1)

                targets_ = targets_.cpu().numpy()
                preds_ = preds_.cpu().numpy()
                targets = targets_ if targets is None else np.append(targets, targets_)
                preds = preds_ if preds is None else np.append(preds, preds_)
                metric = metric_func(targets, preds)

                progress.set_description(
                    f'[G{self.gpu_id}-E{epoch:04d}-Train] '
                    f'ETA {global_progress} '
                    f'Loss {loss / total:0.3f} '
                    f'MCC {100.0 * metric:0.1f}'
                )
                progress.update(1)
            sys.stderr.flush()

            train_loss = loss / total
            train_metric = metric

        self.model.eval()

        with tqdm.tqdm(
            total=len(self.data.val) * self.samples, disable=not self.reporter
        ) as progress:
            loss = 0.0
            total = 0
            targets = None
            preds = None
            metric = 0.0

            for _ in range(self.samples):
                for inputs_, targets_ in self.data.val:
                    with torch.no_grad():
                        outputs_, loss_ = self._run_forward(
                            inputs_, targets_, self.data.val.dataset.transforms
                        )

                    loss += (
                        100.0 * loss_.item() * len(inputs_)
                    )  # multiply by 100 for easier monitoring
                    total += len(inputs_)

                    _, preds_ = torch.max(torch.nn.functional.softmax(outputs_, dim=1), 1)

                    targets_ = targets_.cpu().numpy()
                    preds_ = preds_.cpu().numpy()
                    targets = targets_ if targets is None else np.append(targets, targets_)
                    preds = preds_ if preds is None else np.append(preds, preds_)
                    metric = metric_func(targets, preds)

                    progress.set_description(
                        f'[G{self.gpu_id}-E{epoch:04d}-Val  ] '
                        f'ETA {global_progress} '
                        f'Loss {loss / total:0.3f} '
                        f'MCC {100.0 * metric:0.1f}'
                    )
                    progress.update(1)
            sys.stderr.flush()

            val_loss = loss / total
            val_metric = metric

        return train_loss, train_metric, val_loss, val_metric

    def _get_lr(self):
        return self.optimizer.param_groups[0]['lr']

    def train(self, epochs=20, keep='metric', point=1.0):
        max_epochs = self.epoch + epochs

        capture = io.StringIO()
        with tqdm.tqdm(
            total=epochs,
            disable=not self.reporter,
            bar_format='{n_fmt}/{total_fmt} [{elapsed}<{remaining}]',
            leave=False,
            file=capture,
        ) as progress:
            for epoch in range(self.epoch, max_epochs):
                epoch_values = self._run_epoch(epoch, progress)
                train_loss, train_metric, val_loss, val_metric = epoch_values

                if self.reporter:
                    condition_loss = not self.loss or val_loss < self.loss
                    condition_metric = not self.metric or val_metric > self.metric
                    condition = condition_metric if keep == 'metric' else condition_loss

                    saturated = self.metric and self.metric > point
                    if saturated:
                        # Prevent metric oversaturation, switch to minifying loss once
                        # we reach the saturation point
                        condition = condition_loss and val_metric >= point

                    if condition:
                        self.loss = val_loss
                        self.metric = val_metric
                        self._save_save(epoch, val_loss, val_metric, saturated=saturated)

                    if self.writer:
                        self.writer.add_scalar('learning_rate', self._get_lr(), epoch)
                        self.writer.add_scalar('train/loss', train_loss, epoch)
                        self.writer.add_scalar('val/loss', val_loss, epoch)
                        self.writer.add_scalar('train/mcc', train_metric, epoch)
                        self.writer.add_scalar('val/mcc', val_metric, epoch)

                progress.update(1)
                sys.stderr.flush()

        capture.close()


def load_paths(path):
    if not os.path.exists(path):
        return None

    paths = Path(path).rglob('*.jpg')
    paths = [str(path.absolute()) for path in paths]

    return paths


def load_data(
    path,
    labels,
    batch=16,
    workers=4,
    prefetch=2,
    ratio=10,
    epochs=20,
    sample=True,
    mean=(0.0, 0.0, 0.0),
    stddev=(1.0, 1.0, 1.0),
    noise=True,
):
    paths = {index: load_paths(f'{path}/{label}/') for index, label in enumerate(labels)}
    dataset = Dataset(
        paths,
        ratio=ratio,
        sample=sample,
        epochs=epochs,
        mean=mean,
        stddev=stddev,
        noise=noise,
    )

    gpu_id = int(os.environ['LOCAL_RANK'])
    device = f'cuda:{gpu_id}'
    data = torch.utils.data.DataLoader(
        dataset,
        batch_size=batch,
        pin_memory=True,
        pin_memory_device=device,
        shuffle=False,
        num_workers=workers,
        persistent_workers=True,
        prefetch_factor=prefetch,
        sampler=Sampler(dataset, shuffle=False),
    )

    return data


def main():
    from datetime import datetime

    torch.distributed.init_process_group(backend='nccl')

    labels = []
    for tag in ['train', 'val']:
        labels += [temp.name for temp in Path(f'{tag}').iterdir() if temp.is_dir()]
    labels = sorted(set(labels))

    mean = [0.0932, 0.0255, 0.0512]
    stddev = [0.1057, 0.0543, 0.1170]

    data = Data(
        labels=labels,
        train=load_data(
            'train',
            labels,
            mean=mean,
            stddev=stddev,
            noise=True,
        ),
        val=load_data(
            'val',
            labels,
            sample=False,
            mean=mean,
            stddev=stddev,
            noise=False,
        ),
    )

    model = torchvision.models.mobilenet_v3_large(
        weights=torchvision.models.MobileNet_V3_Large_Weights.IMAGENET1K_V2
    )
    model.classifier = torch.nn.Sequential(
        torch.nn.Linear(960, 64),
        torch.nn.Hardswish(inplace=True),
        torch.nn.Dropout(p=0.2, inplace=True),
        torch.nn.Linear(64, len(labels)),
    )

    lr = 1e-3
    criterion = torch.nn.functional.cross_entropy
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-5)

    saves = 'save.pth'

    now_str = datetime.now().strftime('%m-%d-%Y-%H-%M-%S')
    log_dir = f'runs/{now_str}'

    trainer = Trainer(data, model, criterion, optimizer, saves, log_dir=log_dir)

    try:
        trainer.train()
    except (Exception, KeyboardInterrupt):
        raise
    finally:
        if trainer.writer:
            trainer.writer.close()
        torch.distributed.destroy_process_group()


if __name__ == '__main__':
    """
    CUDA_VISIBLE_DEVICES=0,1,2,3 OMP_NUM_THREADS=1 torchrun --standalone --nproc_per_node=gpu mlflow.py
    """  # noqa: E501
    main()
