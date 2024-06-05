import lzma
import pickle
from datetime import datetime

import cv2
from arknights_mower.utils.image import loadres, saveimg
from arknights_mower.utils.log import logger
from arknights_mower.utils.matcher import ORB
from arknights_mower.utils.path import get_path
from arknights_mower.utils.solver import BaseSolver


class NavigationSolver(BaseSolver):
    location = {
        "BP-1": (0, 0),
        "BP-2": (429, 76),
        "BP-3": (690, -67),
        "BP-4": (956, 47),
        "BP-5": (1220, 160),
        "BP-6": (1549, 1),
        "BP-7": (1790, 471),
        "BP-8": (2000, 341),
    }

    def run(self, name: str) -> None:
        logger.info("Start: 关卡导航")
        self.name = name
        with lzma.open(
            get_path("@install/tmp/hot_update/path_of_life/names.pkl"), "rb"
        ) as f:
            self.names = pickle.load(f)

        self.back_to_index()
        return super().run()

    def transition(self) -> bool:
        if self.find("connecting"):
            self.sleep()
        elif self.recog.detect_index_scene():
            self.tap_index_element("terminal")
        elif self.find("terminal_pre"):
            img = loadres("@hot/path_of_life/terminal.jpg", True)
            kp1, des1 = ORB.detectAndCompute(img, None)
            kp2, des2 = ORB.detectAndCompute(self.recog.gray, None)
            FLANN_INDEX_LSH = 6
            index_params = dict(
                algorithm=FLANN_INDEX_LSH,
                table_number=6,  # 12
                key_size=12,  # 20
                multi_probe_level=0,  # 2
            )
            search_params = dict(checks=50)
            flann = cv2.FlannBasedMatcher(index_params, search_params)
            matches = flann.knnMatch(des1, des2, k=2)
            GOOD_DISTANCE_LIMIT = 0.7
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
            self.tap(kp2[good[0].trainIdx].pt, interval=4)
        elif pos := self.find("@hot/path_of_life/entry"):
            self.tap(pos, interval=2)
        elif self.find("@hot/path_of_life/banner"):
            name, val, loc = "BP-1", 1, None
            for i in range(1, 9):
                result = cv2.matchTemplate(
                    self.recog.gray,
                    self.names[i],
                    cv2.TM_SQDIFF_NORMED,
                )
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                if min_val < val:
                    val = min_val
                    loc = min_loc
                    name = f"BP-{i}"

            def va(a, b):
                return a[0] + b[0], a[1] + b[1]

            def vm(a, b):
                return a[0] - b[0], a[1] - b[1]

            target = va(vm(loc, self.location[name]), self.location[self.name])
            if target[0] + 200 > 1920:
                self.swipe_noinertia((1400, 540), (-800, 0))
            elif target[0] < 0:
                self.swipe_noinertia((400, 540), (800, 0))
            else:
                self.tap((target[0] + 60, target[1] + 20))
        elif self.find("ope_start"):
            return True
        else:
            self.sleep()


if datetime.now() > datetime(2024, 6, 19, 4):
    NavigationSolver.location = {}
