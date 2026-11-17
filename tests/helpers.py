from pathlib import Path
import json
import os
import subprocess
import sys

from PIL import Image


REPO = Path(__file__).resolve().parents[1]


def photo_file(path, size=(40, 20), color="red", **save_options):
    with Image.new("RGB", size, color) as image:
        image.save(path, **save_options)
    return path


def layout_data(width=100, height=100):
    return {
        "schema_version": 2,
        "canvas": {"width": width, "height": height, "background": "#FFFFFF"},
        "layers": [
            {"photo_id": 1, "mode": "whole",
             "box": {"x": 0.05, "y": 0.1, "width": 0.2}},
            {"photo_id": 2, "mode": "whole",
             "box": {"x": 0.5, "y": 0.1, "width": 0.2}},
        ],
    }


def write_layout(tmp_path, data=None):
    path = tmp_path / "input.json"
    path.write_text(json.dumps(data if data is not None else layout_data()), encoding="utf-8")
    return path


def framed_layout_data(width=100, height=100):
    data = layout_data(width, height)
    for layer in data["layers"]:
        layer["mode"] = "cover"
        layer["box"]["height"] = 0.2
        layer["crop"] = {}
    return data


def rounded_layout_data(framed=False, border_width=5):
    data = framed_layout_data() if framed else layout_data()
    front, back = data["layers"]
    front["box"] = {"x": 0.2, "y": 0.2, "width": 0.6}
    back["box"] = {"x": 0.1, "y": 0.1, "width": 0.8}
    if framed:
        front["box"]["height"] = 0.6
        back["box"]["height"] = 0.8
    front["corner_radius_px"] = 10
    if border_width:
        front["border"] = {"width_px": border_width, "color": "#FFFFFF"}
    data["layers"].reverse()
    return data


def run_cli(data_dir, *arguments):
    environment = {
        key: value for key, value in os.environ.items()
        if not key.startswith(("AZURE_", "OPENAI_"))
    }
    script = (
        "import runpy,socket\n"
        "def blocked(*args,**kwargs):\n"
        "    raise AssertionError('Network calls forbidden')\n"
        "socket.socket.connect=blocked\n"
        "socket.create_connection=blocked\n"
        "runpy.run_module('ai_collage',run_name='__main__')\n"
    )
    return subprocess.run(
        [sys.executable, "-c", script, "--data-dir", str(data_dir), *map(str, arguments)],
        cwd=REPO, env=environment, capture_output=True, text=True, timeout=30,
    )
