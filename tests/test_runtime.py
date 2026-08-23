from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from time import sleep

import torch

from phasenox.runtime import ModelRepository, ModelRuntime
from phasenox.runtime.loader import ModelLoader
from phasenox.runtime.models import LoadedModelAssets


class FakeModel:
    def __init__(self) -> None:
        self.devices: list[object] = []

    def to(self, device, dtype=None):
        self.devices.append(device)
        return self


class FakeLoader:
    def __init__(self) -> None:
        self.calls = 0
        self._lock = Lock()

    def load(self, spec, **kwargs) -> LoadedModelAssets:
        with self._lock:
            self.calls += 1
        sleep(0.02)
        return LoadedModelAssets(model=FakeModel())


class FakeTransformersModel(FakeModel):
    received_options = None

    @classmethod
    def from_pretrained(cls, source, **options):
        cls.received_options = options
        return cls()


def test_runtime_loads_one_asset_for_concurrent_requests() -> None:
    loader = FakeLoader()
    runtime = ModelRuntime(loader=loader, device=torch.device("cpu"))

    def load():
        return runtime.load(model_name="fake", model_cls=FakeModel, backend="fake")

    with ThreadPoolExecutor(max_workers=8) as executor:
        assets = list(executor.map(lambda _: load(), range(8)))

    assert loader.calls == 1
    assert len({id(item) for item in assets}) == 1


def test_cache_identity_includes_backend_and_options() -> None:
    loader = FakeLoader()
    runtime = ModelRuntime(loader=loader, device=torch.device("cpu"))

    runtime.load(model_name="fake", model_cls=FakeModel, backend="first")
    runtime.load(model_name="fake", model_cls=FakeModel, backend="second")
    runtime.load(
        model_name="fake",
        model_cls=FakeModel,
        backend="first",
        tokenizer_options={"padding_side": "left"},
    )

    assert loader.calls == 3


def test_unload_releases_runtime_owned_assets() -> None:
    loader = FakeLoader()
    runtime = ModelRuntime(loader=loader, device=torch.device("cpu"))
    assets = runtime.load(model_name="fake", model_cls=FakeModel, backend="fake")
    spec = runtime.available_models()[0]

    runtime.unload(spec)

    assert assets.model is None
    assert runtime.available_models() == ()


def test_loader_receives_repository_by_injection() -> None:
    repository = ModelRepository(root="test-models")
    loader = ModelLoader(repository)

    assert loader.repository is repository


def test_device_map_is_passed_to_loader_without_runtime_placement() -> None:
    runtime = ModelRuntime(
        loader=ModelLoader(ModelRepository(root="test-models")),
        device=torch.device("cpu"),
    )

    assets = runtime.load(
        model_name="large-model",
        model_cls=FakeTransformersModel,
        model_options={"device_map": "auto"},
    )

    assert FakeTransformersModel.received_options["device_map"] == "auto"
    assert assets.model.devices == []
