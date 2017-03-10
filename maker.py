# coding: utf-8
"""
Rage Expression Maker

@author: Rem
@contact: remch183@outlook.com
@time: 2017/3/10
"""


import numpy as np
from matplotlib import pyplot as plt
import cv2
import os


class Template:
    def __init__(self, img):
        self.img = img
        self.ix = 0
        self.iy = 0
        self.iw = 0
        self.ih = 0


class ExpressionMaker:
    cascade = cv2.CascadeClassifier('haarcascade_hand_fist.xml')
    face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_alt.xml')
    eye_cascade = cv2.CascadeClassifier('haarcascade_eye.xml')

    def __init__(self):
        pass

    def make_expression(self, img_name, output_dir='./output/'):
        start_num = len(os.listdir(output_dir))
        try:
            faces = self.face_recognition(img_name)
        except cv2.error:
            print img_name
            return
        template = self.get_template()
        expressions = []
        print('Recognize %d faces in img %s' % (len(faces), img_name))
        for i, face in enumerate(faces):
            block = int(float(20 * (i + 1)) / len(faces) + 0.5)
            print '\r' + '■'*block + '□'*(20 - block) + '%d / %d' % (i+1, len(faces)),
            face = self.brighten_face(face)
            face = self.remove_jew(face)
            face = self._resize_img_by_width(face, template.iw)
            blended_img = self.blend_imgs(face, template)
            expression = self.eadge_beautify(blended_img, face, template)
            expressions.append(expression)

        for i, expression in enumerate(expressions):
            output_filename = output_dir + '%03d.jpg' % (i + start_num,)
            cv2.imwrite(output_filename, expression)

        return

    def face_recognition(self, img_name):
        try:
            img = cv2.imread(img_name)
        except UnicodeEncodeError:
            print(img_name, 'Unicode_error')
            return []
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
        cut_faces = []
        for (x, y, w, h) in faces:
            roi_gray = gray[y:y + h, x:x + w]
            roi_color = img[y:y + h, x:x + w]
            one_face = np.array(roi_color)
            img = cv2.rectangle(img, (x, y), (x + w, y + h), (255, 0, 0), 2)
            eyes = self.eye_cascade.detectMultiScale(roi_gray)
            top, left, right = 100000, 100000, 0
            for (ex, ey, ew, eh) in eyes:
                cv2.rectangle(roi_color, (ex, ey), (ex + ew, ey + eh), (0, 255, 0), 2)
                if ey < top: top = ey
                if ex < left: left = ex
                if ex + ew > right: right = ex + ew
            if len(eyes):
                one_face = one_face[top:, left:right]
            cut_faces.append(one_face)
        return cut_faces

    def brighten_face(self, face):
        median = np.median(face)
        thredshold = 220
        if median < thredshold:
            rate = thredshold / median
            face = (face.astype(np.float16) * rate)
            face[face > 255] = 255.
            face = face.astype(np.uint8)
        mean = np.mean(face)
        plt.subplot(121)
        plt.imshow(face)

        smooth = 2
        rate = (255 - mean) / (thredshold - mean)
        rate /= smooth
        face = (face.astype(np.float16) - mean) * rate + mean
        face[face > 255] = 255.
        face[face < 0] = 0.
        face = face.astype(np.uint8)
        plt.subplot(122)
        plt.imshow(face)
        return face

    def remove_jew(self, face):
        median = np.median(face)
        def find_jew_coor(img):
            x_middle = img.shape[1] // 2
            thredshold = median
            for y in range(img.shape[0] - 1, -1, -1):
                if img[y, x_middle].mean() >= thredshold:
                    return (x_middle, y)
            return (x_middle, img.shape[1] - 1)

        start_point = find_jew_coor(face)
        begin_x, begin_y = start_point
        queue = [start_point, (face.shape[1] - 1, face.shape[0] - 1), (0, face.shape[0] - 1)]
        visited = set(queue)
        fill_value = 255
        while len(queue):
            x, y = queue.pop()
            flag = 0
            if begin_y - y > abs(x - begin_x):
                continue

            if face[y, x].mean() < median:
                flag = 1
                face[y, x] = fill_value
            for add_x, add_y in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                if not flag:
                    if add_y == -1:
                        continue
                    if x - begin_x > 0:
                        if add_x < 0: continue
                    elif add_x > 0:
                        continue
                new_x, new_y = x + add_x, y + add_y
                if new_x >= face.shape[1] \
                        or new_x < 0 \
                        or new_y >= face.shape[0] \
                        or new_y < 0:
                    continue

                if (new_x, new_y) in visited: continue
                visited.add((new_x, new_y))
                queue.insert(0, (new_x, new_y))

        def get_eraser(size=10):
            erase = np.zeros((size, size), dtype=np.float16)
            center = size // 2
            for x in range(size):
                for y in range(size):
                    distance = np.sqrt((x - center) ** 2 + (y - center) ** 2)
                    erase[x, y] = 1 - distance / size * 2
            return erase

        def erase_img(img, eraser, x, y, alpha=1.0):
            if isinstance(eraser, int):
                eraser = get_eraser(eraser * 2)
            bound_y, bound_x, _ = img.shape
            erase_size = eraser.shape[0] // 2
            cut_erase = eraser[max(0, erase_size - y):min(erase_size * 2, erase_size + bound_y - y),
                        max(0, erase_size - x): min(erase_size * 2, erase_size + bound_x - x)]
            cut_erase *= alpha
            ly, ry = max(0, y - erase_size), min(y + erase_size, bound_y)
            lx, rx = max(0, x - erase_size), min(x + erase_size, bound_x)
            area = img[ly:ry, lx:rx]
            t = area[:, :, 0].astype(np.float16)
            t = 255 - ((255 - t) - (255 - t) * cut_erase)
            for i in range(3):
                area[:, :, i] = t.astype(np.uint8)

        erase_size = 2
        eraser = get_eraser(erase_size * 2)
        for x, y in visited:
            erase_img(face, eraser, x, y)

        return face

    def _resize_img_by_width(self, face_img, target_width=120):
        t = cv2.resize(face_img, (target_width, face_img.shape[0] * target_width // face_img.shape[1]))
        return t

    def get_template(self, filename='118_80_120_120.jpg'):
        template = Template(cv2.imread('../template/' + filename))
        template.ix, template.iy, template.iw, template.ih = \
            [int(x) for x in filename.split('.')[0].split('_')]

        return template

    def blend_imgs(self, face_img, template):
        theight, twidth, _ = face_img.shape
        ix, iy, iw, ih = template.ix, template.iy, template.iw, template.ih
        height, width, _ = template.img.shape
        padding = (iw - twidth) // 2

        target = cv2.copyMakeBorder(face_img,
                                    iy,
                                    height - iy - theight,
                                    ix + padding, width - ix - twidth,
                                    cv2.BORDER_CONSTANT,
                                    value=[255, 255, 255])

        target = cv2.resize(target, (template.img.shape[1], template.img.shape[0]))
        target = 255 - (255 - template.img.astype(np.int16)) - (255 - target.astype(np.int16))
        target[target > 255] = 255
        target[target < 0] = 0
        target = target.astype(np.uint8)
        return target

    def medianize(self, blended_img, face_img, template, plot=True):
        theight, twidth, _ = face_img.shape
        ix, iy, iw, ih = template.ix, template.iy, template.iw, template.ih
        height, width, _ = template.img.shape
        padding = (iw - twidth) // 2

        def set_median(refer, img, x, y, size=4):
            temp = refer[x - size // 2:x + size - size // 2, y - size // 2:y + size - size // 2]
            value = np.median(temp)
            if abs(refer[x, y][0] - value) >= 2:
                img[x, y] = value
                return True
            return False

        target = np.array(blended_img, copy=True)
        queue = [(x, iy) for x in range(ix, ix + twidth + padding)]
        queue.extend([(ix + padding + 1, y) for y in range(iy, iy + theight)])
        for i in range(3):
            queue.extend([(ix + twidth + i, y) for y in range(iy, iy + theight)])
        visited = set(queue)
        refer = np.array(target, copy=True)
        counter = 0
        while len(queue):
            x, y = queue.pop()
            if set_median(refer, target, x, y):
                counter += 1
                for add_x, add_y in ((1, 0), (-1, 0), (0, -1)):
                    new_x, new_y = x + add_x, y + add_y
                    if (new_x, new_y) in visited \
                            or new_x < 20 or new_y < 20 \
                            or new_x > ix + twidth + padding + 10 \
                            or new_y > iy + theight:
                        continue
                    queue.append((new_x, new_y))
                    visited.add((new_x, new_y))
        if plot:
            plt.figure(figsize=(16, 16))
            plt.subplot(1, 2, 1)
            _ = plt.imshow(blended_img), plt.title('origin')
            plt.subplot(1, 2, 2)
            _ = plt.imshow(target), plt.title('fixed(failed)')

        return target

    def eadge_beautify(self, blended_img, face_img, template):
        theight, twidth, _ = face_img.shape
        ix, iy, iw, ih = template.ix, template.iy, template.iw, template.ih
        height, width, _ = template.img.shape
        padding = (iw - twidth) // 2

        queue = [(x, iy, 'top', 0) for x in range(ix, ix + twidth + padding)]
        queue.extend([(ix + padding + 1, y, 'left', 0) for y in range(iy, iy + theight)])
        queue.extend([(ix + padding + twidth + 2, y, 'right', 0) for y in range(iy, iy + theight)])
        queue.extend([(ix + padding + twidth + 1, y, 'right', 0) for y in range(iy, iy + theight)])
        visited = set(queue)
        refer = np.array(blended_img, copy=True)
        interval = [90, 220]
        while len(queue):
            x, y, ty, step = queue.pop()
            if (x, y) in visited: continue
            visited.add((x, y))
            v = refer[y, x][0]
            if step >= 15: continue
            if v < interval[1]:
                if v < interval[0]:
                    step += 3
                delta = int((255.0 - float(blended_img[y, x, 0])) * (1. - float(step) / 20.))
                ans = blended_img[y, x, 0] + delta
                if ans > 255:
                    ans = 255
                elif ans < 0:
                    ans = 0
                blended_img[y, x] = ans
                if ty == 'top':
                    queue.append((x, y + 1, 'top', step + 1))
                elif ty == 'left':
                    queue.append((x + 1, y, 'left', step + 1))
                    queue.append((x + 1, y + 1, 'left', step + 1))
                    queue.append((x + 1, y - 1, 'left', step + 1))
                elif ty == 'right':
                    queue.append((x - 1, y, 'right', step + 1))
                    queue.append((x - 1, y - 1, 'right', step + 1))
                    queue.append((x - 1, y + 1, 'right', step + 1))

        blended_img[iy:iy + theight, ix: ix + 3] = 255
        blended_img[iy:iy + theight, ix + twidth: ix + twidth + 3] = 255
        return self.medianize(blended_img, face_img, template)
