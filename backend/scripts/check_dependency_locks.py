#!/usr/bin/env python3
"""Validate product and CI dependency locks without resolving the network."""
from __future__ import annotations

import re
import sys
from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from packaging.version import Version


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PIN_PATTERN = re.compile(r"^([A-Za-z0-9_.-]+)==([^\s;\\]+)")


def _read_pins(path: Path) -> dict[str, str]:
    pins: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = PIN_PATTERN.match(line)
        if not match:
            continue
        name = canonicalize_name(match.group(1))
        version = match.group(2)
        if name in pins and pins[name] != version:
            raise ValueError(
                f"{path.name} pins {name} to both {pins[name]} and {version}"
            )
        pins[name] = version
    if not pins:
        raise ValueError(f"{path.name} contains no exact pins")
    return pins


def _read_direct_requirements(path: Path) -> list[Requirement]:
    requirements: list[Requirement] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if line:
            requirements.append(Requirement(line))
    return requirements


def main() -> int:
    product_source = BACKEND_ROOT / "requirements.txt"
    product_lock = BACKEND_ROOT / "requirements.lock.txt"
    ci_source = BACKEND_ROOT / "requirements-ci.in"
    ci_lock = BACKEND_ROOT / "requirements-ci.lock.txt"

    try:
        product_pins = _read_pins(product_lock)
        ci_pins = _read_pins(ci_lock)
        direct_requirements = _read_direct_requirements(product_source)

        for requirement in direct_requirements:
            name = canonicalize_name(requirement.name)
            pinned = product_pins.get(name)
            if pinned is None:
                raise ValueError(
                    f"{product_lock.name} does not pin direct dependency {requirement.name}"
                )
            if requirement.specifier and Version(pinned) not in requirement.specifier:
                raise ValueError(
                    f"{requirement} is incompatible with locked {requirement.name}=={pinned}"
                )

        for name, product_version in product_pins.items():
            ci_version = ci_pins.get(name)
            if ci_version != product_version:
                raise ValueError(
                    f"CI lock drift for {name}: product={product_version}, ci={ci_version}"
                )

        expected_ci_source = "-r requirements.lock.txt\n\npytest==8.4.2\n"
        if ci_source.read_text(encoding="utf-8") != expected_ci_source:
            raise ValueError(
                "requirements-ci.in must contain only the product lock plus pytest==8.4.2"
            )
        if ci_pins.get("pytest") != "8.4.2":
            raise ValueError("requirements-ci.lock.txt must pin pytest==8.4.2")
    except (OSError, ValueError) as exc:
        print(f"Dependency lock check failed: {exc}", file=sys.stderr)
        return 1

    print(
        "Dependency locks are consistent: "
        f"product={len(product_pins)} pins, ci={len(ci_pins)} pins"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
