import threading
import time
import cv2
from . import signs as cfg
from .utils import draw_distance

class SignController:
    def __init__(self, drive, stop):
        self.drive, self.stop = drive, stop
        self.abort = threading.Event()
        self.thread = None
        self.active = False
        self.status = ''
        self.next_side = 'RIGHT'
        self.enabled = {'cone': True, 'arrow': True}
        self.absent = {'cone': None, 'arrow': None}
        self.last_frame_time = time.monotonic()
        self.error = None

    def heartbeat(self):
        self.last_frame_time = time.monotonic()

    def cancel(self):
        if self.thread is not None:
            self.abort.set()
            self.thread.join()
            self.thread = None
            self.stop()
        self.active = False
        self.status = ''

    def close(self):
        self.cancel()

    def sleep(self, seconds):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            if self.abort.wait(min(0.01, max(0, end-time.monotonic()))):
                return False
            if time.monotonic() - self.last_frame_time > 0.7:
                self.abort.set()
                return False
        return not self.abort.is_set()

    def run(self, kind, value):
        try:
            self.stop()
            if kind == 'cone':
                steps = [('STOP', .12, (0,0))]
                for name, duration, command in cfg.avoid_steps(value):
                    steps += [(name, duration, command), ('STOP', .08, (0,0))]
            else:
                left = value == 'balra_nyil'
                steps = [('STOP', cfg.ARROW_STOP_S, (0,0)),
                         ('TURN', cfg.TURN_90_LEFT_S if left else cfg.TURN_90_RIGHT_S,
                          (-cfg.TURN_SPEED,cfg.TURN_SPEED) if left else (cfg.TURN_SPEED,-cfg.TURN_SPEED)),
                         ('CLEAR', cfg.CLEAR_S, (cfg.LEFT_STRAIGHT_SPEED,cfg.RIGHT_STRAIGHT_SPEED))]
            for _, duration, command in steps:
                if self.abort.is_set():
                    return
                self.drive(*command)
                if not self.sleep(duration):
                    return
            if kind == 'cone':
                self.next_side = 'LEFT' if value == 'RIGHT' else 'RIGHT'
        except Exception as exc:
            self.error = exc
        finally:
            self.stop()
            self.active = False

    def update(self, detections, can_start=True):
        if self.error is not None:
            raise RuntimeError('Jelzesmanover hiba') from self.error
        now = time.monotonic()
        cones = [d for d in detections if d[0]=='boja']
        arrows = [d for d in detections if d[0]!='boja']
        for kind, items in [('cone',cones),('arrow',arrows)]:
            if items:
                self.absent[kind] = None
            elif self.absent[kind] is None:
                self.absent[kind] = now
            elif not self.active and now-self.absent[kind] >= 1.0:
                self.enabled[kind] = True
        if self.active or not can_start:
            return self.active
        cone = min(cones,key=lambda d:d[1],default=None)
        arrow = min(arrows,key=lambda d:d[1],default=None)
        if arrow and self.enabled['arrow'] and arrow[1]<=cfg.ARROW_NEAR_CM:
            kind, value = 'arrow',arrow[0]
            status = 'Fordul balra' if value=='balra_nyil' else 'Fordul jobbra'
        elif cone and self.enabled['cone'] and cone[1]<=cfg.CONE_NEAR_CM:
            kind, value = 'cone',self.next_side
            status = 'Kerul jobbrol' if value=='RIGHT' else 'Kerul balrol'
        else:
            return False
        if self.thread is not None:
            self.thread.join()
        self.enabled[kind] = False
        self.absent[kind] = None
        self.abort.clear()
        self.active = True
        self.status = status
        self.thread = threading.Thread(target=self.run,args=(kind,value),daemon=True)
        self.thread.start()
        return True

    def draw(self, frame, detections):
        palette = {'balra_nyil': (255,56,56), 'boja': (255,157,151), 'jobbra_nyil': (255,112,31)}
        for name, distance, cx, score, (x1,y1,x2,y2) in detections:
            cv2.rectangle(frame,(x1,y1),(x2,y2),palette[name],2)
            cv2.putText(frame,f'{name} {score*100:.0f}%',(x1,min(frame.shape[0]-5,y1+18)),
                        cv2.FONT_HERSHEY_SIMPLEX,.5,(220,220,220),1)
            draw_distance(frame,distance,x1,max(18,y1-7))
