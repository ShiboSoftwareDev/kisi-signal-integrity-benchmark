"""Check scientific reproducibility and retain the experiment's known failures."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from si_benchmark import analysis as a

ROOT = Path(__file__).resolve().parents[1]


class BenchmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.output = Path(cls.temp.name)
        with contextlib.redirect_stdout(io.StringIO()):
            cls.actual = a.analyze(output_dir=cls.output)
        cls.recorded = json.loads(
            (ROOT / "provenance/comparison-results.json").read_text()
        )

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_recorded_metrics_reproduce(self):
        for level, actual in self.actual["examples"].items():
            expected = self.recorded["examples"][level]
            for tool in ("our", "kisi"):
                self.assertAlmostEqual(
                    actual["step_delay_ps"][tool],
                    expected["step_delay_ps"][tool],
                    places=7,
                )
                for computed, stored in zip(actual[tool], expected[tool], strict=True):
                    for key in ("height_v", "width_ui", "min_v", "max_v"):
                        self.assertAlmostEqual(computed[key], stored[key], places=10)
            with np.load(ROOT / "data/cases" / level / "comparison.npz") as stored:
                with np.load(self.output / level / "comparison.npz") as computed:
                    for key in ("our_h", "kisi_h", "our_voltage", "kisi_voltage"):
                        np.testing.assert_allclose(
                            computed[key], stored[key], rtol=1e-10, atol=1e-10
                        )

    def test_label_based_eye_audit(self):
        # Classify by transmitted PRBS bits, independently of the voltage threshold.
        for level, result in self.actual["examples"].items():
            with np.load(self.output / level / "comparison.npz") as data:
                for tool in ("our", "kisi"):
                    latency = (
                        result["step_delay_ps"][tool] * 1e-12 + 5 * a.sigma
                    ) / a.ui
                    phases = np.arange(a.spui) / a.spui
                    phases += np.ceil(latency - phases)
                    positions = (np.arange(127)[:, None] + phases) * a.spui
                    for rx, y in enumerate(data[tool + "_voltage"]):
                        labels = np.roll(a.bits, 31 * rx).astype(bool)
                        samples = np.interp(
                            positions % len(y), np.arange(len(y) + 1), np.r_[y, y[0]]
                        )
                        opening = (
                            samples[labels].min(axis=0) - samples[~labels].max(axis=0)
                        ).max()
                        self.assertAlmostEqual(
                            opening, result[tool][rx]["height_v"], places=9
                        )

    def test_loading_against_analytical_resistor(self):
        # 20-ohm series resistor between 50-ohm source and receiver:
        # 2 * 50 / (50 + 20 + 50) = 5/6 V at DC.
        resistance = 20.0
        reflection = resistance / (100 + resistance)
        transmission = 100 / (100 + resistance)
        s = np.array(
            [[[reflection, transmission], [transmission, reflection]]], dtype=complex
        )
        loaded = a.response(np.array([1e-6]), s, False, False)
        self.assertAlmostEqual(loaded[0, 0, 0].real, 5 / 6, places=12)

    def test_known_failures_remain_visible(self):
        two = self.actual["examples"]["level2-two-channels"]
        self.assertEqual(len(two["kicad_shorts"]), 2)
        self.assertTrue(two["render_diagnostics"])
        case = ROOT / "data/cases/level2-two-channels"
        self.assertEqual(
            json.loads((case / "native-ibis-summary.json").read_text())["status"],
            "blocked_by_verified_short",
        )
        for level, expected in [
            ("level1-single-ended", 0),
            ("level1-differential", 1),
            ("level2-two-channels", 0),
        ]:
            path = ROOT / "data/cases" / level / "native-export-validation-status.json"
            self.assertEqual(json.loads(path.read_text())["exit_code"], expected)

        report = json.loads(
            (
                ROOT
                / "data/cases/level1-differential/native-export-validation/results.json"
            ).read_text()
        )
        self.assertEqual(len(report["lanes"]), 2)
        for model in report["lanes"]:
            self.assertGreater(model["step"]["max_diff_of_final"], 0.05)


if __name__ == "__main__":
    unittest.main()
