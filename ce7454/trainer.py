import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader
from focalloss import FocalLossV1 as FocalLoss
from tqdm import tqdm


def cosine_annealing(step, total_steps, lr_max, lr_min):
    return lr_min + (lr_max -
                     lr_min) * 0.5 * (1 + np.cos(step / total_steps * np.pi))


class BaseTrainer:
    def __init__(self,
                 net: nn.Module,
                 train_loader: DataLoader,
                 learning_rate: float = 0.1,
                 momentum: float = 0.9,
                 weight_decay: float = 0.0005,
                 epochs: int = 100) -> None:
        self.net = net
        self.train_loader = train_loader

        self.optimizer = torch.optim.SGD(
            net.parameters(),
            learning_rate,
            momentum=momentum,
            weight_decay=weight_decay,
            nesterov=True,
        )

        self.scheduler = torch.optim.lr_scheduler.LambdaLR(
            self.optimizer,
            lr_lambda=lambda step: cosine_annealing(
                step,
                epochs * len(train_loader),
                1,  # since lr_lambda computes multiplicative factor
                1e-6 / learning_rate,
            ),
        )

    def train_epoch(self):
        self.net.train()  # enter train mode

        loss_avg = 0.0
        train_dataiter = iter(self.train_loader)

        for train_step in tqdm(range(1, len(train_dataiter) + 1)):
            # for train_step in tqdm(range(1, 5)):
            data, target = next(train_dataiter)
            data = data.cuda()
            target = target.cuda()
            # forward
            logits = self.net(data)
            del data
            #loss = F.binary_cross_entropy_with_logits(logits,
            #                                          target,
            #                                          reduction='sum')
            loss_fn = FocalLoss(reduction="sum")
            loss = loss_fn(logits, target)
            # backward
            del target
            del logits
            self.optimizer.zero_grad()
            loss.backward()
            self.optimizer.step()
            self.scheduler.step()

            # exponential moving average, show smooth values
            with torch.no_grad():
                loss_avg = loss_avg * 0.8 + float(loss) * 0.2

        metrics = {}
        metrics['train_loss'] = loss_avg

        return metrics
