import urllib.request
import requests
from io import BytesIO
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.core.image import Image as CoreImage
from kivy.clock import Clock

ROBOT_IP = "127.0.0.1"
STREAM_URL = f"http://{ROBOT_IP}:5000/video_feed"
CMD_URL = f"http://{ROBOT_IP}:5000/cmd?action="

class PiCarApp(App):
    def build(self):
        root = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        self.video_img = Image(allow_stretch=True, keep_ratio=True)
        root.add_widget(self.video_img)

        mode_layout = GridLayout(cols=4, size_hint=(1, 0.12), spacing=5)
        mode_layout.add_widget(Button(text="Kézi (1)", on_press=lambda x: self.send_cmd("mode_1")))
        mode_layout.add_widget(Button(text="Követ (2)", on_press=lambda x: self.send_cmd("mode_2")))
        mode_layout.add_widget(Button(text="Kerül (3)", on_press=lambda x: self.send_cmd("mode_3")))
        mode_layout.add_widget(Button(text="Modell (M)", on_press=lambda x: self.send_cmd("switch_model")))
        root.add_widget(mode_layout)

        nav_layout = GridLayout(cols=3, size_hint=(1, 0.35), spacing=5)
        nav_layout.add_widget(Button(text=""))
        nav_layout.add_widget(Button(text="ELŐRE", on_press=lambda x: self.send_cmd("forward"), on_release=lambda x: self.send_cmd("stop")))
        nav_layout.add_widget(Button(text=""))
        
        nav_layout.add_widget(Button(text="BALRA", on_press=lambda x: self.send_cmd("left"), on_release=lambda x: self.send_cmd("stop")))
        nav_layout.add_widget(Button(text="STOP", background_color=(1,0,0,1), on_press=lambda x: self.send_cmd("stop")))
        nav_layout.add_widget(Button(text="JOBBRA", on_press=lambda x: self.send_cmd("right"), on_release=lambda x: self.send_cmd("stop")))
        
        nav_layout.add_widget(Button(text=""))
        nav_layout.add_widget(Button(text="HÁTRA", on_press=lambda x: self.send_cmd("backward"), on_release=lambda x: self.send_cmd("stop")))
        nav_layout.add_widget(Button(text=""))
        root.add_widget(nav_layout)

        Clock.schedule_interval(self.update_stream, 1.0 / 20.0)
        self.stream_bytes = b''
        self.stream_handle = None

        return root

    def send_cmd(self, action):
        try:
            requests.get(CMD_URL + action, timeout=0.15)
        except Exception:
            pass

    def update_stream(self, dt):
        if self.stream_handle is None:
            try:
                self.stream_handle = urllib.request.urlopen(STREAM_URL, timeout=2)
            except Exception:
                return

        try:
            chunk = self.stream_handle.read(4096)
            if chunk:
                self.stream_bytes += chunk
                a = self.stream_bytes.find(b'\xff\xd8') # JPEG Start
                b = self.stream_bytes.find(b'\xff\xd9') # JPEG End
                if a != -1 and b != -1 and b > a:
                    jpg_data = self.stream_bytes[a:b+2]
                    self.stream_bytes = self.stream_bytes[b+2:]
                    
                    data_io = BytesIO(jpg_data)
                    img = CoreImage(data_io, ext="jpeg")
                    self.video_img.texture = img.texture
        except Exception:
            self.stream_handle = None

if __name__ == "__main__":
    PiCarApp().run()
