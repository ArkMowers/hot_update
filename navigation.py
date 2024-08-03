import lzma
import pickle
from datetime import datetime

import cv2
from arknights_mower.utils.image import loadres, saveimg
from arknights_mower.utils.log import logger
from arknights_mower.utils.matcher import (
    GOOD_DISTANCE_LIMIT,
    flann,
    keypoints_scale_invariant,
)
from arknights_mower.utils.path import get_path
from arknights_mower.utils.solver import BaseSolver
from arknights_mower.utils.vector import va, vs


class classproperty:
    def __init__(self, method=None):
        self.fget = method

    def __get__(self, instance, cls=None):
        return self.fget(cls)

    def getter(self, method):
        self.fget = method
        return self


class NavigationSolver(BaseSolver):
    _location = {
        "AS-1": (0, 0),
        "AS-2": (483, -146),
        "AS-3": (788, -30),
        "AS-4": (1087, -138),
        "AS-5": (1370, -309),
        "AS-6": (2061, -206),
        "AS-7": (2130, 19),
        "AS-8": (2446, -61),
        "AS-9": (2675, -254),
    }

    @classproperty
    def location(cls):
        if datetime.now() > datetime(2024, 8, 22, 4):
            return {}
        return cls._location

    def run(self, name: str) -> None:
        logger.info("Start: 活动关卡导航")
        self.name = name
        with lzma.open(get_path("@install/tmp/hot_update/inudi/names.pkl"), "rb") as f:
            self.names = pickle.load(f)

        self.back_to_index()
        return super().run()

    def transition(self) -> bool:
        if self.find("connecting"):
            self.sleep()
        elif self.recog.detect_index_scene():
            self.tap_index_element("terminal")
        elif self.find("terminal_main"):
            img = loadres("@hot/inudi/terminal", True)
            kp1, des1 = keypoints_scale_invariant(img)
            kp2, des2 = self.recog.matcher.kp, self.recog.matcher.des
            matches = flann.knnMatch(des1, des2, k=2)
            good = []
            for pair in matches:
                if (len_pair := len(pair)) == 2:
                    x, y = pair
                    if x.distance < GOOD_DISTANCE_LIMIT * y.distance:
                        good.append(x)
                elif len_pair == 1:
                    good.append(pair[0])
            good = sorted(good, key=lambda x: x.distance)
            debug_img = cv2.drawMatches(
                img,
                kp1,
                self.recog.gray,
                kp2,
                good[:10],
                None,
                flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS,
            )
            saveimg(debug_img, "navigation")
            self.tap(kp2[good[0].trainIdx].pt, interval=3)
        elif pos := self.find("@hot/inudi/entry"):
            self.tap(pos, interval=2)
        elif self.find("@hot/inudi/banner"):
            name, val, loc = None, 1, None
            for n, img in self.names.items():
                result = cv2.matchTemplate(self.recog.gray, img, cv2.TM_SQDIFF_NORMED)
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                if min_val < val:
                    val = min_val
                    loc = min_loc
                    name = n

            target = va(vs(loc, self.location[name]), self.location[self.name])
            if target[0] + 200 > 1920:
                self.swipe_noinertia((1400, 540), (-1000, 0))
            elif target[0] < 0:
                self.swipe_noinertia((400, 540), (1000, 0))
            else:
                self.tap(va(target, (60, 20)))
        elif self.find("ope_start"):
            return True
        else:
            self.sleep()
