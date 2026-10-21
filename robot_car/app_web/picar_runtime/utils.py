from functools import lru_cache
from pathlib import Path
import cv2
import numpy as np

COCO_LABELS = 'person,bicycle,car,motorcycle,airplane,bus,train,truck,boat,traffic light,fire hydrant,stop sign,parking meter,bench,bird,cat,dog,horse,sheep,cow,elephant,bear,zebra,giraffe,backpack,umbrella,handbag,tie,suitcase,frisbee,skis,snowboard,sports ball,kite,baseball bat,baseball glove,skateboard,surfboard,tennis racket,bottle,wine glass,cup,fork,knife,spoon,bowl,banana,apple,sandwich,orange,broccoli,carrot,hot dog,pizza,donut,cake,chair,couch,potted plant,bed,dining table,toilet,tv,laptop,mouse,remote,keyboard,cell phone,microwave,oven,toaster,sink,refrigerator,book,clock,vase,scissors,teddy bear,hair drier,toothbrush'.split(',')

def id_to_color(idx):
    return np.random.RandomState(int(idx)).randint(0, 255, size=3, dtype=np.uint8)

def preprocess(image, width, height):
    h, w = image.shape[:2]
    scale = min(width / w, height / h)
    nw, nh = int(w * scale), int(h * scale)
    result = np.full((height, width, 3), 114, dtype=np.uint8)
    x, y = (width - nw) // 2, (height - nh) // 2
    result[y:y+nh, x:x+nw] = cv2.resize(image, (nw, nh), interpolation=cv2.INTER_CUBIC)
    return result

def nms(preds, threshold):
    # Az eredeti cython_nms.pyx szabályai: +1 pixel, >= küszöb,
    # a megtartott indexek eredeti sorrendben.
    x1,y1,x2,y2,scores = np.asarray(preds,dtype=np.float32).T
    area = (x2-x1+1)*(y2-y1+1)
    order = scores.argsort()[::-1]
    kept = []
    while order.size:
        i = order[0]
        kept.append(i)
        rest = order[1:]
        inter = np.maximum(0,np.minimum(x2[i],x2[rest])-np.maximum(x1[i],x1[rest])+1) * np.maximum(0,np.minimum(y2[i],y2[rest])-np.maximum(y1[i],y1[rest])+1)
        iou = inter / (area[i]+area[rest]-inter)
        order = rest[~(iou >= threshold)]
    return np.sort(np.asarray(kept,dtype=np.int64))

@lru_cache(maxsize=512)
def text_mask(text):
    from PIL import Image, ImageDraw, ImageFont
    font = ImageFont.truetype(str(Path(__file__).with_name('DejaVuSans.ttf')), 15)
    box = font.getbbox(text)
    im = Image.new('L', (box[2]-box[0]+2, box[3]-box[1]+2))
    ImageDraw.Draw(im).text((1-box[0], 1-box[1]), text, font=font, fill=255)
    return np.asarray(im)

def draw_distance(frame, distance, x, y):
    mask = text_mask(f'Távolság: {distance:.0f} cm')
    h, w = mask.shape
    x = max(0, min(int(x), frame.shape[1]-w))
    y = max(0, min(int(y)-h, frame.shape[0]-h))
    roi = frame[y:y+h, x:x+w]
    alpha = mask[:roi.shape[0], :roi.shape[1], None] / 255.0
    roi[:] = roi * (1-alpha) + np.array([220,220,220]) * alpha

def overlaps_sign(box, signs):
    x1,y1,x2,y2 = box
    area=max(1,(x2-x1)*(y2-y1))
    for _,_,_,_,(sx1,sy1,sx2,sy2) in signs:
        intersection=max(0,min(x2,sx2)-max(x1,sx1))*max(0,min(y2,sy2)-max(y1,sy1))
        sign_area=max(1,(sx2-sx1)*(sy2-sy1))
        if intersection / (area+sign_area-intersection) > .35:
            return True
    return False
