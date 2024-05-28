from datetime import datetime, timedelta
from typing import Optional

import cv2
from arknights_mower.utils.image import loadres, saveimg
from arknights_mower.utils.log import logger
from arknights_mower.utils.matcher import ORB
from arknights_mower.utils.solver import BaseSolver


class TaskManager:
    def __init__(self):
        self.task_list = ["back_to_index"]

    @property
    def task(self):
        return self.task_list[0] if self.task_list else None

    def add(self, task: str, year: int, month: int, day: int):
        if datetime.now() > datetime(year, month, day):
            return
        self.task_list.insert(-1, task)

    def complete(self, task: Optional[str]):
        task = task or self.task
        if task in self.task_list:
            self.task_list.remove(task)


monthly_card = "monthly_card"
lone_trail = "lone_trail"


class SignInSolver(BaseSolver):
    def run(self) -> None:
        logger.info("Start: 签到活动")
        self.back_to_index()
        self.tm = TaskManager()
        self.tm.add(monthly_card, 2024, 6, 1)  # 五周年专享月卡
        self.tm.add(lone_trail, 2024, 6, 7)  # 孤星领箱子

        self.failure = 0
        self.in_progress = False
        self.start_time = datetime.now()
        return super().run()

    def notify(self, msg):
        logger.info(msg)
        self.recog.save_screencap("sign_in")
        if hasattr(self, "send_message_config") and self.send_message_config:
            self.send_message(msg, attach_image=self.recog.img)

    def handle_unknown(self):
        self.failure += 1
        if self.failure > 30:
            self.notify("签到任务执行失败！")
            self.back_to_index()
            return True
        self.sleep()

    def transition(self) -> bool:
        if datetime.now() - self.start_time > timedelta(minutes=2):
            self.notify("签到任务超时！")
            self.back_to_index()
            return True
        if not self.tm.task:
            return True

        if self.find("connecting"):
            return self.handle_unknown()
        elif self.recog.detect_index_scene():
            if self.tm.task == "back_to_index":
                self.tm.complete("back_to_index")
                return True
            elif self.tm.task == monthly_card:
                if pos := self.find("@hot/monthly_card/entry"):
                    self.tap(pos)
                else:
                    self.notify("未检测到五周年月卡领取入口！")
                    self.tm.complete(monthly_card)
            elif self.tm.task == lone_trail:
                self.tap_index_element("terminal")
            else:
                return True
        elif self.find("@hot/monthly_card/banner"):
            if self.tm.task == monthly_card:
                if pos := self.find("@hot/monthly_card/button_ok"):
                    self.ctap(pos, max_seconds=10)
                else:
                    self.notify("今天的五周年专享月卡已经领取过了")
                    self.tm.complete(monthly_card)
                    self.back()
            else:
                self.back()
        elif self.find("materiel_ico"):
            if self.tm.task == monthly_card:
                self.notify("成功领取五周年专享月卡")
                self.tm.complete(monthly_card)
            elif self.tm.task == lone_trail:
                self.notify("成功领取孤星箱子")
                self.tm.complete(lone_trail)
            self.tap((960, 960))
        elif self.find("terminal_pre"):
            if self.tm.task == lone_trail:
                img = loadres("@hot/lone_trail/terminal.jpg", True)
                kp1, des1 = ORB.detectAndCompute(img, None)
                kp2, des2 = ORB.detectAndCompute(self.recog.gray, None)
                FLANN_INDEX_LSH = 6
                index_params = dict(
                    algorithm=FLANN_INDEX_LSH,
                    table_number=6,  # 12
                    key_size=12,  # 20
                    multi_probe_level=1,  # 2
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
            else:
                self.back()
        elif pos := self.find("@hot/lone_trail/investigation"):
            if self.tm.task == lone_trail:
                self.tap(pos, interval=3)
            else:
                self.back()
        elif self.find("@hot/lone_trail/box"):
            if self.tm.task == lone_trail:
                self.ctap((960, 780))
            else:
                self.back()
        elif self.find("@hot/lone_trail/not_available"):
            if self.tm.task == lone_trail:
                self.notify("孤星箱子已经领完了")
                self.tm.complete(lone_trail)
            self.back()
        elif pos := self.recog.check_announcement():
            self.tap(pos)
        else:
            return self.handle_unknown()
