import cv2
from scipy.signal import argrelmin

from arknights_mower.solvers.auto_fight import AutoFight
from arknights_mower.solvers.navigation import NavigationSolver
from arknights_mower.utils import config
from arknights_mower.utils.email import send_message
from arknights_mower.utils.graph import SceneGraphSolver
from arknights_mower.utils.image import cropimg, loadres
from arknights_mower.utils.log import logger
from arknights_mower.utils.recognize import Scene


class CreditFight(SceneGraphSolver):
    """信用作战

    从首页导航至OF-1，借助战并自动战斗
    """

    def run(self):
        logger.info("Start: 信用作战")
        self.support = False
        navi_solver = NavigationSolver()
        navi_solver.run("OF-1")
        super().run()

    def choose_support(self):
        img = cropimg(config.recog.gray, ((0, 908), (1839, 983)))
        res = loadres("fight/choose", True)
        result = cv2.matchTemplate(img, res, cv2.TM_SQDIFF_NORMED)[0]
        threshold = 0.1
        match = []
        for i in argrelmin(result, order=100)[0]:
            if result[i] < threshold:
                match.append(i)
        logger.debug(match)
        x = match[0]
        return (x, 908), (x + 194, 983)

    def current_squad(self):
        count = []
        for i in range(4):
            hsv = cropimg(
                config.recog.hsv, ((153 + i * 411, 990), (550 + i * 411, (1080)))
            )
            mask = cv2.inRange(hsv, (97, 0, 0), (101, 255, 255))
            count.append(cv2.countNonZero(mask))
        return count.index(max(count)) + 1

    def transition(self):
        if (scene := self.scene()) == Scene.OPERATOR_BEFORE:
            if config.recog.gray[65][1333] < 200:
                self.sleep()
                return
            # 取消代理作战
            if config.recog.gray[907][1600] > 127:
                self.tap((1776, 908))
                return
            self.tap_element("ope_start", interval=2)
        elif scene == Scene.OPERATOR_SELECT:
            if self.find("ope_select_start_empty"):
                logger.info("编队内没有编入干员,停止OF-1")
                return True
            squad = self.current_squad()
            target = config.conf.credit_fight.squad
            if squad != target:
                self.tap((target * 411 - 99, 1040))
                return
            if self.support:
                # 开始行动
                self.tap((1655, 781))
                fight_solver = AutoFight()
                conf = config.conf.credit_fight
                actions = [
                    {"type": "SpeedUp"},
                    {
                        "type": "Deploy",
                        "name": conf.operator,
                        "location": [
                            conf.x,
                            conf.y,
                        ],
                        "direction": conf.direction,
                    },
                    {"type": "SkillDaemon"},
                ]
                fight_solver.run("OF-1", [], actions)
            else:
                # 借助战
                self.ctap((1660, 315))
        elif scene == Scene.OPERATOR_SUPPORT:
            self.tap(self.choose_support())
            self.support = True
        elif scene == Scene.OPERATOR_STRANGER_SUPPORT:
            self.tap_element("fight/use")
        elif scene == Scene.OPERATOR_FINISH:
            return True
        elif scene == Scene.OPERATOR_FAILED:
            msg = "OF-1失败，请检查干员，*今天*不会继续进行信用作战"
            logger.info(msg)
            send_message(msg, level="ERROR")
            return True
        elif scene in self.waiting_scene:
            self.waiting_solver()
        else:
            navi_solver = NavigationSolver()
            navi_solver.run("OF-1")
