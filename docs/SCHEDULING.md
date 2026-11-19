# Running it automatically

Schedule the bot to run **daily**. It decides by itself when to make the weekly report.

## macOS (launchd)

```bash
bash scripts/install_macos.sh                 # daily at 09:00; HOUR=7 MINUTE=30 bash … to change
launchctl list | grep research-digest         # "-  0  io.github…" = installed, last run OK
bash scripts/uninstall_macos.sh
```

launchd runs a missed job when the Mac wakes up, and `RunAtLoad` also runs it at login.

**Permissions:** if `output_dir` is inside Desktop, Documents or Downloads, macOS blocks background
programs from writing there. The log then shows `Operation not permitted`. Either choose another folder
(the default `~/ResearchDigest` is fine), or give your `python3` Full Disk Access under
System Settings ▸ Privacy & Security ▸ Full Disk Access.

With `method = mail_app`, macOS asks once whether python3 may control Mail. Click **OK**.

## Linux (cron)

```bash
bash scripts/install_linux_cron.sh            # daily at 09:00
crontab -l                                    # check
```

cron does not catch up missed runs. On laptops, prefer a **systemd user timer**:

```ini
# ~/.config/systemd/user/research-digest.service
[Service]
Type=oneshot
WorkingDirectory=%h/research-digest-bot
ExecStart=/usr/bin/python3 digest.py

# ~/.config/systemd/user/research-digest.timer
[Timer]
OnCalendar=*-*-* 09:00
Persistent=true

[Install]
WantedBy=timers.target
```

```bash
systemctl --user enable --now research-digest.timer
```

## Windows (Task Scheduler)

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install_windows.ps1
```

This creates a daily task with *"Run task as soon as possible after a scheduled start is missed"*.

## SMTP password in a scheduled job

Set `DIGEST_SMTP_PASSWORD` where the job runs:

- **launchd:** add an `EnvironmentVariables` dict to the plist, or use `launchctl setenv`.
- **cron:** start the line with `DIGEST_SMTP_PASSWORD=... `, or read it from a file only you can read.
- **systemd:** add `Environment=DIGEST_SMTP_PASSWORD=...` to the service, or use `EnvironmentFile=`.
- **Windows:** set it as a user environment variable (`setx DIGEST_SMTP_PASSWORD "..."`).
