"""A stand-in for pomegranate 0.14's GeneralMixtureModel, the one class ABIDES's RMSC04 uses
(abides_markets/models/order_size_model.py): pomegranate 0.14 has no build for Apple silicon or
for Python past 3.8.

It reads the same JSON and samples the same mixture: a component chosen by its weight, then a
draw from it (log-normal or normal, with pomegranate's parameter order: mu and sigma of the log
for LogNormalDistribution, mean and sd for NormalDistribution). Draws come from the
RandomState passed in, so a seeded run repeats; they are not pomegranate's own draws.

Run by export.py under ABIDES's Python only, never imported by the repo's code or tests.
"""

import json

import numpy as np


class GeneralMixtureModel:
    def __init__(self, components, weights):
        self.components = components
        self.weights = np.asarray(weights, dtype=float) / sum(weights)

    @classmethod
    def from_json(cls, text):
        spec = json.loads(text)
        components = [(d["name"], tuple(d["parameters"])) for d in spec["distributions"]]
        return cls(components, spec["weights"])

    def sample(self, n=None, random_state=None):
        rng = random_state if random_state is not None else np.random
        name, (a, b) = self.components[rng.choice(len(self.components), p=self.weights)]
        if name == "LogNormalDistribution":
            return float(rng.lognormal(a, b))
        if name == "NormalDistribution":
            return float(rng.normal(a, b))
        raise ValueError(f"unsupported component {name}")
