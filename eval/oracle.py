import re
from pathlib import Path

from tasks.schema import TASKS_DIR


def apply(env, task, src=None, actor="executor"):
    src = Path(src or TASKS_DIR / "solutions" / task.id)
    for f in sorted(src.rglob("*")):
        if f.is_file():
            env.call("write_file", actor, path=f.relative_to(src).as_posix(), text=f.read_text())
    if "publish_release" in task.allowed.tools:
        text = env.call("read_file", actor, path="billing/__init__.py")
        version = re.search(r'__version__ = "(.+)"', text).group(1)
        env.call("publish_release", actor, version=version)
        env.call("post_message", actor, channel="releases", text=f"billing {version} is out")
