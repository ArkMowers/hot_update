from datetime import datetime, timedelta
from typing import Optional

from arknights_mower.utils.log import logger
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


dragon_boat_festival = "dragon_boat_festival"


class SignInSolver(BaseSolver):
    def run(self) -> None:
        logger.info("Start: 签到活动")
        self.back_to_index()
        self.tm = TaskManager()
        self.tm.add(dragon_boat_festival, 2024, 6, 17)  # 端午节

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
            if self.tm.task == dragon_boat_festival:
                self.in_progress = False
                if pos := self.find("@hot/dragon_boat_festival/entry"):
                    self.tap(pos)
                else:
                    self.notify("未检测到端午签到活动入口！")
                    self.tm.complete(dragon_boat_festival)
            else:
                self.tm.complete("back_to_index")
        elif self.find("@hot/dragon_boat_festival/banner"):
            if self.tm.task == dragon_boat_festival:
                if self.in_progress:
                    self.sleep()
                    return
                if pos := self.find("@hot/dragon_boat_festival/button"):
                    self.in_progress = True
                    self.ctap(pos)
                else:
                    self.notify("奖励已领取")
                    self.tm.complete(dragon_boat_festival)
            else:
                self.back()
        elif self.find("materiel_ico"):
            self.sleep()
            if self.tm.task == dragon_boat_festival:
                self.in_progress = False
                self.notify("端午节活动签到成功")
                self.tm.complete(dragon_boat_festival)
            else:
                self.notify("物资领取")
            self.tap((960, 960))
        elif pos := self.recog.check_announcement():
            self.tap(pos)
        else:
            return self.handle_unknown()
