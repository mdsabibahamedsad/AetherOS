import sys


def test_top_level_skills_flag_defaults_to_chat(monkeypatch):
    import aetheros_cli.main as main_mod

    captured = {}

    def fake_cmd_chat(args):
        captured["skills"] = args.skills
        captured["command"] = args.command

    monkeypatch.setattr(main_mod, "cmd_chat", fake_cmd_chat)
    monkeypatch.setattr(
        sys,
        "argv",
        ["aetheros", "-s", "aetheros-dev,github-auth"],
    )

    main_mod.main()

    assert captured == {
        "skills": ["aetheros-dev,github-auth"],
        "command": None,
    }


def test_chat_subcommand_accepts_skills_flag(monkeypatch):
    import aetheros_cli.main as main_mod

    captured = {}

    def fake_cmd_chat(args):
        captured["skills"] = args.skills
        captured["query"] = args.query

    monkeypatch.setattr(main_mod, "cmd_chat", fake_cmd_chat)
    monkeypatch.setattr(
        sys,
        "argv",
        ["aetheros", "chat", "-s", "github-auth", "-q", "hello"],
    )

    main_mod.main()

    assert captured == {
        "skills": ["github-auth"],
        "query": "hello",
    }


def test_chat_subcommand_accepts_image_flag(monkeypatch):
    import aetheros_cli.main as main_mod

    captured = {}

    def fake_cmd_chat(args):
        captured["query"] = args.query
        captured["image"] = args.image

    monkeypatch.setattr(main_mod, "cmd_chat", fake_cmd_chat)
    monkeypatch.setattr(
        sys,
        "argv",
        ["aetheros", "chat", "-q", "hello", "--image", "~/storage/shared/Pictures/cat.png"],
    )

    main_mod.main()

    assert captured == {
        "query": "hello",
        "image": "~/storage/shared/Pictures/cat.png",
    }


def test_continue_worktree_and_skills_flags_work_together(monkeypatch):
    import aetheros_cli.main as main_mod

    captured = {}

    def fake_cmd_chat(args):
        captured["continue_last"] = args.continue_last
        captured["worktree"] = args.worktree
        captured["skills"] = args.skills
        captured["command"] = args.command

    monkeypatch.setattr(main_mod, "cmd_chat", fake_cmd_chat)
    monkeypatch.setattr(
        sys,
        "argv",
        ["aetheros", "-c", "-w", "-s", "aetheros-dev"],
    )

    main_mod.main()

    assert captured == {
        "continue_last": True,
        "worktree": True,
        "skills": ["aetheros-dev"],
        "command": "chat",
    }
