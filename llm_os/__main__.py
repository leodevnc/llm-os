import argparse
import fcntl
from pathlib import Path

from .kernel import Kernel
from .providers import Runner
from .server import make_server


def main():
    parser = argparse.ArgumentParser(description="Run the local LLM OS workspace (Linux/macOS/WSL)")
    parser.add_argument("--data", type=Path, default=Path(".llm-os"))
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()
    args.data.mkdir(parents=True, exist_ok=True)
    lock = (args.data / "server.lock").open("a+")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        parser.error("Another server already owns this data directory")
    kernel = Kernel(args.data / "workspace.sqlite3")
    kernel.seed()
    runner = Runner(kernel)
    server = make_server(kernel, runner, args.port)
    for task_id in kernel.recover():
        runner.submit(task_id)
    print(f"LLM OS: http://127.0.0.1:{server.server_port} (data: {args.data.resolve()})", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        runner.close()
        lock.close()


if __name__ == "__main__":
    main()
