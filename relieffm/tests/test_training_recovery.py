from __future__ import annotations

import json
from datetime import datetime, timezone

import torch
from accelerate import Accelerator

from ml.training.train_mini import _read_resume_state, _save_recovery_checkpoint


def test_recovery_checkpoint_contains_reloadable_full_state(tmp_path):
    accelerator = Accelerator()
    model = torch.nn.Linear(3, 2)
    optimizer = torch.optim.AdamW(model.parameters())
    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lambda _: 1.0)
    model, optimizer, scheduler = accelerator.prepare(model, optimizer, scheduler)

    _save_recovery_checkpoint(
        accelerator=accelerator,
        out_dir=tmp_path,
        epoch=2,
        batch_in_epoch=17,
        global_step=41,
        skipped_nonfinite=0,
        as_of=datetime(2026, 7, 25, tzinfo=timezone.utc),
        best_val=0.42,
        best_step=40,
    )

    recovery = tmp_path / "recovery"
    state = _read_resume_state(str(recovery))
    assert state["epoch"] == 2
    assert state["batch_in_epoch"] == 17
    assert state["global_step"] == 41
    assert state["best_val"] == 0.42
    assert state["best_step"] == 40
    assert any(path.name.startswith("model") for path in recovery.iterdir())
    assert any(path.name.startswith("optimizer") for path in recovery.iterdir())
    assert json.loads((recovery / "resume_state.json").read_text()) == state

    accelerator.load_state(str(recovery))
    accelerator.end_training()
