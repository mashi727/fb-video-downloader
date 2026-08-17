"""Tests for the fbdl-rename maintenance tool"""

import json

import pytest

from fb_downloader.tools.rename import (
    apply_moves,
    build_plans,
    load_plan,
    main,
    save_plan,
)
from fb_downloader.utils.filename import FileNameGenerator


BODY_SALAD = "レシピを発信しています\n\n『焼きシーザーサラダ🥬』\n\n⚪︎材料\n・レタス"
BODY_SOUP = "毎日のスープ\n\n【鶏塩キャベツスープ】\n\n⚪︎材料\n・鶏むね肉"


@pytest.fixture(autouse=True)
def offline():
    """Keep the tests deterministic and free of subprocess calls"""
    original = FileNameGenerator.USE_CLAUDE
    FileNameGenerator.USE_CLAUDE = False
    yield
    FileNameGenerator.USE_CLAUDE = original


def _make_video(directory, stem, body, extras=()):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{stem}.mp4").write_bytes(b"video")
    (directory / f"{stem}.txt").write_text(body, encoding="utf-8")
    for suffix in extras:
        (directory / f"{stem}{suffix}").write_text("extra", encoding="utf-8")


class TestBuildPlans:
    def test_keeps_the_original_download_date(self, tmp_path):
        _make_video(tmp_path, "20260817_しんちゃん夫婦_の動画", BODY_SALAD)

        plans, _ = build_plans([tmp_path])

        assert len(plans) == 1
        assert plans[0].new_stem == "20260817_焼きシーザーサラダ🥬"

    def test_renames_companions_with_the_video(self, tmp_path):
        _make_video(tmp_path, "20260817_x_の動画", BODY_SALAD, extras=("_yt.srt",))

        plans, _ = build_plans([tmp_path])
        destinations = sorted(dest.name for _, dest in plans[0].targets())

        assert destinations == [
            "20260817_焼きシーザーサラダ🥬.mp4",
            "20260817_焼きシーザーサラダ🥬.txt",
            "20260817_焼きシーザーサラダ🥬_yt.srt",
        ]

    def test_descends_into_subdirectories(self, tmp_path):
        _make_video(tmp_path / "a" / "b", "20260817_x_の動画", BODY_SALAD)

        plans, _ = build_plans([tmp_path])

        assert len(plans) == 1

    def test_no_recursion_when_disabled(self, tmp_path):
        _make_video(tmp_path / "a", "20260817_x_の動画", BODY_SALAD)

        plans, _ = build_plans([tmp_path], recursive=False)

        assert plans == []

    def test_undated_files_are_left_alone(self, tmp_path):
        _make_video(tmp_path, "05_雨にキッスの花束を", BODY_SALAD)

        plans, _ = build_plans([tmp_path])

        assert plans == []

    def test_undated_files_included_with_dated_only_off(self, tmp_path):
        _make_video(tmp_path, "05_雨にキッスの花束を", BODY_SALAD)

        plans, _ = build_plans([tmp_path], dated_only=False)

        assert len(plans) == 1

    def test_video_without_description_is_reported(self, tmp_path):
        (tmp_path / "20260817_x.mp4").write_bytes(b"video")

        plans, skipped = build_plans([tmp_path])

        assert plans == []
        assert [p.name for p in skipped] == ["20260817_x.mp4"]

    def test_same_name_gets_a_suffix_instead_of_overwriting(self, tmp_path):
        _make_video(tmp_path, "20260817_a_の動画", BODY_SOUP)
        _make_video(tmp_path, "20260817_b_の動画", BODY_SOUP)

        plans, _ = build_plans([tmp_path])
        new_stems = sorted(plan.new_stem for plan in plans)

        assert new_stems == ["20260817_鶏塩キャベツスープ", "20260817_鶏塩キャベツスープ_2"]


class TestApply:
    def test_rename_and_undo_round_trip(self, tmp_path):
        _make_video(tmp_path, "20260817_しんちゃん夫婦_の動画", BODY_SALAD)
        plan_file = tmp_path / "undo.json"

        plans, _ = build_plans([tmp_path])
        save_plan(plans, plan_file)
        done, failed = apply_moves([m for plan in plans for m in plan.targets()])

        assert (done, failed) == (2, 0)
        assert (tmp_path / "20260817_焼きシーザーサラダ🥬.mp4").exists()

        reverse = [(dst, src) for src, dst in load_plan(plan_file)]
        apply_moves(reverse)

        assert (tmp_path / "20260817_しんちゃん夫婦_の動画.mp4").exists()

    def test_existing_target_is_not_overwritten(self, tmp_path):
        _make_video(tmp_path, "20260817_a_の動画", BODY_SALAD)
        occupied = tmp_path / "20260817_焼きシーザーサラダ🥬.mp4"
        occupied.write_bytes(b"do not lose me")

        done, failed = apply_moves([(tmp_path / "20260817_a_の動画.mp4", occupied)])

        assert (done, failed) == (0, 1)
        assert occupied.read_bytes() == b"do not lose me"


class TestCli:
    def test_dry_run_changes_nothing(self, tmp_path):
        _make_video(tmp_path, "20260817_x_の動画", BODY_SALAD)

        assert main([str(tmp_path), "-n", "--no-claude"]) == 0
        assert (tmp_path / "20260817_x_の動画.mp4").exists()

    def test_default_run_renames_and_writes_undo_log(self, tmp_path):
        _make_video(tmp_path, "20260817_x_の動画", BODY_SALAD)
        plan_file = tmp_path / "undo.json"

        assert main([str(tmp_path), "--no-claude", "--plan", str(plan_file)]) == 0
        assert (tmp_path / "20260817_焼きシーザーサラダ🥬.mp4").exists()
        assert len(json.loads(plan_file.read_text(encoding="utf-8"))) == 2

        assert main(["--undo", str(plan_file)]) == 0
        assert (tmp_path / "20260817_x_の動画.mp4").exists()
