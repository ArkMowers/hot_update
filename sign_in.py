from datetime import datetime, timedelta
from typing import Optional

import cv2
import numpy as np
from arknights_mower.utils.graph import SceneGraphSolver
from arknights_mower.utils.log import logger
from arknights_mower.utils.scene import Scene
from arknights_mower.utils.vector import va


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


rogue = "rogue"


class SignInSolver(SceneGraphSolver):
    def run(self) -> None:
        logger.info("Start: 签到活动")
        self.scene_graph_navigation(Scene.INDEX)
        self.tm = TaskManager()
        self.tm.add(rogue, 2024, 7, 19)  # 无终奇语签到活动

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
            self.scene_graph_navigation(Scene.INDEX)
            return True
        self.sleep()

    def transition(self) -> bool:
        if datetime.now() - self.start_time > timedelta(minutes=2):
            self.notify("签到任务超时！")
            self.scene_graph_navigation(Scene.INDEX)
            return True
        if not self.tm.task:
            return True

        if self.find("connecting"):
            return self.handle_unknown()
        elif self.recog.detect_index_scene():
            if self.tm.task == rogue:
                if pos := self.find("@hot/rogue/entry"):
                    self.tap(pos)
                else:
                    self.notify("未检测到无终奇语签到活动入口！")
                    self.tm.complete(rogue)
            else:
                self.tm.complete("back_to_index")
        elif self.find("@hot/rogue/banner"):
            if self.tm.task == rogue:
                img = cv2.cvtColor(self.recog.img, cv2.COLOR_RGB2HSV)
                img1 = cv2.inRange(img, (0, 200, 0), (5, 255, 255))
                img2 = cv2.inRange(img, (175, 200, 0), (180, 255, 255))
                img = cv2.bitwise_or(img1, img2)
                tpl = np.zeros((100, 100), dtype=np.uint8)
                tpl[:] = (255,)
                result = cv2.matchTemplate(img, tpl, cv2.TM_CCORR_NORMED)
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                if max_val > 0.9:
                    self.in_progress = True
                    self.ctap(va(max_loc, (50, 50)))
                else:
                    if not self.in_progress:
                        self.notify("无终奇语签到奖励已领完")
                    self.in_progress = False
                    self.tm.complete(rogue)
                    self.back()
            else:
                self.back()
        elif self.find("materiel_ico"):
            self.sleep()
            if self.tm.task == rogue:
                self.notify("无终奇语活动签到成功")
            else:
                self.notify("物资领取")
            self.tap((960, 960))
        elif pos := self.recog.check_announcement():
            self.tap(pos)
        else:
            return self.handle_unknown()
