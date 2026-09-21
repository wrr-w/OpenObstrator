"""NanoGhost 实例的技能白名单。

守的是这个契约：控制台写下去的那把钥匙，必须是 NanoGhost 真正读的那把。

NanoGhost 侧读 `skills.enabled_only`（`src/agent_core/skill/registry.py::_enabled_only`），
**空/缺失 = 一个技能都不给**，和 `mcp.enabled_only` 同语义。
控制台这边曾经写的是 Hermes 那套 `skills.disabled` 黑名单 —— 键名不同、极性相反，
于是面板里每个技能都显示勾选着，而 agent 实到一个都看不见，且没有任何报错。
这两条用例就是钉住"再也别飘回去"。
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from fastapi.testclient import TestClient

import server.app as app_mod


def _mk_skill(d: Path, name: str) -> None:
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {name} 的说明\n---\nbody\n", encoding="utf-8",
    )


def _client(tmp_path: Path, monkeypatch, *, inst_cfg: str, shared: list[str]):
    """搭一个只有 tmp 的世界：实例目录、共享技能目录、管理器配置，全在 tmp_path 里。

    `shared_skills_root` 必须显式指到 tmp —— 默认值是 `~/.agents/skills`，那是**真机**
    的目录，读它会让断言随本机上装了什么技能而变化。
    """
    ng_root = tmp_path / "nanoghost"
    inst = ng_root / "instances" / "demo1"
    inst.mkdir(parents=True, exist_ok=True)
    (inst / "config.yaml").write_text(inst_cfg, encoding="utf-8")

    shared_dir = tmp_path / "shared-skills"
    for name in shared:
        _mk_skill(shared_dir / name, name)

    cfg = tmp_path / "manager_config.yaml"
    cfg.write_text(
        f"nanoghost_root: {ng_root}\nshared_skills_root: {shared_dir}\n", encoding="utf-8",
    )
    monkeypatch.setattr(app_mod, "CONFIG_PATH", cfg)
    return TestClient(app_mod.app), inst, shared_dir


def _items(client: TestClient) -> dict[str, dict]:
    r = client.get("/api/runtimes/nanoghost/instances/demo1/skills")
    assert r.status_code == 200, r.text
    return {x["name"]: x for x in r.json()["items"]}


def test_absent_allowlist_means_everything_off(tmp_path, monkeypatch):
    """没配 enabled_only → 面板全不勾。这是如实显示，不是故障。

    实例里此刻确实一个技能都用不了 —— 面板要是显示"全勾着"，那才是在骗人。
    """
    client, _inst, _shared = _client(
        tmp_path, monkeypatch, inst_cfg="a: 1\n", shared=["alpha", "beta"],
    )
    items = _items(client)
    assert set(items) == {"alpha", "beta"}
    assert items["alpha"]["enabled"] is False
    assert items["beta"]["enabled"] is False


def test_enabled_follows_the_allowlist(tmp_path, monkeypatch):
    """白名单里的才勾上 —— 真机上 cc 那 33 个技能按理全是没勾的。"""
    client, _inst, _shared = _client(
        tmp_path, monkeypatch,
        inst_cfg="skills:\n  enabled_only:\n    - alpha\n",
        shared=["alpha", "beta"],
    )
    items = _items(client)
    assert items["alpha"]["enabled"] is True
    assert items["beta"]["enabled"] is False


def test_save_writes_enabled_only_not_disabled(tmp_path, monkeypatch):
    """批量保存落盘的键必须是 enabled_only，绝不能冒出 disabled。"""
    client, inst, _shared = _client(
        tmp_path, monkeypatch, inst_cfg="a: 1\n", shared=["alpha", "beta"],
    )
    r = client.put(
        "/api/runtimes/nanoghost/instances/demo1/skills/batch",
        json={"items": {"alpha": True, "beta": False}},
    )
    assert r.status_code == 200, r.text

    parsed = yaml.safe_load((inst / "config.yaml").read_text(encoding="utf-8"))
    assert parsed["a"] == 1  # 别的键不能被抹掉
    assert parsed["skills"]["enabled_only"] == ["alpha"]
    assert "disabled" not in parsed["skills"]

    items = _items(client)
    assert items["alpha"]["enabled"] is True
    assert items["beta"]["enabled"] is False


def test_save_preserves_names_the_panel_never_showed(tmp_path, monkeypatch):
    """只动被点名的那个，白名单里其它的原样留着。

    面板列不出所有技能（比如按平台过滤掉的、放在 skills.dirs 里的）。保存时要是拿
    面板内容整个覆盖白名单，那些看不见的就被悄悄关掉了。
    """
    client, inst, _shared = _client(
        tmp_path, monkeypatch,
        inst_cfg="skills:\n  enabled_only:\n    - keepme\n",
        shared=["alpha"],
    )
    r = client.put(
        "/api/runtimes/nanoghost/instances/demo1/skills/batch",
        json={"items": {"alpha": True}},
    )
    assert r.status_code == 200, r.text

    parsed = yaml.safe_load((inst / "config.yaml").read_text(encoding="utf-8"))
    assert parsed["skills"]["enabled_only"] == ["alpha", "keepme"]


def test_skill_without_frontmatter_name_is_not_listed(tmp_path, monkeypatch):
    """缺 frontmatter name 的技能不列 —— NanoGhost 加载时直接跳过它。

    真机上的 `iwms` 就是这么个例子（只有 description）。列出来的话，用户勾上、
    保存、白名单里多个名字，而 agent 那边压根没注册过这个名字：**勾了没有任何反应，
    也没有任何报错**。面板宁可少列一个，也不能列一个假名字。
    """
    client, inst, shared = _client(
        tmp_path, monkeypatch, inst_cfg="a: 1\n", shared=["alpha"],
    )
    d = shared / "noname"
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text("---\ndescription: 没有 name\n---\nbody\n", encoding="utf-8")

    items = _items(client)
    assert "noname" not in items
    assert items["alpha"]["enabled"] is False


def test_configured_dirs_replace_the_shared_dir(tmp_path, monkeypatch):
    """配了 skills.dirs 就只扫这些 —— 共享目录整个丢掉。

    用户的 `cc` 33 个技能**全在共享目录里**，实例自己的 skills/ 是空的。所以给它配了
    dirs 等于把这些全关掉，只剩 dirs 指的那几个。这正是 NanoGhost 的行为，面板必须
    显示同一套，不然界面说有、agent 说没有。
    """
    client, inst, shared = _client(
        tmp_path, monkeypatch,
        inst_cfg="skills:\n  dirs:\n    - ./vendor/sk\n",
        shared=["alpha", "beta"],
    )
    _mk_skill(inst / "vendor" / "sk" / "gamma", "gamma")

    items = _items(client)
    assert set(items) == {"gamma"}


def test_extra_dirs_displace_the_instance_skills_dir(tmp_path, monkeypatch):
    """配了 extra_dirs 时 <实例>/skills 不扫 —— 和共享目录并列的是 extra_dirs。

    NanoGhost 的 `resolve_instance_skill_dirs` 在 extra_dirs 分支直接 return，
    不会再把 `<实例>/skills` 带上。这里跟着来，别自作主张多扫一个目录。
    """
    client, inst, shared = _client(
        tmp_path, monkeypatch,
        inst_cfg="skills:\n  extra_dirs:\n    - ./vendor/sk\n",
        shared=["alpha"],
    )
    _mk_skill(inst / "vendor" / "sk" / "gamma", "gamma")
    _mk_skill(inst / "skills" / "delta", "delta")

    items = _items(client)
    assert set(items) == {"alpha", "gamma"}  # 没有 delta


def test_instance_dir_wins_a_name_collision(tmp_path, monkeypatch):
    """同名技能只列一个，且**实例里那份赢** —— 本地覆盖全局。

    两边都得是这个方向：面板说"这条是实例里的"，agent 实际加载的就必须是同一份。
    要是控制台按实例优先、NanoGhost 按共享优先，用户改了实例里那份却发现没生效。
    """
    client, inst, shared = _client(
        tmp_path, monkeypatch, inst_cfg="a: 1\n", shared=["dup"],
    )
    _mk_skill(inst / "skills" / "dup", "dup")

    items = _items(client)
    assert list(items) == ["dup"]
    assert items["dup"]["source"] == "local"
    got = os.path.realpath(os.path.dirname(os.path.dirname(items["dup"]["path"])))
    assert got == os.path.realpath(str(inst / "skills"))


def test_group_entry_is_listed_under_its_directory_name(tmp_path, monkeypatch):
    """分组目录自己那份 SKILL.md 也算一个技能，名字取**目录名**，不是 frontmatter 的 name。

    NanoGhost 的 `_load_group_skills` 就是拿目录名注册的（`name=group_name`），而 system
    prompt 给模型的导航提示正是 `use_skill(name="分组名")`。面板要是显示 frontmatter 里
    那个名字，用户勾了它、agent 那边根本没这个名字 —— 又一例"勾了没反应"。

    这个入口**必须**能勾到：子技能名压根不在模型上下文里，只有展开分组才看得到，少了
    它整组都够不着。真机上 `lark`（26 个子技能）和 `image`（2 个）都是这种结构。
    """
    client, _inst, shared = _client(tmp_path, monkeypatch, inst_cfg="a: 1\n", shared=[])
    grp = shared / "lark"
    _mk_skill(grp / "lark-im", "lark-im")
    _mk_skill(grp / "lark-calendar", "lark-calendar")
    (grp / "SKILL.md").write_text(
        "---\nname: 飞书套件\ndescription: 飞书相关的一组技能\n---\nbody\n", encoding="utf-8",
    )

    items = _items(client)
    assert set(items) == {"lark", "lark-im", "lark-calendar"}
    assert items["lark"]["description"] == "飞书相关的一组技能"
    assert items["lark"]["category"] == "lark"
    assert items["lark-im"]["category"] == "lark"
    assert items["lark-calendar"]["category"] == "lark"


def test_third_level_skills_are_not_listed(tmp_path, monkeypatch):
    """只认两层：扫描根 → 分组 → 子技能。第三层的 NanoGhost 看不见，面板也不许列。

    列出来用户就会勾上，白名单里多一个 agent 从没注册过的名字，又是"勾了没反应"。
    """
    client, _inst, shared = _client(tmp_path, monkeypatch, inst_cfg="a: 1\n", shared=[])
    _mk_skill(shared / "grp" / "sub", "sub")
    _mk_skill(shared / "grp" / "sub" / "deep", "deep")
    _mk_skill(shared / "flat", "flat")

    items = _items(client)
    assert set(items) == {"sub", "flat"}


def test_platforms_frontmatter_does_not_hide_a_skill(tmp_path, monkeypatch):
    """`platforms:` 不该让技能从面板上消失 —— NanoGhost 压根不拿它做判断。

    `discovery.py:138` 把它读进来、`:196` 存进字段、`models.py` 序列化出去，就这三处，
    没有任何筛选。面板要是拿它过滤，就会出现"面板没有、agent 有"。

    这里用 `plan9` 而不是 macos/windows：`_skill_matches_platform` 比的是 `os.sys.platform`，
    拿真实平台名写断言的话，这条用例在别的宿主上结论会变。
    """
    client, _inst, shared = _client(tmp_path, monkeypatch, inst_cfg="a: 1\n", shared=[])
    d = shared / "posix-ish"
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(
        "---\nname: posix-ish\ndescription: 随便哪个平台\nplatforms:\n  - plan9\n---\nbody\n",
        encoding="utf-8",
    )

    assert "posix-ish" in _items(client)


def test_global_skills_skip_the_platform_filter_for_nanoghost(tmp_path):
    """全局注册表页也一样：nanoghost 不过滤 `platforms:`，hermes 过。

    这两条路是同一个函数、同一个目录，只差一个开关 —— 开关接反了就又回到"界面说没有、
    agent 说有"。
    """
    from server.skills import list_global_skills_runtime

    shared = tmp_path / "shared"
    _mk_skill(shared / "any", "any")
    d = shared / "posix-ish"
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(
        "---\nname: posix-ish\ndescription: 随便哪个平台\nplatforms:\n  - plan9\n---\nbody\n",
        encoding="utf-8",
    )

    ng = {x["name"] for x in list_global_skills_runtime(shared, apply_platform_filter=False)}
    hermes = {x["name"] for x in list_global_skills_runtime(shared, apply_platform_filter=True)}
    assert ng == {"any", "posix-ish"}
    assert hermes == {"any"}


def test_unticking_the_last_skill_leaves_an_empty_allowlist(tmp_path, monkeypatch):
    """全部取消 = 写个空列表，语义是"全禁" —— 和 mcp 的白名单一致，不是"恢复默认"。"""
    client, inst, _shared = _client(
        tmp_path, monkeypatch,
        inst_cfg="skills:\n  enabled_only:\n    - alpha\n",
        shared=["alpha"],
    )
    r = client.put(
        "/api/runtimes/nanoghost/instances/demo1/skills/batch",
        json={"items": {"alpha": False}},
    )
    assert r.status_code == 200, r.text

    parsed = yaml.safe_load((inst / "config.yaml").read_text(encoding="utf-8"))
    assert parsed["skills"]["enabled_only"] == []
