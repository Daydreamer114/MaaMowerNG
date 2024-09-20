#!/usr/bin/env python3
import multiprocessing as mp


def splash_screen(queue: mp.Queue):
    import tkinter as tk
    from tkinter.font import Font

    from PIL import Image, ImageTk

    from arknights_mower.utils.path import get_path

    root = tk.Tk()
    container = tk.Frame(root)

    logo_path = get_path("@install/logo.png")
    img = Image.open(logo_path)
    img = ImageTk.PhotoImage(img)
    canvas = tk.Canvas(container, width=256, height=256)
    canvas.create_image(128, 128, image=img)
    canvas.pack()

    title_font = Font(size=24)
    title_label = tk.Label(
        container,
        text="arknights-mower",
        font=title_font,
    )
    title_label.pack()

    loading_label = tk.Label(container)
    loading_label.pack()

    container.pack(expand=1)
    root.overrideredirect(True)

    window_width = 500
    window_height = 400
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = int(screen_width / 2 - window_width / 2)
    y = int(screen_height / 2 - window_height / 2)
    root.geometry(f"{window_width}x{window_height}+{x}+{y}")

    def recv_msg():
        try:
            msg = queue.get(False)
            if msg["type"] == "text":
                loading_label.config(text=msg["data"] + "……")
                root.after(100, recv_msg)
            elif msg["type"] == "dialog":
                from tkinter import messagebox

                root.withdraw()
                messagebox.showerror("arknights-mower", msg["data"])
                root.destroy()
        except Exception:
            pass

    root.after(100, recv_msg)
    root.mainloop()


def start_tray(queue: mp.Queue, global_space, port, url):
    from PIL import Image
    from pystray import Icon, Menu, MenuItem

    from arknights_mower.utils.path import get_path

    logo_path = get_path("@install/logo.png")
    img = Image.open(logo_path)

    title = f"mower@{port}({global_space})" if global_space else f"mower@{port}"

    def open_browser():
        import webbrowser

        webbrowser.open(url)

    icon = Icon(
        name="arknights-mower",
        icon=img,
        menu=Menu(
            MenuItem(
                text=title,
                action=None,
                enabled=False,
            ),
            Menu.SEPARATOR,
            MenuItem(
                text="打开/关闭窗口",
                action=lambda: queue.put("toggle"),
                default=True,
            ),
            MenuItem(
                text="在浏览器中打开网页面板",
                action=open_browser,
            ),
            Menu.SEPARATOR,
            MenuItem(
                text="退出",
                action=lambda: queue.put("exit"),
            ),
        ),
        title=title,
    )
    icon.run()


def webview_window(child_conn, global_space, host, port, url, tray):
    import sys
    from threading import Thread

    import webview

    webview.settings["ALLOW_DOWNLOADS"] = True

    from arknights_mower.__init__ import __version__
    from arknights_mower.utils import config, path

    path.global_space = global_space

    global width
    global height

    config.load_conf()
    width = config.conf.webview.width
    height = config.conf.webview.height

    def window_size(w, h):
        global width
        global height
        width = w
        height = h

    window = webview.create_window(
        f"arknights-mower {__version__} (http://{host}:{port})",
        url,
        text_select=True,
        confirm_close=not tray,
        width=width,
        height=height,
    )
    window.events.resized += window_size

    def recv_msg():
        while True:
            msg = child_conn.recv()
            if msg == "exit":
                window.confirm_close = False
                window.destroy()
                return
            if msg == "file":
                result = window.create_file_dialog(
                    dialog_type=webview.OPEN_DIALOG,
                )
            elif msg == "folder":
                result = window.create_file_dialog(
                    dialog_type=webview.FOLDER_DIALOG,
                )
            if result is None:
                result = ""
            elif not isinstance(result, str):
                if len(result) == 0:
                    result = ""
                else:
                    result = result[0]
            child_conn.send(result)

    Thread(target=recv_msg, daemon=True).start()

    try:
        webview.start()

        config.load_conf()
        config.conf.webview.width = width
        config.conf.webview.height = height
        config.save_conf()
        sys.exit()
    except Exception:
        import webbrowser

        webbrowser.open(url)


if __name__ == "__main__":
    splash_queue = mp.Queue()
    splash_process = mp.Process(target=splash_screen, args=(splash_queue,), daemon=True)
    splash_process.start()

    splash_queue.put({"type": "text", "data": "加载配置文件"})

    import sys

    from arknights_mower.utils import path

    if len(sys.argv) == 2:
        path.global_space = sys.argv[1]

    from arknights_mower.utils import config

    conf = config.conf
    tray = conf.webview.tray
    token = conf.webview.token
    host = "0.0.0.0" if token else "127.0.0.1"

    splash_queue.put({"type": "text", "data": "检测端口占用"})

    import time

    from arknights_mower.utils.network import get_new_port, is_port_in_use

    if token:
        port = conf.webview.port

        if is_port_in_use(port):
            splash_queue.put(
                {"type": "dialog", "data": f"端口{port}已被占用，无法启动！"}
            )
            time.sleep(5)
            sys.exit()
    else:
        port = get_new_port()

    url = f"http://127.0.0.1:{port}"
    if token:
        url += f"?token={token}"

    splash_queue.put({"type": "text", "data": "加载Flask依赖"})

    from server import app

    splash_queue.put({"type": "text", "data": "启动Flask网页服务器"})

    from threading import Thread
    from time import sleep

    if token:
        app.token = token
    flask_thread = Thread(
        target=app.run,
        kwargs={"host": host, "port": port},
        daemon=True,
    )
    flask_thread.start()

    while not is_port_in_use(port):
        sleep(0.1)

    if tray:
        splash_queue.put({"type": "text", "data": "加载托盘图标"})
        tray_queue = mp.Queue()
        tray_process = mp.Process(
            target=start_tray,
            args=(tray_queue, path.global_space, port, url),
            daemon=True,
        )
        tray_process.start()

    splash_queue.put({"type": "text", "data": "创建主窗口"})

    config.parent_conn, child_conn = mp.Pipe()
    config.webview_process = mp.Process(
        target=webview_window,
        args=(child_conn, path.global_space, host, port, url, tray),
        daemon=True,
    )
    config.webview_process.start()

    splash_process.terminate()

    if tray:
        while True:
            msg = tray_queue.get()
            if msg == "toggle":
                if config.webview_process.is_alive():
                    config.parent_conn.send("exit")
                    if config.webview_process.join(3) is None:
                        config.webview_process.terminate()
                else:
                    config.parent_conn, child_conn = mp.Pipe()
                    config.webview_process = mp.Process(
                        target=webview_window,
                        args=(
                            child_conn,
                            path.global_space,
                            host,
                            port,
                            url,
                            tray,
                        ),
                        daemon=True,
                    )
                    config.webview_process.start()
            elif msg == "exit":
                config.parent_conn.send("exit")
                if config.webview_process.join(3) is None:
                    config.webview_process.terminate()
                break
    else:
        config.webview_process.join()
