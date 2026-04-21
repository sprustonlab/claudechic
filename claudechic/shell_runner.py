"""PTY-based shell command execution with color support.

NOTE: PTY support is Unix-only. On Windows, run_in_pty raises NotImplementedError.
Use the fallback in commands.py for Windows (interactive shell via subprocess).
"""

import asyncio
import contextlib
import os
import signal
import subprocess
import sys
from collections.abc import Callable
from typing import TYPE_CHECKING

# PTY support is Unix-only
UNIX_PTY_SUPPORT = sys.platform != "win32"

if UNIX_PTY_SUPPORT or TYPE_CHECKING:
    import pty
    import select


def run_in_pty(
    cmd: str, shell: str, cwd: str | None, env: dict[str, str]
) -> tuple[str, int]:
    """Run command in PTY to capture colors.

    Returns (output, returncode) tuple.

    Raises NotImplementedError on Windows (PTY not available).
    """
    if not UNIX_PTY_SUPPORT:
        raise NotImplementedError("PTY shell execution is not available on Windows")

    master_fd, slave_fd = pty.openpty()
    try:
        proc = subprocess.Popen(
            [shell, "-lc", cmd],
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            cwd=cwd,
            env=env,
            close_fds=True,
            start_new_session=True,
        )
        os.close(slave_fd)

        output = b""
        while True:
            r, _, _ = select.select([master_fd], [], [], 0.1)
            if r:
                try:
                    data = os.read(master_fd, 4096)
                    if data:
                        output += data
                    else:
                        break
                except OSError:
                    break
            elif proc.poll() is not None:
                # Process done, drain remaining output
                while True:
                    r, _, _ = select.select([master_fd], [], [], 0.05)
                    if not r:
                        break
                    try:
                        data = os.read(master_fd, 4096)
                        if data:
                            output += data
                        else:
                            break
                    except OSError:
                        break
                break

        os.close(master_fd)
        proc.wait()
        return output.decode(errors="replace"), proc.returncode or 0
    except Exception:
        os.close(master_fd)
        raise


def _run_in_pty_with_cancel(
    cmd: str,
    shell: str,
    cwd: str | None,
    env: dict[str, str],
    check_cancelled: Callable[[], bool],
) -> tuple[str, int, bool]:
    """Run command in PTY with cancellation support.

    Args:
        cmd: Command to run
        shell: Shell to use
        cwd: Working directory
        env: Environment variables
        check_cancelled: Callable that returns True if cancelled

    Returns:
        (output, returncode, was_cancelled) tuple
    """
    if not UNIX_PTY_SUPPORT:
        raise NotImplementedError("PTY shell execution is not available on Windows")

    master_fd, slave_fd = pty.openpty()
    proc = None
    try:
        proc = subprocess.Popen(
            [shell, "-lc", cmd],
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            cwd=cwd,
            env=env,
            close_fds=True,
            start_new_session=True,
        )
        os.close(slave_fd)
        slave_fd = -1

        output = b""
        was_cancelled = False

        while True:
            # Check for cancellation
            if check_cancelled():
                was_cancelled = True
                # Kill the process group
                with contextlib.suppress(ProcessLookupError, OSError):
                    if sys.platform != "win32":
                        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                    else:
                        proc.terminate()
                break

            r, _, _ = select.select([master_fd], [], [], 0.1)
            if r:
                try:
                    data = os.read(master_fd, 4096)
                    if data:
                        output += data
                    else:
                        break
                except OSError:
                    break
            elif proc.poll() is not None:
                # Process done, drain remaining output
                while True:
                    r, _, _ = select.select([master_fd], [], [], 0.05)
                    if not r:
                        break
                    try:
                        data = os.read(master_fd, 4096)
                        if data:
                            output += data
                        else:
                            break
                    except OSError:
                        break
                break

        os.close(master_fd)
        master_fd = -1
        proc.wait()
        return output.decode(errors="replace"), proc.returncode or 0, was_cancelled

    except Exception:
        if slave_fd >= 0:
            os.close(slave_fd)
        if master_fd >= 0:
            os.close(master_fd)
        if proc and proc.poll() is None:
            with contextlib.suppress(ProcessLookupError, OSError):
                if sys.platform != "win32":
                    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                else:
                    proc.terminate()
        raise


async def run_in_pty_cancellable(
    cmd: str,
    shell: str,
    cwd: str | None,
    env: dict[str, str],
    cancel_event: asyncio.Event,
) -> tuple[str, int, bool]:
    """Run command in PTY with async cancellation support.

    Args:
        cmd: Command to run
        shell: Shell to use
        cwd: Working directory
        env: Environment variables
        cancel_event: Event that signals cancellation when set

    Returns:
        (output, returncode, was_cancelled) tuple
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        _run_in_pty_with_cancel,
        cmd,
        shell,
        cwd,
        env,
        cancel_event.is_set,
    )


def _run_in_subprocess_with_cancel(
    cmd: str,
    shell: str,
    cwd: str | None,
    env: dict[str, str],
    check_cancelled: Callable[[], bool],
) -> tuple[str, int, bool]:
    """Run command via subprocess pipes with cancellation support.

    Fallback for Windows where PTY is not available. Merges stderr into stdout.

    Args:
        cmd: Command to run
        shell: Shell to use (e.g. cmd.exe)
        cwd: Working directory
        env: Environment variables
        check_cancelled: Callable that returns True if cancelled

    Returns:
        (output, returncode, was_cancelled) tuple
    """
    # Build args: on Windows use /c, on Unix use -c
    if sys.platform == "win32":
        args = [shell, "/c", cmd]
    else:
        args = [shell, "-c", cmd]

    proc = subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=cwd,
        env=env,
    )

    output = b""
    was_cancelled = False
    try:
        while True:
            if check_cancelled():
                was_cancelled = True
                proc.terminate()
                break
            # Read in small chunks with a timeout via poll
            if proc.stdout is not None:
                data = proc.stdout.read1(4096) if hasattr(proc.stdout, "read1") else b""
                if data:
                    output += data
                elif proc.poll() is not None:
                    break
                else:
                    # No data yet and process still running — brief sleep to avoid busy loop
                    import time

                    time.sleep(0.05)
            elif proc.poll() is not None:
                break
    finally:
        # Drain any remaining output
        if proc.stdout is not None:
            remaining = proc.stdout.read()
            if remaining:
                output += remaining
        proc.wait()

    return output.decode(errors="replace"), proc.returncode or 0, was_cancelled


async def run_in_subprocess_cancellable(
    cmd: str,
    shell: str,
    cwd: str | None,
    env: dict[str, str],
    cancel_event: asyncio.Event,
) -> tuple[str, int, bool]:
    """Run command via subprocess pipes with async cancellation support.

    Fallback for Windows where PTY is not available.

    Args:
        cmd: Command to run
        shell: Shell to use
        cwd: Working directory
        env: Environment variables
        cancel_event: Event that signals cancellation when set

    Returns:
        (output, returncode, was_cancelled) tuple
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        _run_in_subprocess_with_cancel,
        cmd,
        shell,
        cwd,
        env,
        cancel_event.is_set,
    )
