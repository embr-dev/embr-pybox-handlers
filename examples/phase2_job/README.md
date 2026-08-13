# Phase 2 example job (optional)

Default Job Folder for the handler is **`/tmp/embr_cache_job`** (not this folder).

Flame runs handlers from `/var/tmp`, so paths derived from the script file break.
Use an absolute directory in the Pybox UI.

Optional: point Job Folder here instead:

```text
…/embr-pybox-handlers/examples/phase2_job/alpha/{frame}.exr
```
