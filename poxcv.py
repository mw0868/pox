# poxcv.py

"""POX Main Computer Vision stuff

The CVMain class wraps the Python OpenCV functionality.

- Cascade Initialization
- Single pass of Face and Eye finder

"""

import cv2


class CVMain(object):

    def __init__(self):

        self.cc_face = cv2.CascadeClassifier()
        self.cc_eyes = cv2.CascadeClassifier()

        # assume face will be "big"
        # and eyes will be smaller
        # TODO -- this might depend on scale (currently fixed at 0.5)
        self.size_face = (60, 60)
        self.size_eyes = (18, 18)

    def load_cascades(self, path):
        # try to load standard OpenCV face and eyes cascades
        face_cascade_name = path + "haarcascade_frontalface_alt.xml"
        eyes_cascade_name = path + "haarcascade_eye_tree_eyeglasses.xml"
        if not self.cc_face.load(face_cascade_name):
            print "Face cascade data failed to open:", face_cascade_name
            return False
        if not self.cc_eyes.load(eyes_cascade_name):
            print "Eyes cascade data failed to open:", eyes_cascade_name
            return False
        return True

    def detect(self, img_rgb, use_eyes=True):

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
                # TODO -- maybe add mouth or smile detection
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
                    face_roi = r[y1:y1 + face_h, x1:x1 + face_w]
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

        # return a flag indicating success if all desired features found
        # and a list of data for drawing boxes around what was found
        return b_found, boxes
