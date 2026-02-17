from __future__ import annotations

import importlib.util
import inspect
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

from fastapi import HTTPException

from app.pricing_calculators.base import BasePriceCalculator


@dataclass(frozen=True)
class CalculatorDescriptor:
    file: str
    class_name: str
    description: str


def calculators_root() -> Path:
    return Path(__file__).resolve().parents[1] / "pricing_calculators"


def _safe_file_path(file_name: str) -> Path:
    root = calculators_root().resolve()
    candidate = (root / file_name).resolve()
    if candidate.suffix != ".py":
        raise HTTPException(status_code=400, detail="Calculator file must be a .py module")
    if root not in candidate.parents:
        raise HTTPException(status_code=400, detail="Calculator file path is outside calculators folder")
    if not candidate.exists():
        raise HTTPException(status_code=404, detail="Calculator file not found")
    return candidate


def _load_module(file_path: Path) -> ModuleType:
    module_name = f"app.pricing_calculators.runtime_{file_path.stem}"
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise HTTPException(status_code=400, detail="Cannot load calculator module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _iter_calculator_classes(module: ModuleType) -> list[type[BasePriceCalculator]]:
    classes: list[type[BasePriceCalculator]] = []
    for _, cls in inspect.getmembers(module, inspect.isclass):
        if cls.__module__ != module.__name__:
            continue
        if not issubclass(cls, BasePriceCalculator) or cls is BasePriceCalculator:
            continue
        classes.append(cls)
    return classes


def list_available_calculators() -> list[CalculatorDescriptor]:
    root = calculators_root()
    if not root.exists():
        return []
    descriptors: list[CalculatorDescriptor] = []
    for file_path in sorted(root.glob("*.py")):
        if file_path.name.startswith("_") or file_path.name == "base.py":
            continue
        module = _load_module(file_path)
        for cls in _iter_calculator_classes(module):
            descriptors.append(
                CalculatorDescriptor(
                    file=file_path.name,
                    class_name=cls.__name__,
                    description=str(getattr(cls, "description", cls.__doc__ or "")),
                )
            )
    return descriptors


def load_calculator_instance(file_name: str, class_name: str) -> BasePriceCalculator:
    file_path = _safe_file_path(file_name)
    module = _load_module(file_path)
    classes = {cls.__name__: cls for cls in _iter_calculator_classes(module)}
    if class_name not in classes:
        raise HTTPException(status_code=404, detail="Calculator class not found in file")
    cls = classes[class_name]
    try:
        return cls()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Calculator init failed: {exc}") from exc


def run_calculator(
    *,
    file_name: str,
    class_name: str,
    current_amount,
    params: dict[str, Any],
    context: dict[str, Any],
):
    calculator = load_calculator_instance(file_name, class_name)
    try:
        return calculator.calculate(
            current_amount=current_amount,
            params=params,
            context=context,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Calculator execution failed: {exc}") from exc

