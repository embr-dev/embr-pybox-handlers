################################################################################
## Embr Matte — Batch node: Front + guide Matte → async MatAnyone → Result/OutMatte
##
## UX:
##   - Runtime under ~/Embr ($EMBR_HOME): ml/, bin/uv, repos/embr-pybox-handlers
##   - Job path is per Pybox node (Job Path UI; Flame keeps it with the node).
##   - Init Job creates $EMBR_ML_ROOT/jobs/<name> and sets this node's path.
##   - Buttons are logically gated (Pybox cannot grey them out).
##   - Record Front stays manual (Play/scrub) for now.
##
## IMPORTANT: Flame copies handlers under /var/tmp — never use __file__ paths.
################################################################################

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime

import pybox_v1 as pybox

UI_JOB_PATH = "Job Path"
UI_JOB_NAME = "Job Name"
UI_INIT = "Init Job"
UI_REPO = "Repo Root"
UI_DEVICE = "Device"
UI_PADDING = "Frame Padding"
UI_OFFSET = "Frame Offset"
UI_EXPECTED = "Expected Frames"
UI_RECORD = "Record Front"
UI_GUIDE = "Capture Guide Matte"
UI_RUN = "Run Matte"
UI_STATUS = "Refresh Status"
UI_HUD = "Show HUD"

ALPHA_SUBDIR = "alpha"
FGR_SUBDIR = "fgr"
INPUT_SUBDIR = "input"
STATUS_NAME = "status.json"
PID_NAME = "run.pid"
LOG_NAME = "run.log"
HUD_JSON = "hud_info.json"

DEFAULT_EMBR_HOME = os.path.expanduser("~/Embr")
DEFAULT_ML_ROOT = os.path.join(DEFAULT_EMBR_HOME, "ml")
DEFAULT_REPO_PREFERRED = os.path.join(
    DEFAULT_EMBR_HOME, "repos", "embr-pybox-handlers"
)
# Dev fallback while repos/ clone is not yet the canonical install location.
_LEGACY_DEV_REPO = "/Users/oue.isamu/Projects/embr-pybox-handlers"
DEFAULT_DEVICE = "mps" if sys.platform == "darwin" else "cuda:0"
NO_JOB_LABEL = "(press Init Job)"


def _default_repo_root():
    if os.path.isdir(DEFAULT_REPO_PREFERRED):
        return DEFAULT_REPO_PREFERRED
    if os.path.isdir(_LEGACY_DEV_REPO):
        return _LEGACY_DEV_REPO
    return DEFAULT_REPO_PREFERRED


DEFAULT_REPO = _default_repo_root()


class EmbrMatte(pybox.BaseClass):
    def initialize(self):
        self.set_img_format("exr")
        fmt = self.get_img_format()
        tmp = tempfile.gettempdir()

        self._front_path = tmp + "/embr_matte_in_front." + fmt
        self._matte_path = tmp + "/embr_matte_in_matte." + fmt
        self._out_result_path = tmp + "/embr_matte_out_result." + fmt
        self._out_matte_path = tmp + "/embr_matte_out_matte." + fmt

        self.set_in_socket(0, "Front", self._front_path)
        self.set_in_socket(2, "Matte", self._matte_path)
        self.set_out_socket(0, "Result", self._out_result_path)
        self.set_out_socket(1, "OutMatte", self._out_matte_path)

        for src in (self._front_path, self._matte_path):
            if os.path.isfile(src):
                try:
                    shutil.copy2(src, self._out_result_path)
                    shutil.copy2(src, self._out_matte_path)
                except Exception:
                    pass
                break

        self.set_state_id("setup_ui")
        self.setup_ui()

    def setup_ui(self):
        # Pybox grid: row 0..4, col 0..3. File browser is tall — keep its
        # column free of other widgets (otherwise UI vanishes / overlaps).
        # Default empty — Flame may restore this node's previously saved Job Path.
        job_path = pybox.create_text_field(
            UI_JOB_PATH, value=NO_JOB_LABEL, row=0, col=0, page=0, isField=True
        )
        job_name = pybox.create_text_field(
            UI_JOB_NAME, value="", row=1, col=0, page=0, isField=True
        )
        init_btn = pybox.create_toggle_button(UI_INIT, False, row=2, col=0, page=0)
        device = pybox.create_text_field(
            UI_DEVICE, value=DEFAULT_DEVICE, row=3, col=0, page=0, isField=True
        )

        repo_browser = pybox.create_file_browser(
            UI_REPO,
            DEFAULT_REPO,
            "",
            DEFAULT_REPO,
            row=0,
            col=1,
            page=0,
            isFileSelector=False,
        )

        record = pybox.create_toggle_button(UI_RECORD, False, row=0, col=2, page=0)
        guide = pybox.create_toggle_button(UI_GUIDE, False, row=1, col=2, page=0)
        run_btn = pybox.create_toggle_button(UI_RUN, False, row=2, col=2, page=0)
        status = pybox.create_toggle_button(UI_STATUS, False, row=3, col=2, page=0)
        # Default OFF: HUD spawns worker each miss and must not block Run.
        hud = pybox.create_toggle_button(UI_HUD, False, row=4, col=2, page=0)

        padding = pybox.create_float_numeric(
            UI_PADDING, value=4.0, min=1.0, max=8.0, row=0, col=3, page=0
        )
        offset = pybox.create_float_numeric(
            UI_OFFSET, value=0.0, min=-100000.0, max=100000.0, row=1, col=3, page=0
        )
        expected = pybox.create_float_numeric(
            UI_EXPECTED, value=0.0, min=0.0, max=100000.0, row=2, col=3, page=0
        )

        self.add_global_elements(
            job_path,
            job_name,
            init_btn,
            device,
            repo_browser,
            record,
            guide,
            run_btn,
            status,
            hud,
        )
        self.add_render_elements(padding, offset, expected)

        page = pybox.create_page("Embr Matte", "Job", "Repo", "Actions", "Frames")
        self.set_ui_pages(page)

        self.set_state_id("execute")
        self.execute()

    def execute(self):
        # UI first — never run HUD/playback before action toggles (HUD can take
        # seconds per frame and previously starved Run Matte).
        try:
            self._normalize_job_path_ui()
            gate = self._gate()

            # Momentary actions: same pattern as Record (value), not get_ui_changes.
            if self._toggle_on(self.get_global_element_value(UI_INIT)):
                self.set_global_element_value(UI_INIT, False)
                self._action_log("Init Job")
                self._init_job()
                self._normalize_job_path_ui()
                gate = self._gate()

            if self._toggle_on(self.get_global_element_value(UI_RECORD)):
                if gate["allow_record"]:
                    self._record_front()
                else:
                    self.set_global_element_value(UI_RECORD, False)
                    self.set_warning_msg(
                        "Embr Matte: Record disabled — {0}".format(gate["hint"])
                    )

            if self._toggle_on(self.get_global_element_value(UI_GUIDE)):
                self.set_global_element_value(UI_GUIDE, False)
                if gate["allow_guide"]:
                    self._action_log("Capture Guide")
                    self._capture_guide()
                else:
                    self._action_log("Capture Guide blocked: {0}".format(gate["hint"]))
                    self.set_warning_msg(
                        "Embr Matte: Capture Guide disabled — {0}".format(gate["hint"])
                    )

            if self._toggle_on(self.get_global_element_value(UI_RUN)):
                self.set_global_element_value(UI_RUN, False)
                if gate["allow_run"]:
                    self._action_log(
                        "Run Matte (inputs={0}, mask={1})".format(
                            gate["n_input"], gate["has_mask"]
                        )
                    )
                    self._start_run()
                else:
                    self._action_log("Run blocked: {0}".format(gate["hint"]))
                    self.set_warning_msg(
                        "Embr Matte: Run disabled — {0}".format(gate["hint"])
                    )
                gate = self._gate()

            force_status = self._toggle_on(self.get_global_element_value(UI_STATUS))
            if force_status:
                self.set_global_element_value(UI_STATUS, False)
                self._action_log("Refresh Status")

            if gate["running"] or force_status:
                self._refresh_status_notice(force=force_status)
            elif not self._toggle_on(self.get_global_element_value(UI_RECORD)):
                self.set_notice_msg("Embr Matte: {0}".format(gate["hint"]))

            self._playback_outputs()
        except Exception as exc:
            self._action_log("execute error: {0}".format(exc))
            self.set_error_msg("Embr Matte: execute error: {0}".format(exc))
            try:
                self._playback_outputs()
            except Exception:
                pass
    # --- Embr home / per-node job path ----------------------------------------

    def _embr_home(self):
        env = os.environ.get("EMBR_HOME", "").strip()
        if env:
            return os.path.expanduser(env)
        return DEFAULT_EMBR_HOME

    def _ml_root(self):
        env = os.environ.get("EMBR_ML_ROOT", "").strip()
        if env:
            return os.path.expanduser(env)
        # Prefer parent of jobs/ when Job Path is already under …/ml/jobs/…
        job = None
        try:
            raw = self.get_global_element_value(UI_JOB_PATH)
            text = os.path.expanduser(str(raw or "").strip())
            if text and text != NO_JOB_LABEL and os.path.isdir(text):
                job = os.path.normpath(text)
        except Exception:
            job = None
        if job:
            parts = job.split(os.sep)
            if "jobs" in parts:
                idx = parts.index("jobs")
                if idx > 0:
                    return os.sep.join(parts[:idx]) or DEFAULT_ML_ROOT
        return os.path.join(self._embr_home(), "ml")

    def _embr_bin(self):
        return os.path.join(self._embr_home(), "bin")

    def _embr_uv(self):
        env = os.environ.get("EMBR_UV", "").strip()
        if env:
            return os.path.expanduser(env)
        return os.path.join(self._embr_bin(), "uv")

    def _jobs_root(self):
        return os.path.join(self._ml_root(), "jobs")

    def _worker_env(self):
        """Env for worker subprocesses — Embr-local paths, no reliance on ~/.local."""
        env = os.environ.copy()
        home = self._embr_home()
        ml = self._ml_root()
        embr_bin = self._embr_bin()
        env["EMBR_HOME"] = home
        env["EMBR_ML_ROOT"] = ml
        env["EMBR_UV"] = self._embr_uv()
        env["HF_HOME"] = os.path.join(ml, "models", "hf")
        env["PATH"] = embr_bin + os.pathsep + env.get("PATH", "")
        return env

    def _job_dir(self):
        """Job folder for THIS Pybox node (from Job Path UI, persisted by Flame)."""
        raw = self.get_global_element_value(UI_JOB_PATH)
        if raw is None:
            return None
        text = os.path.expanduser(str(raw).strip())
        if not text or text == NO_JOB_LABEL:
            return None
        if text.startswith("/var/examples"):
            return None
        job = os.path.normpath(text)
        base = os.path.basename(job).lower()
        if base in ("alpha", "fgr", "input", "out"):
            job = os.path.dirname(job)
        if os.path.isdir(job):
            return job
        return None

    def _normalize_job_path_ui(self):
        """Keep label clean; never overwrite a valid per-node path from elsewhere."""
        job = self._job_dir()
        try:
            if job:
                self.set_global_element_value(UI_JOB_PATH, job)
            else:
                raw = str(self.get_global_element_value(UI_JOB_PATH) or "").strip()
                if not raw or raw == NO_JOB_LABEL or not os.path.isdir(
                    os.path.expanduser(raw)
                ):
                    self.set_global_element_value(UI_JOB_PATH, NO_JOB_LABEL)
        except Exception:
            pass

    def _set_node_job(self, job):
        try:
            self.set_global_element_value(UI_JOB_PATH, job)
        except Exception:
            pass

    # --- gate ------------------------------------------------------------------

    def _count_input_frames(self, job):
        input_dir = os.path.join(job, INPUT_SUBDIR)
        if not os.path.isdir(input_dir):
            return 0
        return len(
            [
                f
                for f in os.listdir(input_dir)
                if f.lower().endswith((".exr", ".png", ".jpg", ".jpeg"))
            ]
        )

    def _has_mask(self, job):
        return os.path.isfile(os.path.join(job, "mask.exr")) or os.path.isfile(
            os.path.join(job, "mask.png")
        )

    def _gate(self):
        job = self._job_dir()
        running = bool(self._running_pid()) if job else False
        n_input = self._count_input_frames(job) if job else 0
        has_mask = self._has_mask(job) if job else False

        if not job:
            hint = "next: Init Job (optional Job Name)"
            return {
                "has_job": False,
                "n_input": 0,
                "has_mask": False,
                "running": False,
                "allow_record": False,
                "allow_guide": False,
                "allow_run": False,
                "hint": hint,
            }

        if running:
            hint = "running — Refresh Status / scrub for progress"
            allow_record = False
            allow_guide = False
            allow_run = False
        elif n_input < 1:
            hint = "next: Record Front ON → Play/scrub ({0})".format(job)
            allow_record = True
            allow_guide = False
            allow_run = False
        elif not has_mask:
            hint = "next: Capture Guide Matte on first recorded frame ({0} inputs)".format(
                n_input
            )
            allow_record = True
            allow_guide = True
            allow_run = False
        else:
            hint = "next: Run Matte ({0} inputs, mask OK)".format(n_input)
            allow_record = True
            allow_guide = True
            allow_run = True

        return {
            "has_job": True,
            "n_input": n_input,
            "has_mask": has_mask,
            "running": running,
            "allow_record": allow_record,
            "allow_guide": allow_guide,
            "allow_run": allow_run,
            "hint": hint,
        }

    # --- paths / helpers -------------------------------------------------------

    def _repo_root(self):
        value = self.get_global_element_value(UI_REPO)
        # File browser may return str or a one-element sequence.
        if isinstance(value, (list, tuple)) and value:
            value = value[0]
        path = os.path.expanduser(str(value or "").strip())
        if path.endswith(os.sep + "worker") or path.endswith("/worker"):
            path = os.path.dirname(path)
        return path or DEFAULT_REPO

    def _device(self):
        value = self.get_global_element_value(UI_DEVICE)
        text = str(value or "").strip()
        return text or DEFAULT_DEVICE

    def _worker_python(self):
        return os.path.join(self._repo_root(), "worker", ".venv", "bin", "python")

    def _check_worker_media(self, python):
        """Return error snippet if numpy/Pillow/OpenEXR missing, else None."""
        try:
            proc = subprocess.run(
                [
                    python,
                    "-c",
                    "import numpy, PIL, OpenEXR",
                ],
                env=self._worker_env(),
                cwd=os.path.join(self._repo_root(), "worker"),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                timeout=30,
            )
        except Exception as exc:
            return str(exc)
        if proc.returncode != 0:
            text = (proc.stdout or "").strip().splitlines()
            return text[-1] if text else "import failed"
        return None

    def _action_log(self, message):
        """Append diagnostics even when Flame Message Console is ignored."""
        job = self._job_dir()
        if not job:
            return
        path = os.path.join(job, "handler_actions.log")
        try:
            with open(path, "a") as fh:
                fh.write(
                    "{0} {1}\n".format(
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"), message
                    )
                )
        except Exception:
            pass

    def _frame_pad(self):
        pad = int(round(float(self.get_render_element_value(UI_PADDING) or 4)))
        return max(1, min(pad, 8))

    def _batch_frame(self):
        offset = int(round(float(self.get_render_element_value(UI_OFFSET) or 0)))
        return int(self.get_frame()) + offset

    def _frame_name(self):
        return "{frame:0{pad}d}.exr".format(frame=self._batch_frame(), pad=self._frame_pad())

    def _input_frame_path(self):
        job = self._job_dir()
        if not job:
            return None
        return os.path.join(job, INPUT_SUBDIR, self._frame_name())

    def _alpha_path(self):
        job = self._job_dir()
        if not job:
            return None
        return os.path.join(job, ALPHA_SUBDIR, self._frame_name())

    def _fgr_path(self):
        job = self._job_dir()
        if not job:
            return None
        return os.path.join(job, FGR_SUBDIR, self._frame_name())

    def _status_path(self):
        job = self._job_dir()
        if not job:
            return None
        return os.path.join(job, STATUS_NAME)

    def _pid_path(self):
        job = self._job_dir()
        if not job:
            return None
        return os.path.join(job, PID_NAME)

    def _log_path(self):
        job = self._job_dir()
        if not job:
            return None
        return os.path.join(job, LOG_NAME)

    def _safe_copy(self, src, dst):
        if not src or not dst or not os.path.isfile(src):
            return False
        parent = os.path.dirname(dst)
        if parent:
            os.makedirs(parent, exist_ok=True)
        shutil.copy2(src, dst)
        return True

    def _safe_name(self, name):
        name = (name or "").strip().replace(" ", "_")
        if not name:
            return None
        if not re.fullmatch(r"[A-Za-z0-9._-]+", name):
            return None
        return name

    def _read_status(self):
        path = self._status_path()
        if not path or not os.path.isfile(path):
            return {}
        try:
            with open(path, "r") as fh:
                return json.load(fh)
        except Exception:
            return {"state": "error", "message": "status.json unreadable"}

    def _pid_alive(self, pid):
        if not pid or int(pid) <= 0:
            return False
        try:
            os.kill(int(pid), 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        except OSError:
            return False
        return True

    def _running_pid(self):
        path = self._pid_path()
        if path and os.path.isfile(path):
            try:
                with open(path, "r") as fh:
                    pid = int(fh.read().strip())
            except Exception:
                pid = None
            if pid and self._pid_alive(pid):
                return pid
        data = self._read_status()
        pid = data.get("pid")
        if data.get("state") == "running" and self._pid_alive(pid):
            return int(pid)
        return None

    def _format_status(self, data):
        if not data:
            return "Embr Matte: idle (no status.json)"
        state = data.get("state", "?")
        phase = data.get("phase", "")
        msg = data.get("message", "")
        cur = data.get("current")
        total = data.get("total")
        parts = ["Embr Matte: {0}".format(state)]
        if phase:
            parts.append(str(phase))
        if cur is not None and total:
            try:
                pct = int(100.0 * float(cur) / float(total)) if float(total) else 0
                parts.append("{0}/{1} ({2}%)".format(int(cur), int(total), pct))
            except Exception:
                parts.append("{0}/{1}".format(cur, total))
        elif cur is not None:
            parts.append(str(cur))
        if msg:
            parts.append(str(msg))
        return " · ".join(parts)

    # --- actions ---------------------------------------------------------------

    def _init_job(self):
        raw = self.get_global_element_value(UI_JOB_NAME)
        name = self._safe_name(str(raw or ""))
        if raw and str(raw).strip() and not name:
            self.set_error_msg(
                "Embr Matte: Job Name invalid (use letters, digits, . _ -)"
            )
            return

        explicit = bool(name)
        if not name:
            # Prefer clip-ish metadata so many clips get distinct folders.
            for getter in (
                "get_shot_name",
                "get_tape_name",
                "get_nickname",
                "get_node_name",
            ):
                try:
                    fn = getattr(self, getter, None)
                    if not fn:
                        continue
                    cand = self._safe_name(str(fn() or ""))
                    if cand and cand.lower() not in ("pybox", "batch", "none"):
                        name = cand
                        break
                except Exception:
                    continue
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # Always append stamp when auto-naming so re-Init on another clip
            # never silently reuses a previous job.
            name = "{0}_{1}".format(name, stamp) if name else "job_{0}".format(stamp)

        jobs_root = self._jobs_root()
        job = os.path.join(jobs_root, name)

        if explicit and os.path.isdir(job) and self._count_input_frames(job) > 0:
            # Explicit name + existing content → attach THIS node to that job.
            self._set_node_job(job)
            self.set_global_element_value(UI_JOB_NAME, "")
            self.set_notice_msg(
                "Embr Matte: this node → existing job {0}".format(job)
            )
            return

        try:
            for sub in (INPUT_SUBDIR, "out", ALPHA_SUBDIR, FGR_SUBDIR):
                os.makedirs(os.path.join(job, sub), exist_ok=True)
            self._set_node_job(job)
            self.set_global_element_value(UI_JOB_NAME, "")
            self.set_notice_msg(
                "Embr Matte: Init OK → {0} · next: Record Front ON → Play/scrub".format(
                    job
                )
            )
        except Exception as exc:
            self.set_error_msg("Embr Matte: Init failed: {0}".format(exc))

    def _record_front(self):
        src = self.get_in_socket_path(0)
        dst = self._input_frame_path()
        if not dst:
            self.set_warning_msg("Embr Matte: no job — Init first")
            return
        if not src or not os.path.isfile(src):
            self.set_warning_msg("Embr Matte: Front missing; cannot Record")
            return
        try:
            self._safe_copy(src, dst)
            self.set_notice_msg("Embr Matte: recorded Front → {0}".format(dst))
        except Exception as exc:
            self.set_error_msg("Embr Matte: Record failed: {0}".format(exc))

    def _capture_guide(self):
        src = self.get_in_socket_path(2)
        job = self._job_dir()
        if not job:
            self.set_error_msg("Embr Matte: no job — Init first")
            return
        dst = os.path.join(job, "mask.exr")
        if not src or not os.path.isfile(src):
            self.set_error_msg(
                "Embr Matte: Matte missing. Connect guide matte, show guide frame, Capture Guide."
            )
            return
        try:
            os.makedirs(job, exist_ok=True)
            shutil.copy2(src, dst)
            meta = os.path.join(job, "guide_frame.txt")
            with open(meta, "w") as fh:
                fh.write(str(self._batch_frame()) + "\n")
            self.set_notice_msg(
                "Embr Matte: guide mask → {0} (batch frame {1})".format(
                    dst, self._batch_frame()
                )
            )
        except Exception as exc:
            self.set_error_msg("Embr Matte: Capture Guide failed: {0}".format(exc))

    def _start_run(self):
        job = self._job_dir()
        if not job:
            self._action_log("Run abort: no job")
            self.set_error_msg("Embr Matte: no job — Init first")
            return
        python = self._worker_python()
        if not os.path.isfile(python):
            tip = (
                "Embr Matte: worker python missing:\n{0}\n"
                "Install Embr runtime (uv + clone under ~/Embr/repos/…), "
                "then set Repo Root to that clone.".format(python)
            )
            self._action_log(tip.replace("\n", " "))
            self.set_error_msg(tip)
            return

        alive = self._running_pid()
        if alive:
            tip = "Embr Matte: already running (pid {0}). Refresh Status.".format(alive)
            self._action_log(tip)
            self.set_warning_msg(tip)
            return

        input_dir = os.path.join(job, INPUT_SUBDIR)
        os.makedirs(input_dir, exist_ok=True)
        os.makedirs(os.path.join(job, ALPHA_SUBDIR), exist_ok=True)
        os.makedirs(os.path.join(job, FGR_SUBDIR), exist_ok=True)

        n_input = self._count_input_frames(job)
        if n_input < 1:
            tip = "Embr Matte: no frames in input/. Turn on Record Front and Play/scrub."
            self._action_log(tip)
            self.set_error_msg(tip)
            return
        if not self._has_mask(job):
            tip = (
                "Embr Matte: missing mask. Capture Guide Matte on the first recorded frame."
            )
            self._action_log(tip)
            self.set_error_msg(tip)
            return

        media_err = self._check_worker_media(python)
        if media_err:
            tip = (
                "Embr Matte: worker media deps missing ({0}).\n"
                "On the Linux box run:\n"
                "  cd {1}/worker && uv pip install -e .\n"
                "HUD and Run both need numpy / Pillow / OpenEXR.".format(
                    media_err, self._repo_root()
                )
            )
            self._action_log(tip.replace("\n", " "))
            self.set_error_msg(tip)
            return

        env = self._worker_env()

        cmd = [
            python,
            "-m",
            "embr_ml.cli",
            "process-job",
            "--job-dir",
            job,
            "--device",
            self._device(),
            "--start-frame",
            "1",
            "--padding",
            str(self._frame_pad()),
        ]
        try:
            names = sorted(
                f
                for f in os.listdir(input_dir)
                if f.lower().endswith((".exr", ".png", ".jpg", ".jpeg"))
            )
            if names:
                stem = os.path.splitext(names[0])[0]
                cmd[cmd.index("--start-frame") + 1] = str(int(stem))
        except Exception:
            pass

        log_path = self._log_path()
        try:
            log_fh = open(log_path, "w")
        except Exception as exc:
            self.set_error_msg("Embr Matte: cannot open run.log: {0}".format(exc))
            return

        try:
            seed = {
                "state": "running",
                "phase": "starting",
                "current": 0,
                "total": n_input,
                "message": "spawning worker",
                "updated_at": time.time(),
            }
            with open(self._status_path(), "w") as fh:
                json.dump(seed, fh, indent=2)

            proc = subprocess.Popen(
                cmd,
                env=env,
                stdout=log_fh,
                stderr=subprocess.STDOUT,
                cwd=os.path.join(self._repo_root(), "worker"),
                start_new_session=True,
            )
            with open(self._pid_path(), "w") as fh:
                fh.write(str(proc.pid) + "\n")
        except Exception as exc:
            log_fh.close()
            self.set_error_msg("Embr Matte: failed to start: {0}".format(exc))
            return

        try:
            log_fh.close()
        except Exception:
            pass

        msg = (
            "Embr Matte: started pid={0} · {1} input frames · log={2}".format(
                proc.pid, n_input, log_path
            )
        )
        self._action_log(msg)
        self.set_notice_msg(msg)
        try:
            self.set_dialog_msg(msg)
        except Exception:
            pass

    def _refresh_status_notice(self, force=False):
        data = self._read_status()
        running = self._running_pid()
        if data.get("state") == "running" and not running:
            log_path = self._log_path()
            tail = ""
            if log_path and os.path.isfile(log_path):
                try:
                    with open(log_path, "r") as fh:
                        lines = fh.read().splitlines()
                    tail = " | ".join(lines[-4:]) if lines else ""
                except Exception:
                    tail = ""
            data["state"] = "error"
            data["phase"] = "error"
            data["message"] = tail or data.get("message") or "worker exited (see run.log)"
            path = self._status_path()
            if path:
                try:
                    with open(path, "w") as fh:
                        json.dump(data, fh, indent=2)
                except Exception:
                    pass
            pid_path = self._pid_path()
            if pid_path and os.path.isfile(pid_path):
                try:
                    os.remove(pid_path)
                except Exception:
                    pass
        elif running and data.get("state") != "running":
            data["state"] = "running"
            data["message"] = data.get("message") or "worker alive"
        if not data and not running and not force:
            return
        if not data and force:
            self.set_notice_msg("Embr Matte: idle (no status.json)")
            return
        self.set_notice_msg(self._format_status(data))
        if data.get("state") == "error":
            self.set_warning_msg("Embr Matte error: {0}".format(data.get("message", "")))

    def _guide_frame(self):
        job = self._job_dir()
        if not job:
            return None
        path = os.path.join(job, "guide_frame.txt")
        if not os.path.isfile(path):
            return None
        try:
            with open(path, "r") as fh:
                return int(fh.read().strip())
        except Exception:
            return None

    def _input_frame_stats(self):
        job = self._job_dir()
        if not job:
            return 0, None, None, False
        input_dir = os.path.join(job, INPUT_SUBDIR)
        if not os.path.isdir(input_dir):
            return 0, None, None, False
        frames = []
        for name in os.listdir(input_dir):
            low = name.lower()
            if not low.endswith((".exr", ".png", ".jpg", ".jpeg")):
                continue
            stem = os.path.splitext(name)[0]
            try:
                frames.append(int(stem))
            except Exception:
                continue
        if not frames:
            return 0, None, None, False
        cur = self._batch_frame()
        return len(frames), min(frames), max(frames), cur in frames

    def _expected_frames(self):
        try:
            return int(round(float(self.get_render_element_value(UI_EXPECTED) or 0)))
        except Exception:
            return 0

    def _hud_lines(self, gate):
        job = self._job_dir()
        n, fmin, fmax, cur_ok = self._input_frame_stats()
        expected = self._expected_frames()
        guide = self._guide_frame()
        batch = self._batch_frame()
        lines = []

        if not job:
            lines.append("Job: (none) — press Init Job")
            lines.append("Prep: not ready")
            return lines

        lines.append("Job: {0}".format(os.path.basename(job)))
        lines.append("Batch frame: {0}".format(batch))

        if expected > 0:
            lines.append("Record Front: {0}/{1}".format(n, expected))
        else:
            lines.append("Record Front: {0} frames".format(n))
        if fmin is not None:
            lines.append("Record range: {0}–{1}".format(fmin, fmax))
        lines.append("This frame recorded: {0}".format("yes" if cur_ok else "no"))

        if guide is not None:
            lines.append("Guide matte: frame {0}".format(guide))
        else:
            lines.append("Guide matte: (not captured)")

        if gate.get("allow_run"):
            lines.append("Prep: READY — Run Matte")
        else:
            lines.append("Prep: {0}".format(gate.get("hint", "not ready")))

        data = self._read_status()
        running = gate.get("running")
        if running or data.get("state") in ("running", "done", "error"):
            state = data.get("state", "running" if running else "?")
            phase = data.get("phase", "")
            cur = data.get("current")
            total = data.get("total")
            msg = data.get("message", "")
            if cur is not None and total:
                try:
                    pct = int(100.0 * float(cur) / float(total)) if float(total) else 0
                    lines.append(
                        "Run: {0} {1} {2}/{3} ({4}%)".format(
                            state, phase, int(cur), int(total), pct
                        )
                    )
                except Exception:
                    lines.append("Run: {0} {1}".format(state, phase))
            else:
                lines.append("Run: {0} {1}".format(state, phase))
            if msg:
                lines.append("  {0}".format(msg)[:72])
        else:
            lines.append("Run: idle")

        return lines

    def _toggle_on(self, value):
        """Pybox may return True/False, 1/0, or strings."""
        if value is True or value is False:
            return value
        if value is None:
            return False
        if isinstance(value, (int, float)):
            return value != 0
        text = str(value).strip().lower()
        return text in ("1", "true", "on", "yes")

    def _apply_hud(self, base_src, out_result, gate):
        """Composite status panel onto Result via worker (Flame Python lacks PIL).

        Caches per batch frame so scrubbing does not re-spawn PIL/OpenEXR every time.
        """
        if not base_src or not os.path.isfile(base_src):
            return False
        python = self._worker_python()
        if not os.path.isfile(python):
            tip = (
                "Embr Matte: HUD needs worker venv:\n{0}\n"
                "Install Embr runtime (python-scripts), set Repo Root.".format(python)
            )
            self._action_log(tip.replace("\n", " "))
            self.set_warning_msg(tip)
            return self._safe_copy(base_src, out_result)

        job = self._job_dir()
        lines = self._hud_lines(gate)
        try:
            base_mtime = os.path.getmtime(base_src)
        except Exception:
            base_mtime = 0.0
        cache_key = "{0}|{1}|{2}".format(
            base_src, base_mtime, "\n".join(lines)
        )

        cache_dir = None
        cache_exr = None
        cache_key_path = None
        if job:
            cache_dir = os.path.join(job, ".hud")
            frame = self._batch_frame()
            cache_exr = os.path.join(cache_dir, "{0}.exr".format(frame))
            cache_key_path = os.path.join(cache_dir, "{0}.key".format(frame))
            try:
                if (
                    cache_exr
                    and os.path.isfile(cache_exr)
                    and cache_key_path
                    and os.path.isfile(cache_key_path)
                ):
                    with open(cache_key_path, "r") as fh:
                        prev = fh.read()
                    if prev == cache_key:
                        return self._safe_copy(cache_exr, out_result)
            except Exception:
                pass

        info_path = os.path.join(job if job else tempfile.gettempdir(), HUD_JSON)
        try:
            payload = {"title": "Embr Matte", "lines": lines}
            parent = os.path.dirname(info_path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(info_path, "w") as fh:
                json.dump(payload, fh)
        except Exception as exc:
            self.set_warning_msg("Embr Matte: HUD info write failed: {0}".format(exc))
            return self._safe_copy(base_src, out_result)

        render_out = cache_exr or out_result
        if cache_dir:
            try:
                os.makedirs(cache_dir, exist_ok=True)
            except Exception:
                render_out = out_result

        # Direct module — avoids pulling ensure_models via embr_ml.cli import side paths.
        cmd = [
            python,
            "-m",
            "embr_ml.hud_overlay",
            "--base",
            base_src,
            "--out",
            render_out,
            "--info-json",
            info_path,
        ]
        try:
            proc = subprocess.run(
                cmd,
                env=self._worker_env(),
                cwd=os.path.join(self._repo_root(), "worker"),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                timeout=12,
            )
        except Exception as exc:
            self._action_log("HUD failed: {0}".format(exc))
            self.set_warning_msg("Embr Matte: HUD failed to start: {0}".format(exc))
            return self._safe_copy(base_src, out_result)

        if proc.returncode != 0 or not os.path.isfile(render_out):
            tail = (proc.stdout or "").strip().splitlines()
            tip = " | ".join(tail[-3:]) if tail else "no output"
            self._action_log("HUD exit {0}: {1}".format(proc.returncode, tip))
            self.set_warning_msg(
                "Embr Matte: HUD exit {0}: {1}".format(proc.returncode, tip)
            )
            return self._safe_copy(base_src, out_result)

        if cache_key_path and render_out == cache_exr:
            try:
                with open(cache_key_path, "w") as fh:
                    fh.write(cache_key)
            except Exception:
                pass
            return self._safe_copy(cache_exr, out_result)
        return True

    def _playback_outputs(self):
        out_result = self.get_out_socket_path(0)
        out_matte = self.get_out_socket_path(1)
        front = self.get_in_socket_path(0)
        matte = self.get_in_socket_path(2)
        gate = self._gate()
        show_hud = self._toggle_on(self.get_global_element_value(UI_HUD))

        fgr = self._fgr_path()
        base = None
        if fgr and os.path.isfile(fgr):
            base = fgr
        elif front and os.path.isfile(front):
            base = front

        if base:
            if show_hud:
                self._apply_hud(base, out_result, gate)
            else:
                self._safe_copy(base, out_result)

        alpha = self._alpha_path()
        if alpha and os.path.isfile(alpha):
            self._safe_copy(alpha, out_matte)
            return

        for src in (matte, front):
            if self._safe_copy(src, out_matte):
                if self._running_pid():
                    self.set_warning_msg(
                        "Embr Matte: alpha not ready yet ({0})".format(alpha)
                    )
                elif alpha:
                    self.set_warning_msg(
                        "Embr Matte: missing {0} (fallback Matte/Front)".format(alpha)
                    )
                return

        self.set_error_msg("Embr Matte: could not write OutMatte")

    def teardown(self):
        pass


def _main(argv):
    p = EmbrMatte(argv[0])
    p.dispatch()
    p.write_to_disk(argv[0])


if __name__ == "__main__":
    _main(sys.argv[1:])
