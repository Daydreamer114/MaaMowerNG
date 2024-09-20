#!/usr/bin/env python3

import json

import webview


class Api:
    def __init__(self):
        try:
            with open("instances.json", "r", encoding="utf-8") as f:
                self.instances = json.load(f)
        except Exception:
            self.instances = []
            self.save()

    def save(self):
        with open("instances.json", "w", encoding="utf-8") as f:
            json.dump(self.instances, f, ensure_ascii=False)

    def get_instances(self):
        return self.instances

    def add(self, name, path):
        self.instances.append({"name": name, "path": path})
        self.save()

    def remove(self, idx):
        del self.instances[idx]
        self.save()

    def rename(self, idx, name):
        self.instances[idx]["name"] = name
        self.save()

    def select_path(self, idx):
        window = webview.active_window()
        folder = window.create_file_dialog(dialog_type=webview.FOLDER_DIALOG)
        if folder is None:
            return None
        if not isinstance(folder, str):
            folder = folder[0]
        self.instances[idx]["path"] = folder
        self.save()
        return folder

    def start(self, idx):
        import sys
        from pathlib import Path
        from subprocess import Popen

        Popen(
            [sys.executable, "webview_ui.py", self.instances[idx]["path"]],
            cwd=Path(__file__).parent,
        )


def jump_to_index(window):
    window.load_url("/manager/index.html")


if __name__ == "__main__":
    api = Api()
    window = webview.create_window(
        title="多开管理器",
        url="ui/dist/index.html",
        js_api=api,
        min_size=(400, 500),
        width=400,
        height=500,
    )
    webview.start(jump_to_index, window, http_server=True)
