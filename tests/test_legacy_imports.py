"""Pins that legacy/ stays runnable, not just archived.

`legacy/` holds work that came first and is still live — imported by
`audit_bridge`, exercised by the rest of the suite, runnable on its own.
Nothing enforced that. `validity_weighted_reweighting` used a flat import
of its sibling and had been unimportable from the repository root since
the day it landed, for three months, because no test imported it.

These tests are the enforcement: every module under `legacy/` must import
from the root and keep its demo entry point. If a future move breaks one,
the suite says so instead of the folder quietly rotting into an archive.
"""

import importlib
import pathlib
import unittest

LEGACY_ROOT = pathlib.Path(__file__).resolve().parent.parent / "legacy"

LEGACY_MODULES = (
    "legacy.business_audit.business_resilience_framework",
    "legacy.dependency_audit.refinery_dependency_graph",
    "legacy.premise_audit.premise_cross_domain_audit",
    "legacy.premise_audit.validity_weighted_reweighting",
    "legacy.substrate_audit.substrate_aware_audit",
)


class LegacyImportTests(unittest.TestCase):
    """Every legacy module imports from the repository root."""

    def test_every_module_imports(self):
        for name in LEGACY_MODULES:
            with self.subTest(module=name):
                self.assertIsNotNone(importlib.import_module(name))

    def test_module_list_covers_every_legacy_source_file(self):
        # A new module added under legacy/ without an entry here would
        # inherit exactly the blind spot this file exists to close.
        on_disk = {
            "legacy." + ".".join(p.relative_to(LEGACY_ROOT).with_suffix("").parts)
            for p in LEGACY_ROOT.rglob("*.py")
            if "__pycache__" not in p.parts and p.name != "__init__.py"
        }
        self.assertEqual(on_disk, set(LEGACY_MODULES))

    def test_every_module_keeps_a_demo_entry_point(self):
        # Each is documented as runnable via `python -m`. That claim is
        # only true while the guard is present.
        for name in LEGACY_MODULES:
            with self.subTest(module=name):
                source = pathlib.Path(
                    importlib.import_module(name).__file__
                ).read_text()
                self.assertIn('if __name__ == "__main__":', source)


class ReweighterSiblingImportTests(unittest.TestCase):
    """The specific breakage that motivated this file (see F-7)."""

    def test_reweighter_reaches_its_sibling_engine(self):
        module = importlib.import_module(
            "legacy.premise_audit.validity_weighted_reweighting"
        )
        engine_module = importlib.import_module(
            "legacy.premise_audit.premise_cross_domain_audit"
        )
        # Same class object, not a second copy loaded under a flat name —
        # two copies would make isinstance checks fail across the boundary.
        self.assertIs(module.PremiseAuditEngine, engine_module.PremiseAuditEngine)

    def test_reweighter_example_builds(self):
        module = importlib.import_module(
            "legacy.premise_audit.validity_weighted_reweighting"
        )
        reweighter = module.build_example()
        self.assertTrue(reweighter.studies)


if __name__ == "__main__":
    unittest.main()
