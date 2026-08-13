################################################################################
## Embr Cache Playback — Phase 2 Pybox handler
##
## Front → Result passthrough.
## OutMatte ← <job>/alpha/{frame}.exr when present; otherwise falls back to
## Matte input (if any) or Front so Flame always has a readable OutMatte file.
##
## IMPORTANT: Flame runs handlers from a temp copy under /var/tmp — never derive
## paths from __file__. Use an absolute Job Folder (default under /tmp).
################################################################################

import os
import shutil
import sys
import tempfile

import pybox_v1 as pybox

UI_JOB = "Job Folder"
UI_PADDING = "Frame Padding"
UI_OFFSET = "Frame Offset"
UI_CAPTURE = "Capture Matte to Cache"
UI_LOG = "Log Status"

ALPHA_SUBDIR = "alpha"

# Absolute defaults only (Flame copies the handler to /var/tmp).
DEFAULT_JOB = os.path.join(
    os.path.expanduser("~"), "Embr", "ml", "jobs", "mac_smoke"
)


class EmbrCachePlayback(pybox.BaseClass):
    def initialize(self):
        self.set_img_format("exr")
        fmt = self.get_img_format()
        tmp = tempfile.gettempdir()

        self._front_path = tmp + "/embr_cache_in_front." + fmt
        self._matte_path = tmp + "/embr_cache_in_matte." + fmt
        self._out_matte_path = tmp + "/embr_cache_out_matte." + fmt

        self.set_in_socket(0, "Front", self._front_path)
        self.set_in_socket(2, "Matte", self._matte_path)

        self.set_out_socket(0, "Result", self._front_path)
        self.set_out_socket(1, "OutMatte", self._out_matte_path)

        try:
            os.makedirs(os.path.join(DEFAULT_JOB, ALPHA_SUBDIR), exist_ok=True)
        except Exception:
            pass

        self.set_state_id("setup_ui")
        self.setup_ui()

    def setup_ui(self):
        # File browser is tall — keep Job column free of other widgets.
        # Frames / Actions go in separate page columns to avoid overlap.
        job_browser = pybox.create_file_browser(
            UI_JOB,
            DEFAULT_JOB,
            "",
            DEFAULT_JOB,
            row=0,
            col=0,
            page=0,
            isFileSelector=False,
        )
        padding = pybox.create_float_numeric(
            UI_PADDING, value=4.0, min=1.0, max=8.0, row=0, col=1, page=0
        )
        offset = pybox.create_float_numeric(
            UI_OFFSET, value=0.0, min=-100000.0, max=100000.0, row=1, col=1, page=0
        )
        capture = pybox.create_toggle_button(
            UI_CAPTURE, False, row=0, col=2, page=0
        )
        log_btn = pybox.create_toggle_button(UI_LOG, False, row=1, col=2, page=0)

        self.add_global_elements(job_browser, capture, log_btn)
        self.add_render_elements(padding, offset)

        page = pybox.create_page("Cache Playback", "Job", "Frames", "Actions")
        self.set_ui_pages(page)

        self.set_state_id("execute")
        self.execute()

    def execute(self):
        changes = {el.get("name") for el in self.get_ui_changes()}

        if UI_CAPTURE in changes:
            self._capture_matte()
            self.set_global_element_value(UI_CAPTURE, False)

        self._playback_matte()

        if UI_LOG in changes:
            self._log_status()
            self.set_global_element_value(UI_LOG, False)

    def _job_dir(self):
        job = self.get_global_element_value(UI_JOB)
        if job is None:
            return DEFAULT_JOB
        job = os.path.expanduser(str(job).strip())
        if not job:
            return DEFAULT_JOB
        # Guard against broken relative defaults from older builds.
        if job.startswith("/var/examples") or job == "examples/phase2_job":
            return DEFAULT_JOB
        # User sometimes selects …/alpha; cache path already appends /alpha.
        job = os.path.normpath(job)
        if os.path.basename(job).lower() == "alpha":
            job = os.path.dirname(job)
        return job

    def _cache_frame_number(self):
        pad = int(round(float(self.get_render_element_value(UI_PADDING) or 4)))
        pad = max(1, min(pad, 8))
        offset = int(round(float(self.get_render_element_value(UI_OFFSET) or 0)))
        frame = int(self.get_frame()) + offset
        return frame, pad

    def _cache_path(self):
        job = self._job_dir()
        frame, pad = self._cache_frame_number()
        name = "{frame:0{pad}d}.exr".format(frame=frame, pad=pad)
        return os.path.join(job, ALPHA_SUBDIR, name)

    def _safe_copy(self, src, dst):
        if not src or not os.path.isfile(src):
            return False
        shutil.copy2(src, dst)
        return True

    def _ensure_out_matte(self, preferred_src, note=None):
        """Flame errors/spins if OutMatte path is missing — always write a file."""
        out_matte = self.get_out_socket_path(1)
        if preferred_src and self._safe_copy(preferred_src, out_matte):
            if note:
                self.set_notice_msg(note)
            return True

        # Fallbacks so the node always produces OutMatte.
        for src in (self.get_in_socket_path(2), self.get_in_socket_path(0)):
            if self._safe_copy(src, out_matte):
                return True

        self.set_error_msg(
            "Embr Cache: could not write OutMatte (no cache / Matte / Front file)."
        )
        return False

    def _capture_matte(self):
        src = self.get_in_socket_path(2)
        dst = self._cache_path()
        if not src or not os.path.isfile(src):
            self.set_error_msg(
                "Embr Cache: Matte input missing. Keep Matte connected, show a frame, then Capture."
            )
            return
        try:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            self.set_notice_msg("Embr Cache: captured Matte → {0}".format(dst))
        except Exception as exc:
            self.set_error_msg("Embr Cache: capture failed: {0}".format(exc))

    def _playback_matte(self):
        cache = self._cache_path()
        if os.path.isfile(cache):
            self._ensure_out_matte(cache)
            return

        self.set_warning_msg("Embr Cache: missing {0} (fallback to Matte/Front)".format(cache))
        self._ensure_out_matte(None)

    def _log_status(self):
        frame, pad = self._cache_frame_number()
        cache = self._cache_path()
        self.set_notice_msg(
            "Embr Cache: job={job} frame={frame} pad={pad} exists={exists} path={path}".format(
                job=self._job_dir(),
                frame=frame,
                pad=pad,
                exists=os.path.isfile(cache),
                path=cache,
            )
        )

    def teardown(self):
        pass


def _main(argv):
    p = EmbrCachePlayback(argv[0])
    p.dispatch()
    p.write_to_disk(argv[0])


if __name__ == "__main__":
    _main(sys.argv[1:])
