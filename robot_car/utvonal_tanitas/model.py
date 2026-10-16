# Az útvonalkövető neurális háló felépítése két motorkimenettel.

import torch
import torch.nn as nn


# Modell
class FlashFireCNN(nn.Module):
    def __init__(self):
        super(FlashFireCNN, self).__init__()

        # Jellemzőkinyerés
        self.conv_layers = nn.Sequential(
            nn.Conv2d(3, 24, kernel_size=5, stride=2),
            nn.ReLU(),
            nn.Conv2d(24, 32, kernel_size=5, stride=2),
            nn.ReLU(),
            nn.Conv2d(32, 64, kernel_size=5, stride=2),
            nn.ReLU(),
            nn.Conv2d(64, 64, kernel_size=3, stride=1),
            nn.ReLU(),
            nn.Conv2d(64, 64, kernel_size=3, stride=1),
            nn.ReLU()
        )

        # Kimenet
        self.fc_layers = nn.Sequential(
            nn.Flatten(),
            nn.Linear(8 * 13 * 64, 128),
            nn.ReLU(),
            nn.Linear(128, 128),
            nn.ReLU(),
            nn.Linear(128, 2)
        )

    # Feldolgozás
    def forward(self, inputs):
        inputs = self.conv_layers(inputs)
        inputs = self.fc_layers(inputs)
        return inputs
