Expense tracking Telegram bot
=============================

* Free software: BSD 3-Clause License

Service operation
-----------------

The systemd unit runs the bot in the foreground and restarts it if the process
exits. Install an updated unit with:

```bash
sudo cp service/expensebot.service /etc/systemd/system/expensebot.service
sudo systemctl daemon-reload
sudo systemctl enable --now expensebot
```

The default currency selected with `/setCurrency` is persisted in
`/home/osmc/.expensebot-state.yaml`, so it survives deployments, failures, and
machine reboots.

`service/update.sh` can remain in the existing nightly crontab if automatic
updates are desired. It installs and restarts the service only when `git pull`
retrieves a new commit. Remove the crontab entry if deployments will be handled
manually instead.

Historical category discovery
-----------------------------

When fixed and explicit category matching fail, the bot can reuse a category
from recent expenses with the same normalized concept. By default it searches
the current and previous six monthly sheets and requires at least two matches
whose categories all agree. The history is loaded at startup and refreshed
lazily when an unmatched expense arrives after the six-hour cache lifetime.
Failed refreshes retain stale history and are retried after fifteen minutes.

Defaults can be overridden in the bot configuration:

```yaml
category-discovery:
  enabled: true
  months: 6
  minimum-occurrences: 2
  cache-ttl-hours: 6
  retry-delay-minutes: 15
```
