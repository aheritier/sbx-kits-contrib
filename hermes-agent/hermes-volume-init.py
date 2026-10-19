#!/usr/bin/env python3
import fcntl
import os
import sys


def initialize():
    enabled = os.environ.get("HERMES_INIT_VOLUME", "")
    if enabled in ("", "0"):
        return
    if enabled != "1" or os.environ.get("HERMES_HOME") != "/data":
        raise RuntimeError("volume initialization requires HERMES_INIT_VOLUME=1 and HERMES_HOME=/data")
    if os.geteuid() != 0:
        raise RuntimeError("volume initialization must run as root")

    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    fd = os.open("/data", flags)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        current = os.fstat(fd)
        if current.st_dev == os.stat("/").st_dev or not os.path.ismount("/data"):
            raise RuntimeError("/data must be a separately mounted filesystem")
        owner = (current.st_uid, current.st_gid)
        if owner == (0, 0):
            entries = os.listdir(fd)
            if entries == ["lost+found"]:
                recovery = os.open("lost+found", flags, dir_fd=fd)
                try:
                    info = os.fstat(recovery)
                    if (info.st_uid, info.st_gid) != (0, 0) or os.listdir(recovery):
                        raise RuntimeError("refusing incompatible lost+found")
                finally:
                    os.close(recovery)
            elif entries:
                raise RuntimeError("refusing to initialize a nonempty root-owned volume")
            # Transfer ownership last so a retry can finish interrupted initialization.
            os.fchmod(fd, 0o700)
            os.fchown(fd, 1000, 1000)
        elif owner != (1000, 1000):
            raise RuntimeError("refusing to change an existing volume's owner")

        os.fchdir(fd)
        os.setgroups([])
        os.setgid(1000)
        os.setuid(1000)
        if not os.access(".", os.W_OK | os.X_OK):
            raise RuntimeError("/data is not writable by UID 1000")
    finally:
        os.close(fd)


if __name__ == "__main__":
    try:
        initialize()
    except (OSError, RuntimeError) as error:
        sys.exit(f"Hermes volume initialization failed: {error}")
