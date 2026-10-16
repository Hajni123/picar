import threading
import urllib.request
import time
import io
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.core.image import Image as CoreImage

class PiCarControlApp(App):
    def build(self):
        root_layout = BoxLayout(orientation='vertical', padding=6, spacing=4)
        
        # 1. KILÉPÉS GOMB FENT
        btn_exit = Button(
            text='KILÉPÉS AZ APPBÓL', 
            background_normal='', 
            background_color=(0.8, 0.1, 0.1, 1),
            color=(1, 1, 1, 1),
            font_size='14sp',
            bold=True,
            size_hint=(1, 0.05)
        )
        btn_exit.bind(on_press=self.stop)
        root_layout.add_widget(btn_exit)

        # 2. KAMERA + ZÖLD SÁV EGYÜTT
        cam_container = RelativeLayout(size_hint=(1, 0.50))
        
        self.camera_image = Image(
            source='', 
            nocache=True,
            size_hint=(1, 1),
            allow_stretch=True,
            keep_ratio=False
        )
        cam_container.add_widget(self.camera_image)
        
        self.status_label = Label(
            text='[1] KEZI (WASD / TELEFON) | AI: DET | [ENH: KI] (C)',
            color=(0.2, 1.0, 0.2, 1),
            font_size='12sp',
            bold=True,
            size_hint=(1, 0.15),
            pos_hint={'x': 0, 'y': 0}
        )
        cam_container.add_widget(self.status_label)
        root_layout.add_widget(cam_container)
        
        # 3. MÓDVÁLASZTÓ GOMBOK
        mode_layout_top = GridLayout(cols=3, spacing=3, size_hint=(1, 0.08))
        modes_top = [("1: Kezi", "mode_1"), ("2: Kovetes", "mode_2"), ("3: Kerules", "mode_3")]
        for text, cmd in modes_top:
            btn = Button(
                text=text, 
                background_normal='', 
                background_color=(0.05, 0.45, 0.75, 1),
                color=(1, 1, 1, 1),
                font_size='12sp',
                bold=True
            )
            btn.bind(on_press=lambda x, c=cmd: self.send_command(c))
            mode_layout_top.add_widget(btn)
        root_layout.add_widget(mode_layout_top)

        mode_layout_bottom = GridLayout(cols=2, spacing=3, size_hint=(1, 0.08))
        
        btn_model = Button(
            text='M: Modell Valtas', 
            background_normal='', 
            background_color=(0.9, 0.5, 0.1, 1),
            color=(1, 1, 1, 1),
            font_size='12sp',
            bold=True
        )
        btn_model.bind(on_press=lambda x: self.send_command('switch_model'))
        mode_layout_bottom.add_widget(btn_model)

        btn_kepjav = Button(
            text='C: Kepjavitas', 
            background_normal='', 
            background_color=(0.5, 0.25, 0.7, 1),
            color=(1, 1, 1, 1),
            font_size='12sp',
            bold=True
        )
        btn_kepjav.bind(on_press=lambda x: self.send_command('toggle_enhance'))
        mode_layout_bottom.add_widget(btn_kepjav)
        
        root_layout.add_widget(mode_layout_bottom)
        
        # 4. IRÁNYÍTÓ GOMBOK ALUL (on_press + on_release motor_stop)
        control_layout = GridLayout(cols=3, spacing=3, size_hint=(1, 0.21))
        
        control_layout.add_widget(Button(text='', disabled=True, opacity=0))
        
        btn_forward = Button(text='ELORE', background_normal='', background_color=(0.2, 0.25, 0.25, 1), color=(1, 1, 1, 1), font_size='13sp', bold=True)
        btn_forward.bind(on_press=lambda x: self.send_command('forward'), on_release=lambda x: self.send_command('motor_stop'))
        control_layout.add_widget(btn_forward)
        
        control_layout.add_widget(Button(text='', disabled=True, opacity=0))
        
        btn_left = Button(text='BALRA', background_normal='', background_color=(0.2, 0.25, 0.25, 1), color=(1, 1, 1, 1), font_size='13sp', bold=True)
        btn_left.bind(on_press=lambda x: self.send_command('left'), on_release=lambda x: self.send_command('motor_stop'))
        control_layout.add_widget(btn_left)
        
        btn_stop = Button(text='STOP', background_normal='', background_color=(1.0, 0.0, 0.0, 1), color=(1, 1, 1, 1), font_size='13sp', bold=True)
        btn_stop.bind(on_press=lambda x: self.send_command('stop'))
        control_layout.add_widget(btn_stop)
        
        btn_right = Button(text='JOBBRA', background_normal='', background_color=(0.2, 0.25, 0.25, 1), color=(1, 1, 1, 1), font_size='13sp', bold=True)
        btn_right.bind(on_press=lambda x: self.send_command('right'), on_release=lambda x: self.send_command('motor_stop'))
        control_layout.add_widget(btn_right)
        
        control_layout.add_widget(Button(text='', disabled=True, opacity=0))
        
        btn_back = Button(text='HATRA', background_normal='', background_color=(0.2, 0.25, 0.25, 1), color=(1, 1, 1, 1), font_size='13sp', bold=True)
        btn_back.bind(on_press=lambda x: self.send_command('backward'), on_release=lambda x: self.send_command('motor_stop'))
        control_layout.add_widget(btn_back)
        
        control_layout.add_widget(Button(text='', disabled=True, opacity=0))
        
        root_layout.add_widget(control_layout)
        
        # Kamera frissítő szál indítása
        threading.Thread(target=self.update_camera_stream, daemon=True).start()

        return root_layout

    def send_command(self, cmd):
        url = f"http://192.168.1.32:5000/cmd?action={cmd}"
        try:
            urllib.request.urlopen(url, timeout=0.5)
        except Exception as e:
            print(f"Hiba a parancs küldésekor ({cmd}): {e}")

    def update_camera_stream(self):
        while True:
            try:
                req = urllib.request.urlopen('http://192.168.1.32:5000/video_feed', timeout=2)
                bytes_data = b''
                while True:
                    chunk = req.read(1024)
                    if not chunk:
                        break
                    bytes_data += chunk
                    a = bytes_data.find(b'\xff\xd8')
                    b = bytes_data.find(b'\xff\xd9')
                    if a != -1 and b != -1:
                        jpg = bytes_data[a:b+2]
                        bytes_data = bytes_data[b+2:]
                        img_io = io.BytesIO(jpg)
                        core_image = CoreImage(img_io, ext='jpg')
                        Clock.schedule_once(lambda dt, ci=core_image: setattr(self.camera_image, 'texture', ci.texture))
            except Exception:
                time.sleep(1)

if __name__ == '__main__':
    PiCarControlApp().run()
