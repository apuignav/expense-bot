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

Interactive category correction
-------------------------------

An expense that still has no category after fixed, fuzzy, and historical
matching is saved immediately as `Undefined`, then the bot sends an inline
keyboard containing the configured expense categories. Selecting a category
updates the exact row already written to Google Sheets and records the choice
in the in-memory history so later expenses can benefit from it. **Leave
undefined** dismisses the prompt without changing the sheet.

Each prompt belongs to the authorized user who created the expense, is
single-use, and expires after 24 hours. Pending prompts are deliberately kept
only in memory: after a restart an old button reports that it expired, while the
expense remains safely recorded as `Undefined`. Multiline messages receive a
separate category prompt for every undefined expense.

Defaults can be overridden in the bot configuration:

```yaml
category-discovery:
  enabled: true
  months: 6
  minimum-occurrences: 2
  cache-ttl-hours: 6
  retry-delay-minutes: 15
```

Docker Compose deployment
-------------------------

The container uses a multi-stage Python 3.11 build and runs as an unprivileged
user with a read-only root filesystem. It exposes no ports: Telegram polling
and Google Sheets access are outbound connections.

1. Create the configuration directory outside the Git checkout:

   ```bash
   mkdir -p "${DOCKERDIR}/expense-bot/config"
   cp .expensebotrc.example "${DOCKERDIR}/expense-bot/config/expensebot.yaml"
   chmod 600 "${DOCKERDIR}/expense-bot/config/expensebot.yaml"
   ```

   Fill the copied file with the Telegram, Google Sheets, currency, and
   category configuration. In the homelab deployment this file is generated
   from Proton Pass instead of being edited manually.

2. Ensure `DOCKERDIR`, `PUID`, `PGID`, and `TZ` are available in the Compose
   environment, then build and start the bot:

   ```bash
   docker compose up -d --build
   docker compose logs -f expense-bot
   ```

The configuration is mounted read-only from
`${DOCKERDIR}/expense-bot/config/expensebot.yaml`. Existing mutable state stays
at `${DOCKERDIR}/expense-bot/state.yaml`; there is no state migration. Docker's
`local` logging driver retains three 10 MB rotated files. Stop the old Raspberry
Pi service before starting this container so that two polling instances do not
consume the same Telegram updates.
