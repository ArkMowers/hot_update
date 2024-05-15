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


class SignInSolver(BaseSolver):
    def run(self) -> None:
        logger.info("Start: 签到活动")
        self.back_to_index()
        self.tm = TaskManager()
        self.tm.add("monthly_card", 2024, 6, 1)  # 五周年专享月卡

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
            elif self.tm.task == "monthly_card":
                if pos := self.find("@hot/monthly_card/entry"):
                    self.tap(pos)
                else:
                    self.notify("未检测到五周年月卡领取入口！")
                    self.tm.complete("monthly_card")
            else:
                return True
        elif self.find("@hot/monthly_card/banner"):
            if self.tm.task == "monthly_card":
                if pos := self.find("@hot/monthly_card/button_ok"):
                    self.ctap(pos, max_seconds=10)
                else:
                    self.notify("今天的五周年专享月卡已经领取过了")
                    self.tm.complete("monthly_card")
                    self.back()
            else:
                self.back()
        elif self.find("materiel_ico"):
            if self.tm.task == "monthly_card":
                self.notify("成功领取五周年专享月卡")
                self.tm.complete("monthly_card")
            self.tap((960, 960))
        else:
            return self.handle_unknown()
