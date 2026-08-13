################################################################################
## Embr ML Worker — thin Pybox front-end for company-style setup + downloads
##
## Does NOT import torch. Spawns subprocesses only.
##
## Company flow (after git clone of this repo):
##   1. Point handler at handlers/embr_ml_worker.py
##   2. Set Repo Root to the clone path
##   3. Press "Run Setup"  →  uv + venv + pip install -e . + ensure-models
##
## "Ensure Models" / "Worker Status" need Setup to have succeeded once.
################################################################################

import os
import shutil
import subprocess
import sys
import tempfile

import pybox_v1 as pybox

UI_REPO = "Repo Root"
UI_ML_ROOT = "EMBR_ML_ROOT"
UI_SETUP = "Run Setup"
UI_ENSURE = "Ensure Models"
UI_STATUS = "Worker Status"
UI_FORCE = "Force Re-download"

# Absolute defaults only (Flame copies this handler to /var/tmp).
_DEFAULT_ML_ROOT = os.path.expanduser("~/Embr/ml")
_DEFAULT_REPO = os.path.expanduser("~/Embr/repos/embr-pybox-handlers")
if not os.path.isdir(_DEFAULT_REPO):
    _legacy = "/Users/oue.isamu/Projects/embr-pybox-handlers"
    if os.path.isdir(_legacy):
        _DEFAULT_REPO = _legacy


class EmbrMlWorker(pybox.BaseClass):
    def initialize(self):
        self.set_img_format("exr")
        fmt = self.get_img_format()
        tmp = tempfile.gettempdir()

        front = tmp + "/embr_ml_in_front." + fmt
        matte = tmp + "/embr_ml_in_matte." + fmt
        out_matte = tmp + "/embr_ml_out_matte." + fmt

        self.set_in_socket(0, "Front", front)
        self.set_in_socket(2, "Matte", matte)
        self.set_out_socket(0, "Result", front)
        self.set_out_socket(1, "OutMatte", out_matte)

        for src in (matte, front):
            if os.path.isfile(src):
                try:
                    shutil.copy2(src, out_matte)
                except Exception:
                    pass
                break

        self.set_state_id("setup_ui")
        self.setup_ui()

    def setup_ui(self):
        repo = pybox.create_file_browser(
            UI_REPO,
            _DEFAULT_REPO,
            "",
            _DEFAULT_REPO,
            row=0,
            col=0,
            isFileSelector=False,
        )
        ml_root = pybox.create_text_field(
            UI_ML_ROOT, value=_DEFAULT_ML_ROOT, row=1, col=0, isField=True
        )
        setup = pybox.create_toggle_button(UI_SETUP, False, row=0, col=1)
        ensure = pybox.create_toggle_button(UI_ENSURE, False, row=1, col=1)
        status = pybox.create_toggle_button(UI_STATUS, False, row=2, col=1)
        force = pybox.create_toggle_button(UI_FORCE, False, row=3, col=1)

        self.add_global_elements(repo, ml_root, setup, ensure, status, force)
        page = pybox.create_page("Embr ML", "Paths", "Actions")
        self.set_ui_pages(page)

        self.set_state_id("execute")
        self.execute()

    def execute(self):
        changes = {el.get("name") for el in self.get_ui_changes()}
        self._passthrough_matte()

        if UI_SETUP in changes:
            self._run_setup()
            self.set_global_element_value(UI_SETUP, False)

        if UI_STATUS in changes:
            self._run_worker(["status"])
            self.set_global_element_value(UI_STATUS, False)

        if UI_ENSURE in changes:
            cmd = ["ensure-models"]
            if self.get_global_element_value(UI_FORCE):
                cmd.append("--force")
                self.set_global_element_value(UI_FORCE, False)
            self._run_worker(cmd)
            self.set_global_element_value(UI_ENSURE, False)

    def _passthrough_matte(self):
        out_matte = self.get_out_socket_path(1)
        for src in (self.get_in_socket_path(2), self.get_in_socket_path(0)):
            if src and os.path.isfile(src):
                try:
                    shutil.copy2(src, out_matte)
                except Exception:
                    pass
                return

    def _repo_root(self):
        value = self.get_global_element_value(UI_REPO)
        path = os.path.expanduser(str(value or "").strip())
        return path or _DEFAULT_REPO

    def _ml_root(self):
        value = self.get_global_element_value(UI_ML_ROOT)
        path = os.path.expanduser(str(value or "").strip())
        return path or _DEFAULT_ML_ROOT

    def _worker_python(self):
        root = self._repo_root()
        return os.path.join(root, "worker", ".venv", "bin", "python")

    def _run_setup(self):
        """
        Uses Flame's python (sys.executable) only to launch bootstrap.py from the
        repo on disk. Bootstrap then installs uv + venv under Repo Root/worker.
        """
        repo = self._repo_root()
        bootstrap = os.path.join(repo, "worker", "embr_ml", "bootstrap.py")
        if not os.path.isfile(bootstrap):
            self.set_error_msg(
                "Embr ML: bootstrap not found: {0}\n"
                "Clone embr-pybox-handlers and set Repo Root to that clone.".format(
                    bootstrap
                )
            )
            return

        cmd = [
            sys.executable,
            bootstrap,
            "--repo-root",
            repo,
            "--ml-root",
            self._ml_root(),
        ]
        if self.get_global_element_value(UI_FORCE):
            cmd.append("--force-models")
            self.set_global_element_value(UI_FORCE, False)

        self.set_notice_msg(
            "Embr ML: Run Setup started (uv/venv/weights). Flame may wait several minutes…"
        )
        try:
            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                timeout=None,
            )
        except Exception as exc:
            self.set_error_msg("Embr ML: Setup failed to start: {0}".format(exc))
            return

        text = (proc.stdout or "").strip()
        tail = "\n".join(text.splitlines()[-20:]) if text else "(no output)"
        if proc.returncode != 0:
            self.set_error_msg("Embr ML: Setup exit {0}\n{1}".format(proc.returncode, tail))
            return

        py = self._worker_python()
        if not os.path.isfile(py):
            self.set_error_msg(
                "Embr ML: Setup reported OK but venv python missing:\n{0}\n{1}".format(
                    py, tail
                )
            )
            return
        self.set_notice_msg("Embr ML: Setup OK\nworker_python={0}\n{1}".format(py, tail))

    def _run_worker(self, args):
        python = self._worker_python()
        if not os.path.isfile(python):
            self.set_error_msg(
                "Embr ML: Worker Python not found:\n{0}\n"
                "Press Run Setup once (Repo Root must point at the git clone).".format(
                    python
                )
            )
            return

        env = os.environ.copy()
        ml = self._ml_root()
        embr_home = os.environ.get("EMBR_HOME", "").strip() or os.path.expanduser("~/Embr")
        embr_bin = os.path.join(embr_home, "bin")
        env["EMBR_HOME"] = embr_home
        env["EMBR_ML_ROOT"] = ml
        env["EMBR_UV"] = os.path.join(embr_bin, "uv")
        env["HF_HOME"] = os.path.join(ml, "models", "hf")
        env["PATH"] = embr_bin + os.pathsep + env.get("PATH", "")

        cmd = [python, "-m", "embr_ml.cli"] + list(args)
        self.set_notice_msg("Embr ML: running {0}".format(" ".join(args)))
        try:
            proc = subprocess.run(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                timeout=None,
            )
        except Exception as exc:
            self.set_error_msg("Embr ML: worker failed to start: {0}".format(exc))
            return

        text = (proc.stdout or "").strip()
        tail = "\n".join(text.splitlines()[-12:]) if text else "(no output)"
        if proc.returncode != 0:
            self.set_error_msg("Embr ML: exit {0}\n{1}".format(proc.returncode, tail))
            return
        self.set_notice_msg("Embr ML: ok\n{0}".format(tail))

    def teardown(self):
        pass


def _main(argv):
    p = EmbrMlWorker(argv[0])
    p.dispatch()
    p.write_to_disk(argv[0])


if __name__ == "__main__":
    _main(sys.argv[1:])
