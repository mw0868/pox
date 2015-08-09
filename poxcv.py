# poxcv.py

"""POX Main Computer Vision stuff

The CVMain class wraps the Python OpenCV functionality.

- Cascade Initialization
- Single pass of Face, Eye, and Grin finder

"""

import cv2


class CVMain(object):

    def __init__(self):

        self.cc_face = cv2.CascadeClassifier()
        self.cc_eyes = cv2.CascadeClassifier()
        self.cc_grin = cv2.CascadeClassifier()

        # assume face will be "big"
        # and eyes will be smaller
        # suitable limits here will increase frame rate
        # TODO -- this might depend on scale (currently fixed at 0.5)
        self.size_face = (60, 60)
        self.size_eyes = (18, 18)

        # grin detection tweak
        # - use 2 for mouth detector
        # - use big number like 70-140 for smile detector
        # TODO -- tune during start-up ?
        self.magic = 140

    def load_cascades(self, path):
        # try to load standard OpenCV face/eyes/grin cascades
        face_cascade_name = path + "haarcascade_frontalface_alt.xml"
        eyes_cascade_name = path + "haarcascade_eye_tree_eyeglasses.xml"
        grin_cascade_name = path + "haarcascade_smile.xml"
        #grin_cascade_name = "haarcascade_mcs_mouth.xml"

        if not self.cc_face.load(face_cascade_name):
            print "Face cascade data failed to open:", face_cascade_name
            return False
        if not self.cc_eyes.load(eyes_cascade_name):
            print "Eyes cascade data failed to open:", eyes_cascade_name
            return False
        if not self.cc_grin.load(path + grin_cascade_name):
            print "Grin cascade data failed to open."
            return False
        return True

    def detect(self, img_rgb, use_eyes=True, use_grin=False):

        # convert to gray
        # and equalize (since demo code does this too)
        r = cv2.cvtColor(img_rgb, cv2.COLOR_BGR2GRAY)
        cv2.equalizeHist(r, r)

        # assume eyes found
        # this will be applied to debounce
        # if face or eye detections fail (rare)
        b_found = False

        # each box element will be a list of form [pt1, pt2]
        boxes = []

        # first find one face
        obj_face = self.cc_face.detectMultiScale(r, 1.1, 2, 0, self.size_face)
        if len(obj_face) == 1:
            for face in obj_face:
                # create face box with sub-boxes for eyes and mouth
                # horizontal line 5/8 from top of face box
                # to separate mouth region and rest of face
                face_x, face_y = face[:2]
                face_w, face_h = face[2:]
                yfrac = (face_h * 5) / 8
                halfx = face_x + face_w / 2
                y1 = face_y
                x1 = face_x

                boxes.append([(x1, y1), (halfx, y1 + yfrac)])
                boxes.append([(halfx, y1), (x1 + face_w, y1 + yfrac)])
                boxes.append([(x1, y1 + yfrac), (x1 + face_w, y1 + face_h)])
                b_found = True

                if use_eyes:
                    # seek eyes in face region
                    # use "4" for rectangle threshold (fewer False detections)
                    # assume frame is "good" if more than 2 eyes
                    face_roi = r[y1:y1 + yfrac, x1:x1 + face_w]
                    obj_eyes = self.cc_eyes.detectMultiScale(face_roi, 1.1, 4,
                                                             0,
                                                             self.size_eyes)

                    b_found = b_found and (len(obj_eyes) > 0)
                    if len(obj_eyes) > 2:
                        # just FYI if needed for debugging
                        # print "invalid eye count"
                        pass

                    # generate eye box data
                    for eye in obj_eyes:
                        eye_x, eye_y = eye[:2]
                        eye_w, eye_h = eye[2:]
                        eye_pt1 = (face_x + eye_x, face_y + eye_y)
                        eye_pt2 = (eye_pt1[0] + eye_w, eye_pt1[1] + eye_h)
                        boxes.append([eye_pt1, eye_pt2])

                if use_grin:
                    # increase upper/lower bounds on mouth region
                    # need even bigger lower bounds if using "mouth" detector
                    # (makes it possible to detect wide-open mouth)
                    # inc_y = (face_h / 8)
                    y1m = (y1 + yfrac) # - inc_y
                    y2m = (y1 +face_h) # + inc_y

                    # try to find grin in mouth area
                    grin_roi = r[y1m:y2m, x1:x1 + face_w]
                    gw = (face_w * 3) / 8  # min 3/8 of mouth region w
                    gh = (face_h - yfrac) / 3  # min 1/3 of mouth region h
                    obj_grin = self.cc_grin.detectMultiScale(grin_roi, 1.1,
                                                             self.magic, 0,
                                                             (gw, gh))

                    # apply grin detection to found flag
                    b_found = b_found and (len(obj_grin) > 0)

                    # generate grin box data
                    # must uncomment offset below if using bigger mouth region
                    for grin in obj_grin:
                        grin_x, grin_y = grin[:2]
                        grin_w, grin_h = grin[2:]
                        grin_pt1 = (face_x + grin_x,
                                    face_y + yfrac + grin_y) # - inc_y)
                        grin_pt2 = (grin_pt1[0] + grin_w,
                                    grin_pt1[1] + grin_h)
                        boxes.append([grin_pt1, grin_pt2])

        # return a flag indicating success if all desired features found
        # and a list of data for drawing boxes around what was found
        return b_found, boxes
