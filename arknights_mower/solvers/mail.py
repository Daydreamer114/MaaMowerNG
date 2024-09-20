from arknights_mower.utils.graph import SceneGraphSolver
from arknights_mower.utils.log import logger
from arknights_mower.utils.recognize import Scene


class MailSolver(SceneGraphSolver):
    def run(self) -> None:
        self.touched = False

        logger.info("Start: 领取邮件")
        super().run()

    def transition(self) -> bool:
        if self.scene() == Scene.MAIL:
            if self.touched:
                return True
            self.touched = True
            self.tap_element("read_mail")
        else:
            self.scene_graph_step(Scene.MAIL)
