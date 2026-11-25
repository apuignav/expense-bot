# Wallet expense Shortcut

An Apple Shortcut that sends each Apple Pay payment to the family group as an `/add` command for the expense bot.

## What it does

1. Reads the Wallet notification: the subtitle (the shop) and the body (currency and amount, for example `CHF 12.50`).
2. Cleans the shop name. It looks up the subtitle in the shop table (`shops.json`). If the subtitle contains the `match` text of an entry, the shop name is the `name` of that entry. The first matching entry wins. If no entry matches, it keeps the full subtitle. It replaces `'` with a space, removes all digits (the bot takes the first number in the message as the amount, so `BP 1234 Zürich` would be saved as 1234), collapses repeated spaces and trims the result.
3. Turns the body into `<amount><currency>` with no space, for example `12.50CHF`. It removes thousands separators and accepts `.` or `,` as the decimal mark.
4. Sends `/add@<bot username> <shop> <amount><currency>` to the group through the Telegram Bot API, using the sender bot.
5. Shows a notification if something goes wrong, so the expense can be added by hand:
    - If the body has no amount or no currency, nothing is sent. The notification shows the subtitle and the body.
    - If Telegram replies with `ok` not true, the notification shows the message and the error description.

## Build

Cherri cannot create a Wallet trigger. The build script compiles the source with Cherri, adds the trigger to the compiled file, fills in the deployment values, and signs it. Install [Cherri](https://cherrilang.org/), or set the `CHERRI` environment variable to the path of the Cherri binary. You also need the Proton Pass command line tool (`pass-cli`), logged in. Then run this in the repository root:

```
python3 shortcut/build.py
```

This creates `shortcut/wallet-expense.shortcut`, which Git ignores. It also creates `shortcut/wallet-expense.patched.plist`, an unsigned copy that you can read to check the result. Git ignores it too. The copy does not contain the bot token. Signing needs a Mac.

## Deployment values

The source file has no values in it. The build script reads them from a secure note in Proton Pass:

- Vault: `Server`
- Item: `ExpenseBot Shortcut config`

To use another vault or item, set the `PASS_VAULT` or `PASS_ITEM` environment variable.

The note text is JSON with three keys:

- `token`: the token of the bot that posts to the group (text).
- `chat_id`: the ID of the family group (a number, for example `-1001234567890`).
- `bot_username`: the username of the expense bot, without `@` (text).

The build stops with an error if the note is missing, is not valid JSON, or lacks a key. The error names the key and never shows a value.

The signed `.shortcut` file contains the bot token. Delete every copy of the file after you import it.

## Shops

The shop table is in `shortcut/shops.json`. It is a list of objects with two text fields:

```
{"match": "Coop", "name": "Coop"}
```

If the subtitle of the notification contains `match`, the shop name is `name`. The first matching line wins, so put the more specific lines first. If no line matches, the shop name is the full subtitle.

To add a shop:

1. Add one line to `shortcut/shops.json`.
2. Run `python3 shortcut/build.py`.
3. Import the new `.shortcut` file again on both phones, and add the Wallet trigger again (see below).

The build stops with an error if `shops.json` is not a list of objects with non-empty text fields `match` and `name`.

## Import

Open the built `.shortcut` file on the iPhone and add it. The Shortcuts app asks nothing at import, because all values are already in the file.

## Wallet trigger

The Shortcut reads the subtitle and the body of a notification from the Wallet app. iOS removes the trigger when it imports a Shortcut file, so add it by hand after each import: open the Shortcut, add a trigger for notifications from the Wallet app, and make sure that the Subtitle and Body inputs show the notification icon. You do not need a separate automation.
