# A PiCar kameraképének megjelenítése és távoli vezérlése Kivy-felületen.

import io
import sys
import threading
import time
import urllib.request

from kivy.app import App
from kivy.clock import Clock
from kivy.core.image import Image as CoreImage
from kivy.graphics import Color, RoundedRectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.slider import Slider


# Gombok
class RoundedNavButton(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.background_normal = ""
        self.background_down = ""
        self.background_color = (0, 0, 0, 0)

        with self.canvas.before:
            self.bg_color = Color(0.2, 0.25, 0.25, 1)
            self.rect = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[24]
            )

        self.bind(
            pos=self.update_canvas,
            size=self.update_canvas
        )

    def update_canvas(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

    def set_color(self, rgba):
        self.bg_color.rgba = rgba


# Alkalmazás
class PiCarControlApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.is_forward = False
        self.is_backward = False
        self.is_left = False
        self.is_right = False
        self.pending_speed = 35

    # Felület
    def build(self):
        root_layout = BoxLayout(
            orientation="vertical",
            padding=[10, 35, 10, 135],
            spacing=4
        )

        # Kilépés
        exit_button = Button(
            text="Kilépés az appból",
            background_normal="",
            background_color=(0.8, 0.1, 0.1, 1),
            color=(1, 1, 1, 1),
            font_size="13sp",
            bold=True,
            size_hint=(1, 0.05)
        )
        exit_button.bind(on_press=self.stop)
        root_layout.add_widget(exit_button)

        # Kamera
        camera_container = RelativeLayout(
            size_hint=(1, 0.38)
        )

        self.camera_image = Image(
            source="",
            nocache=True,
            size_hint=(1, 1),
            allow_stretch=True,
            keep_ratio=False
        )

        camera_container.add_widget(self.camera_image)
        root_layout.add_widget(camera_container)

        # Üzemmódok
        mode_layout_top = GridLayout(
            cols=3,
            spacing=3,
            size_hint=(1, 0.065)
        )

        modes = [
            ("1: Kezi", "mode_1"),
            ("2: Kovetes", "mode_2"),
            ("3: Kerules", "mode_3")
        ]

        for text, command in modes:
            button = Button(
                text=text,
                background_normal="",
                background_color=(0.05, 0.45, 0.75, 1),
                color=(1, 1, 1, 1),
                font_size="11sp",
                bold=True
            )

            button.bind(
                on_press=lambda instance, cmd=command: (
                    self.send_command(cmd)
                )
            )
            mode_layout_top.add_widget(button)

        root_layout.add_widget(mode_layout_top)

        # Kapcsolók
        mode_layout_bottom = GridLayout(
            cols=2,
            spacing=3,
            size_hint=(1, 0.05)
        )

        model_button = Button(
            text="M: Modell valtas",
            background_normal="",
            background_color=(0.9, 0.5, 0.1, 1),
            color=(1, 1, 1, 1),
            font_size="11sp",
            bold=True
        )
        model_button.bind(
            on_press=lambda instance: (
                self.send_command("switch_model")
            )
        )
        mode_layout_bottom.add_widget(model_button)

        enhance_button = Button(
            text="C: Kepjavitas",
            background_normal="",
            background_color=(0.5, 0.25, 0.7, 1),
            color=(1, 1, 1, 1),
            font_size="11sp",
            bold=True
        )
        enhance_button.bind(
            on_press=lambda instance: (
                self.send_command("toggle_enhance")
            )
        )
        mode_layout_bottom.add_widget(enhance_button)

        root_layout.add_widget(mode_layout_bottom)

        # Sebesség
        self.speed_slider = Slider(
            min=20,
            max=100,
            value=35,
            step=1,
            size_hint=(1, 0.05)
        )
        self.speed_slider.bind(
            value=self.on_slider_value_change
        )
        root_layout.add_widget(self.speed_slider)

        # Irányítás
        control_layout = GridLayout(
            cols=3,
            spacing=4,
            size_hint=(1, 0.18)
        )

        control_layout.add_widget(
            Button(text="", disabled=True, opacity=0)
        )

        forward_button = RoundedNavButton(
            text="Elore",
            color=(1, 1, 1, 1),
            font_size="11sp",
            bold=True
        )
        forward_button.bind(
            on_press=lambda instance: self.on_dir_press("forward"),
            on_release=lambda instance: self.on_dir_release("forward")
        )
        control_layout.add_widget(forward_button)

        control_layout.add_widget(
            Button(text="", disabled=True, opacity=0)
        )

        left_button = RoundedNavButton(
            text="Balra",
            color=(1, 1, 1, 1),
            font_size="11sp",
            bold=True
        )
        left_button.bind(
            on_press=lambda instance: self.on_dir_press("left"),
            on_release=lambda instance: self.on_dir_release("left")
        )
        control_layout.add_widget(left_button)

        stop_button = RoundedNavButton(
            text="Stop",
            color=(1, 1, 1, 1),
            font_size="11sp",
            bold=True
        )
        stop_button.set_color((1.0, 0.0, 0.0, 1))
        stop_button.bind(
            on_press=lambda instance: self.stop_all()
        )
        control_layout.add_widget(stop_button)

        right_button = RoundedNavButton(
            text="Jobbra",
            color=(1, 1, 1, 1),
            font_size="11sp",
            bold=True
        )
        right_button.bind(
            on_press=lambda instance: self.on_dir_press("right"),
            on_release=lambda instance: self.on_dir_release("right")
        )
        control_layout.add_widget(right_button)

        control_layout.add_widget(
            Button(text="", disabled=True, opacity=0)
        )

        backward_button = RoundedNavButton(
            text="Hatra",
            color=(1, 1, 1, 1),
            font_size="11sp",
            bold=True
        )
        backward_button.bind(
            on_press=lambda instance: self.on_dir_press("backward"),
            on_release=lambda instance: self.on_dir_release("backward")
        )
        control_layout.add_widget(backward_button)

        control_layout.add_widget(
            Button(text="", disabled=True, opacity=0)
        )

        root_layout.add_widget(control_layout)

        # Szálindítás
        threading.Thread(
            target=self.update_camera_stream,
            daemon=True
        ).start()

        return root_layout

    # Csúszka
    def on_slider_value_change(self, instance, value):
        Clock.unschedule(self.send_delayed_speed)
        self.pending_speed = int(value)
        Clock.schedule_once(self.send_delayed_speed, 0.1)

    def send_delayed_speed(self, dt):
        self.send_command(f"speed_{self.pending_speed}")

    # Gombnyomás
    def on_dir_press(self, direction):
        if direction == "forward":
            self.is_forward = True
            self.is_backward = False

        elif direction == "backward":
            self.is_backward = True
            self.is_forward = False

        elif direction == "left":
            self.is_left = True
            self.is_right = False

        elif direction == "right":
            self.is_right = True
            self.is_left = False

        self.send_command(direction)

    # Felengedés
    def on_dir_release(self, direction):
        if direction == "forward":
            self.is_forward = False

        elif direction == "backward":
            self.is_backward = False

        elif direction == "left":
            self.is_left = False

        elif direction == "right":
            self.is_right = False

        if self.is_forward:
            self.send_command("forward")

        elif self.is_backward:
            self.send_command("backward")

        elif self.is_left:
            self.send_command("left")

        elif self.is_right:
            self.send_command("right")

        else:
            self.send_command("release")

    # Leállítás
    def stop_all(self):
        self.is_forward = False
        self.is_backward = False
        self.is_left = False
        self.is_right = False
        self.send_command("stop")

    # Parancsküldés
    def send_command(self, command):
        def send():
            url = (
                "http://192.168.1.32:5000/cmd"
                f"?action={command}"
            )

            try:
                urllib.request.urlopen(url, timeout=0.5)
            except Exception as error:
                print(
                    f"Hiba a parancs küldésekor "
                    f"({command}): {error}"
                )

        threading.Thread(
            target=send,
            daemon=True
        ).start()

    # Képfrissítés
    def update_camera_stream(self):
        while True:
            try:
                response = urllib.request.urlopen(
                    "http://192.168.1.32:5000/video_feed",
                    timeout=2
                )
                image_buffer = b""

                while True:
                    chunk = response.read(1024)

                    if not chunk:
                        break

                    image_buffer += chunk
                    start_index = image_buffer.find(b"\xff\xd8")
                    end_index = image_buffer.find(b"\xff\xd9")

                    if start_index != -1 and end_index != -1:
                        jpeg_data = image_buffer[
                            start_index:end_index + 2
                        ]
                        image_buffer = image_buffer[end_index + 2:]

                        image_stream = io.BytesIO(jpeg_data)
                        core_image = CoreImage(
                            image_stream,
                            ext="jpg"
                        )

                        Clock.schedule_once(
                            lambda dt, image=core_image: setattr(
                                self.camera_image,
                                "texture",
                                image.texture
                            )
                        )

            except Exception:
                time.sleep(1)

    # Kilépés
    def stop(self, *args):
        try:
            urllib.request.urlopen(
                "http://192.168.1.32:5000/cmd?action=stop",
                timeout=0.2
            )
        except Exception:
            pass

        sys.exit(0)


# Indítás
if __name__ == "__main__":
    PiCarControlApp().run()
