from pathlib import Path


def _main_source():
    return (Path(__file__).resolve().parents[1] / "main.py").read_text(encoding="utf-8")


def test_main_wires_instrument_return_controller_to_selection_reset():
    source = _main_source()

    assert "InstrumentReturnController" in source
    assert "self.instrument_return_controller.update" in source
    assert "self.__return_to_instrument_selection()" in source
