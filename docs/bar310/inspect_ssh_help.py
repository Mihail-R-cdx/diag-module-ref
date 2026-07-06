"""Read Huawei endpoint SSH CLI help without changing configuration."""

from __future__ import annotations

import argparse
import getpass
import time

import paramiko


def receive(channel, wait: float = 0.8) -> str:
    time.sleep(wait)
    chunks: list[bytes] = []
    while channel.recv_ready():
        chunks.append(channel.recv(65535))
        time.sleep(0.05)
    return b"".join(chunks).decode("utf-8", errors="replace")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("host")
    parser.add_argument("username")
    parser.add_argument("--password")
    parser.add_argument(
        "--command",
        action="append",
        help="Read-only CLI command to run instead of the default help queries",
    )
    args = parser.parse_args()
    password = args.password or getpass.getpass("Password: ")

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        args.host,
        username=args.username,
        password=password,
        look_for_keys=False,
        allow_agent=False,
        timeout=8,
        auth_timeout=8,
    )
    channel = client.invoke_shell(width=160, height=50)
    print(receive(channel, 1.0))
    commands = args.command or (
        "?",
        "omconfig ?",
        "vio ?",
        "media ?",
        "devm ?",
    )
    for command in commands:
        print(f"\n--- {command} ---")
        channel.send(command + "\n")
        print(receive(channel))
    channel.close()
    client.close()


if __name__ == "__main__":
    main()
