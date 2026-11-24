# Wallet expense Shortcut

An Apple Shortcut that sends each Apple Pay payment to the family group as an `/add` command for the expense bot.

## What it does

1. Reads the Wallet notification: the subtitle (the shop) and the body (currency and amount, for example `CHF 12.50`).
2. Cleans the shop name. For Coop, Migros and Denner it keeps only the first word of the subtitle. For other shops it keeps the full subtitle. It replaces `'` with a space, removes all digits (the bot takes the first number in the message as the amount, so `BP 1234 Zürich` would be saved as 1234), collapses repeated spaces and trims the result.
3. Turns the body into `<amount><currency>` with no space, for example `12.50CHF`. It removes thousands separators and accepts `.` or `,` as the decimal mark.
4. Sends `/add@<bot username> <shop> <amount><currency>` to the group through the Telegram Bot API, using the sender bot.
5. Shows a notification if something goes wrong, so the expense can be added by hand:
    - If the body has no amount or no currency, nothing is sent. The notification shows the subtitle and the body.
    - If Telegram replies with `ok` not true, the notification shows the message and the error description.

## Compile

Install [Cherri](https://cherrilang.org/), then run this in the repository root:

```
cherri shortcut/wallet-expense.cherri
```

This creates `shortcut/wallet-expense.shortcut`, which Git ignores. Signing needs a Mac. Add `--skip-sign` to compile without signing.

## Import

Open the compiled `.shortcut` file on the iPhone and add it. The Shortcuts app asks three questions:

- Sender bot token: the token of the bot that posts to the group.
- Group chat ID: the ID of the family group, for example `-1001234567890`.
- Expense bot username: the username of the expense bot, without `@`.

The token is stored only in the imported Shortcut on the phone. It is not in the source file.

## Wallet automation

Cherri cannot create a Wallet trigger, so make the automation by hand on the phone:

1. In Shortcuts, open Automation and create a Transaction automation (Wallet).
2. Choose the cards and run it immediately, without asking.
3. Make the automation run this Shortcut.
