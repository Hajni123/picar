[app]

title = PiCar Control
package.name = picarcontrol
package.domain = org.picar
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
source.exclude_dirs = venv,__pycache__,Python-3.11.9,.buildozer,.git,.github,data_dobozkerules_backup
source.exclude_exts = tgz,hef,onnx,pth,log,npy,alls
version = 0.1
requirements = python3,kivy
android.permissions = INTERNET
orientation = portrait
fullscreen = 0
icon.filename = %(source.dir)s/picar.jpg
android.presplash_image = %(source.dir)s/picar.jpg
android.presplash_color = #000000
android.api = 33
android.min_api = 21
android.sdk = 33
android.ndk = 25b
android.archs = arm64-v8a
android.build_tools_version = 33.0.2
android.allow_backup = True
android.build_mode = debug

[buildozer]
log_level = 2
warn_on_root = 1
