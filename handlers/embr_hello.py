################################################################################
## Embr Hello — Phase 1 minimal Pybox handler
##
## Passthrough Front/Matte like Autodesk no_op.py, plus one UI control that
## posts frame / resolution info to Flame's message console.
##
## Load in Flame: point the Pybox node at this file (or symlink into
## /opt/Autodesk/shared/presets/pybox/). After edits, use Change Handler.
################################################################################

import sys
import tempfile

import pybox_v1 as pybox

LOG_BUTTON = "Log Frame Info"


class EmbrHello(pybox.BaseClass):
    def initialize(self):
        self.set_img_format("exr")

        fmt = self.get_img_format()
        tmp = tempfile.gettempdir()

        # Match no_op socket indices (Front=0, Matte=2).
        self.set_in_socket(0, "Front", tmp + "/embr_hello_in_front." + fmt)
        self.set_in_socket(2, "Matte", tmp + "/embr_hello_in_matte." + fmt)

        self.set_out_socket(0, "Result", tmp + "/embr_hello_in_front." + fmt)
        self.set_out_socket(1, "OutMatte", tmp + "/embr_hello_in_matte." + fmt)

        self.set_state_id("setup_ui")
        self.setup_ui()

    def setup_ui(self):
        log_button = pybox.create_toggle_button(LOG_BUTTON, False, col=0, row=0)
        self.add_global_elements(log_button)

        page = pybox.create_page("Embr Hello", "Debug")
        self.set_ui_pages(page)

        self.set_state_id("execute")
        self.execute()

    def execute(self):
        # Passthrough: out sockets already point at the same paths as inputs.
        for change in self.get_ui_changes():
            if change.get("name") != LOG_BUTTON:
                continue
            self._post_frame_info()
            self.set_global_element_value(LOG_BUTTON, False)

    def _post_frame_info(self):
        try:
            msg = (
                "Embr Hello: "
                "frame={frame}  "
                "size={w}x{h}  "
                "format={fmt}  "
                "bit_depth={bit}  "
                "fps={fps}  "
                "node={node}  "
                "project={project}"
            ).format(
                frame=self.get_frame(),
                w=self.get_width(),
                h=self.get_height(),
                fmt=self.get_img_format(),
                bit=self.get_bit_depth(),
                fps=self.get_framerate(),
                node=self.get_node_name(),
                project=self.get_project(),
            )
            self.set_notice_msg(msg)
        except Exception as exc:
            self.set_error_msg("Embr Hello: failed to read metadata: {0}".format(exc))

    def teardown(self):
        pass


def _main(argv):
    p = EmbrHello(argv[0])
    p.dispatch()
    p.write_to_disk(argv[0])


if __name__ == "__main__":
    _main(sys.argv[1:])
