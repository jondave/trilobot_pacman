import os
import pwd
import sys


def main():
    user = pwd.getpwnam("trilobot")
    for root, directories, files in os.walk("/data/demos", followlinks=False):
        os.chown(root, user.pw_uid, user.pw_gid, follow_symlinks=False)
        for name in directories + files:
            os.chown(
                os.path.join(root, name),
                user.pw_uid,
                user.pw_gid,
                follow_symlinks=False,
            )
    os.setgroups([user.pw_gid])
    os.setgid(user.pw_gid)
    os.setuid(user.pw_uid)
    os.execv(
        sys.executable,
        [sys.executable, "control_scripts/blockly/app.py"],
    )


if __name__ == "__main__":
    main()
