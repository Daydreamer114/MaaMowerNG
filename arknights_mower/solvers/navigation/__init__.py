import re

import cv2

from arknights_mower.models import navigation
from arknights_mower.utils import config
from arknights_mower.utils.graph import SceneGraphSolver
from arknights_mower.utils.image import thres2
from arknights_mower.utils.log import logger
from arknights_mower.utils.scene import Scene
from arknights_mower.utils.vector import va, vs

from .activity import ActivityNavigation
from .last_stage import LastStageNavigation

location = {
    1: {
        "1-1": (0, 0),
        "1-2": (428, -1),
        "1-3": (700, 157),
        "1-4": (1138, 158),
        "1-5": (1600, 158),
        "1-6": (2360, -1),
        "1-7": (3073, -180),
        "1-8": (3535, -181),
        "1-9": (4288, -1),
        "1-10": (4635, 167),
        "1-11": (4965, -9),
        "1-12": (5436, -10),
    },
    8: {
        "R8-1": (0, 0),
        "R8-2": (471, 0),
        "R8-3": (864, 0),
        "R8-4": (1259, 0),
        "R8-5": (1651, -4),
        "R8-6": (2045, -4),
        "R8-7": (2228, -124),
        "R8-8": (2437, -4),
        "R8-9": (2951, -4),
        "R8-10": (3284, -4),
        "R8-11": (3617, -4),
        "M8-1": (6, 339),
        "M8-2": (865, 339),
        "M8-3": (1259, 339),
        "M8-4": (1651, 339),
        "M8-5": (2045, 339),
        "M8-6": (2439, 340),
        "M8-7": (2952, 340),
        "M8-8": (3617, 339),
        "JT8-1": (4092, 171),
        "JT8-2": (4545, 171),
        "JT8-3": (5022, 171),
        "H8-1": (5556, -24),
        "H8-2": (5759, 354),
        "H8-3": (5999, -24),
        "H8-4": (6192, 354),
    },
    12: {
        "12-1": (0, 0),
        "12-2": (342, 292),
        "12-3": (701, 292),
        "12-4": (894, 121),
        "12-5": (1122, 292),
        "12-6": (1364, 121),
        "12-7": (1515, 292),
        "12-8": (2109, 290),
        "12-9": (2468, 290),
        "12-10": (2670, 125),
        "12-11": (2980, 422),
        "12-12": (3218, 125),
        "12-13": (3456, 294),
        "12-14": (3694, 123),
        "12-15": (4020, 123),
        "12-16": (4348, -14),
        "12-17": (4673, -14),
        "12-18": (4673, 210),
        "12-19": (5175, 210),
        "12-20": (5700, 210),
        "12-21": (6377, 210),
    },
    "OF": {
        "OF-1": (0, 0),
        "OF-2": (738, 144),
        "OF-3": (1122, 299),
        "OF-4": (1475, 135),
        "OF-5": (2288, -45),
        "OF-6": (2737, -45),
        "OF-7": (3550, 135),
        "OF-8": (3899, 299),
    },
    "AP": {
        "AP-1": (0, 0),
        "AP-2": (416, -74),
        "AP-3": (716, -247),
        "AP-4": (964, -417),
        "AP-5": (1116, -589),
    },
    "LS": {
        "LS-1": (0, 0),
        "LS-2": (385, -34),
        "LS-3": (710, -130),
        "LS-4": (970, -257),
        "LS-5": (1138, -421),
        "LS-6": (1213, -600),
    },
    "CA": {
        "CA-1": (0, 0),
        "CA-2": (416, -73),
        "CA-3": (716, -246),
        "CA-4": (964, -417),
        "CA-5": (1116, -589),
    },
    "CE": {
        "CE-1": (0, 0),
        "CE-2": (382, -33),
        "CE-3": (709, -128),
        "CE-4": (970, -259),
        "CE-5": (1136, -420),
        "CE-6": (1210, -597),
    },
    "SK": {
        "SK-1": (0, 0),
        "SK-2": (416, -73),
        "SK-3": (716, -246),
        "SK-4": (965, -417),
        "SK-5": (1116, -589),
    },
    "PR-A": {"PR-A-1": (0, 0), "PR-A-2": (604, -283)},
    "PR-B": {"PR-B-1": (0, 0), "PR-B-2": (684, -296)},
    "PR-C": {"PR-C-1": (0, 0), "PR-C-2": (667, -231)},
    "PR-D": {"PR-D-1": (0, 0), "PR-D-2": (639, -260)},
}

collection_prefixs = [
    "AP",
    "LS",
    "CA",
    "CE",
    "PR",
    "SK",
]

difficulty_str = [
    "normal",
    "hard",
]


class NavigationSolver(SceneGraphSolver):
    def run(self, name: str):
        if LastStageNavigation().run(name):
            return True
        if name in ActivityNavigation.location:
            ActivityNavigation().run(name)
            return True

        self.success = False
        self.act = None
        self.name = name
        prefix = name.split("-")[0]
        pr_prefix = ""
        if prefix == "PR":
            pr_prefix = name.split("-")[1]
        self.prefix = prefix
        self.pr_prefix = pr_prefix
        self.now_difficulty = None
        self.change_to = None
        self.patten = r"^(R|JT|H|M)(\d{1,2})$"
        if name == "Annihilation":
            logger.info("剿灭导航")
        elif prefix.isdigit() or re.match(self.patten, prefix):
            if match := re.search(self.patten, prefix):
                prefix = match.group(2)
            prefix = int(prefix)
            self.prefix = prefix
            if prefix in location and name in location[prefix]:
                logger.info(f"主线关卡导航：{name}")
                if prefix < 4:
                    act = 0
                elif prefix < 9:
                    act = 1
                else:
                    act = 2
                self.act = act
            else:
                logger.error(f"暂不支持{name}")
                return False
        elif prefix in ["OF"]:
            logger.info(f'别传关卡导航："{name}"')
        elif prefix in ["AP", "LS", "CA", "CE", "SK"]:
            logger.info(f'资源收集关卡导航："{name}"')
        elif prefix.split("-")[0] in ["PR"]:
            logger.info(f'芯片关卡导航："{name}"')

        else:
            logger.error(f"暂不支持{name}")
            return False

        super().run()
        return self.success

    def transition(self):
        if (scene := self.scene()) == Scene.TERMINAL_MAIN:
            if self.name == "Annihilation":
                if pos := self.find("terminal_eliminate"):
                    self.tap(pos)
                else:
                    logger.info("本周剿灭已完成")
                    return True
            elif isinstance(self.prefix, int):
                self.tap_terminal_button("main_theme")
            elif self.prefix in ["OF"]:
                self.tap_terminal_button("biography")
            elif self.prefix in collection_prefixs:
                self.tap_terminal_button("collection")
        elif scene == Scene.OPERATOR_ELIMINATE:
            if self.name != "Annihilation":
                self.back()
                return
            self.success = True
            return True
        elif scene == Scene.TERMINAL_MAIN_THEME:
            if not isinstance(self.prefix, int):
                self.back()
                return
            act_scope = ((300, 315), (400, 370))

            if self.find(f"navigation/act/{self.act}", scope=act_scope):
                if pos := self.find(f"navigation/main/{self.prefix}"):
                    self.tap(pos)
                else:
                    config.device.swipe_ext(
                        ((932, 554), (1425, 554), (1425, 554)), durations=[300, 100]
                    )
                    config.recog.update()
            else:
                self.tap((230, 175))
        elif scene == Scene.TERMINAL_BIOGRAPHY:
            if self.prefix not in ["OF"]:
                self.back()
                return
            if self.find(f"navigation/biography/{self.prefix}_banner"):
                self.tap_element("navigation/entry")
                return
            self.tap_element(f"navigation/biography/{self.prefix}_entry")
        elif scene == Scene.TERMINAL_COLLECTION:
            prefix = self.prefix
            val = 0.9
            if self.prefix not in collection_prefixs:
                self.back()
                return
            if self.prefix == "PR":
                prefix = self.prefix + "-" + self.pr_prefix
            if self.prefix not in ["LS"]:
                if self.find(f"navigation/collection/{prefix}_not_available"):
                    logger.info(f"{self.name}未开放")
                    return True
            if pos := self.find(f"navigation/collection/{prefix}_entry"):
                self.tap(pos)
            else:
                if self.prefix in ["AP", "CA", "CE", "SK"]:
                    self.swipe_noinertia((900, 500), (600, 0))
                if self.prefix in ["PR"]:
                    self.swipe_noinertia((900, 500), (-600, 0))
        elif scene == Scene.OPERATOR_CHOOSE_LEVEL:
            non_black_count = cv2.countNonZero(thres2(config.recog.gray, 10))
            non_black_ratio = non_black_count / (1920 * 1080)
            logger.debug(f"{non_black_ratio=}")
            if non_black_ratio < 0.1:
                self.sleep()
                return
            name, val, loc = "", 1, None
            prefix = self.prefix
            # 资源收集关直接按坐标点击
            if prefix in collection_prefixs:
                if self.prefix == "PR":
                    prefix = "{}-{}".format(self.prefix, self.pr_prefix)
                if pos := self.find(f"navigation/collection/{prefix}-1"):
                    self.success = True
                    self.tap(va(pos[0], location[prefix][self.name]))
                return True
            # 其余关
            if self.act == 2:
                if self.now_difficulty is None:
                    if self.find("navigation/ope_normal"):
                        self.now_difficulty = 0
                    elif self.find("navigation/ope_hard"):
                        self.now_difficulty = 1
                    logger.info(f"当前难度{difficulty_str[self.now_difficulty]}")

                if self.change_to is not None and self.now_difficulty != self.change_to:
                    config.recog.update()
                    if self.find("navigation/ope_difficulty"):
                        self.tap_element(
                            f"navigation/ope_{difficulty_str[self.change_to]}_small"
                        )
                        self.now_difficulty = None
                    else:
                        self.tap_element(
                            f"navigation/ope_{difficulty_str[self.now_difficulty]}"
                        )
                        return
            for i in location[prefix]:
                result = cv2.matchTemplate(
                    config.recog.gray, navigation[i], cv2.TM_SQDIFF_NORMED
                )
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                if min_val < val:
                    val = min_val
                    loc = min_loc
                    name = i

            target = va(vs(loc, location[prefix][name]), location[prefix][self.name])
            if target[0] + 200 > 1920:
                self.swipe_noinertia((1400, 540), (-800, 0))
            elif target[0] < 0:
                self.swipe_noinertia((400, 540), (800, 0))
            else:
                self.success = True
                self.tap(va(target, (60, 20)))
        elif scene == Scene.OPERATOR_BEFORE:
            if self.act == 2:
                if self.change_to is not None:
                    logger.info(f"{self.name} 无法代理")
                    self.success = False
                    self.back_to_index()
                    return True
                if self.find("ope_agency_lock"):
                    self.change_to = self.now_difficulty ^ 1
                    logger.info(
                        f"{self.name} {difficulty_str[self.now_difficulty]} 无法代理，切难度尝试"
                    )
                    self.back()
                    return
            if self.success:
                return True
            else:
                self.back()
        else:
            self.scene_graph_step(Scene.TERMINAL_MAIN)
