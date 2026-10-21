import json
import queue
import threading
import time
from pathlib import Path
import cv2
import numpy as np
from .hailo_inference import HailoInfer
from .utils import COCO_LABELS, preprocess
from .signs import detections_from_hailo, _nms_box_to_frame
from . import detection

signs_enabled = threading.Event()

def infer_one(model, frame):
    result, errors = [], []
    def callback(completion_info, bindings_list):
        if completion_info.exception:
            errors.append(completion_info.exception)
            return
        bindings = bindings_list[0]
        names = bindings._output_names
        if len(names)==1:
            result.append(bindings.output().get_buffer())
        else:
            result.append({name:np.expand_dims(bindings.output(name).get_buffer(),0) for name in names})
    h,w,_ = model.get_input_shape()
    model.run([preprocess(frame,w,h)], callback).wait(10000)
    if errors:
        raise RuntimeError('Hailo inferenciahiba') from errors[0]
    if not result:
        raise RuntimeError('Ures Hailo eredmeny')
    return result[0]

def general_detections(raw, engine, model, frame, config):
    h,w = frame.shape[:2]
    if engine=='det':
        rows=[]
        for cls_id, class_rows in enumerate(raw):
            for box in class_rows:
                x1,y1,x2,y2,score = _nms_box_to_frame(box,w,h)
                if score >= .25 and x2>x1 and y2>y1:
                    rows.append((y1,x1,y2,x2,score,cls_id))
        return rows
    from . import segmentation
    if model.is_nms_postprocess_enabled():
        return [(y1,x1,y2,x2,float(det.score),int(det.class_id))
                for det in raw
                for x1,y1,x2,y2,score in [_nms_box_to_frame(
                    [det.y_min,det.x_min,det.y_max,det.x_max,det.score],w,h)]
                if det.score>=.25 and x2>x1 and y2>y1]
    decoded=segmentation.decode_and_postprocess(raw,config,'v5')
    # A szegmentáló dekódoló [xmin,ymin,xmax,ymax] normalizált dobozokat ad.
    return [(y1,x1,y2,x2,float(score),int(cls))
            for box,score,cls in zip(decoded['detection_boxes'],decoded['detection_scores'],decoded['detection_classes'])
            for x1,y1,x2,y2,_ in [_nms_box_to_frame([box[1],box[0],box[3],box[2],score],w,h)]
            if score>=.25 and x2>x1 and y2>y1]

def run_pipeline(app_dir,engine,visualize,start_mode,start_enhance,emergency_stop):
    from picamera2 import Picamera2
    app_dir=Path(app_dir)
    for filename in [ 'yolov6n.hef' if engine=='det' else 'yolov5m_seg_with_nms.hef', 'best.hef']:
        if not (app_dir/filename).is_file():
            raise FileNotFoundError(app_dir/filename)
    config=json.loads(Path(__file__).with_name('detection.json' if engine=='det' else 'segmentation.json').read_text())
    if engine=='seg':
        from . import segmentation
    stop_event=threading.Event()
    output=queue.Queue(maxsize=1)
    models=[]
    camera=None
    worker=None
    def publish(item):
        try:
            output.put_nowait(item)
        except queue.Full:
            try: output.get_nowait()
            except queue.Empty: pass
            output.put_nowait(item)
    try:
        general=HailoInfer(str(app_dir/('yolov6n.hef' if engine=='det' else 'yolov5m_seg_with_nms.hef')),1,
                           output_type='FLOAT32' if engine=='seg' else None)
        models.append(general)
        sign_model=HailoInfer(str(app_dir/'best.hef'),1,output_type='FLOAT32')
        models.append(sign_model)
        camera=Picamera2()
        camera.configure(camera.create_video_configuration(main={'size':(640,360),'format':'RGB888'},controls={'FrameRate':30}))
        camera.start()
        if start_mode==3: signs_enabled.set()
        else: signs_enabled.clear()
        def process():
            try:
                while not stop_event.is_set():
                    frame=cv2.cvtColor(camera.capture_array(),cv2.COLOR_BGR2RGB)
                    timestamp=time.monotonic()
                    raw=infer_one(general,frame)
                    if stop_event.is_set():
                        break
                    detected_signs=None
                    if signs_enabled.is_set():
                        detected_signs=detections_from_hailo(infer_one(sign_model,frame),640,360)
                    rows=general_detections(raw,engine,general,frame,config)
                    publish((frame,{'raw':raw,'signs':detected_signs,'detections':rows,'timestamp':timestamp}))
            except BaseException as exc:
                emergency_stop()
                publish(exc)
        def draw(frame,raw):
            if engine=='det':
                return detection.inference_result_handler(frame,raw,COCO_LABELS,config)
            return segmentation.inference_result_handler(frame,raw,config,'v5',COCO_LABELS,
                         nms_postprocess_enabled=general.is_nms_postprocess_enabled())
        worker=threading.Thread(target=process,daemon=True,name='picar-inference')
        worker.start()
        return visualize(None,None,output,draw,None,stop_event,engine,start_mode,start_enhance)
    finally:
        stop_event.set()
        emergency_stop()
        if worker is not None:
            worker.join(timeout=22)
        if camera is not None:
            camera.stop()
            camera.close()
        for model in reversed(models):
            model.close()
