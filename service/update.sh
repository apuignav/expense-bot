#!/bin/bash
set -eu

cd /home/osmc/src/expense-bot/

old_commit=$(git rev-parse HEAD)
git pull --quiet --ff-only
new_commit=$(git rev-parse HEAD)

if [ "$old_commit" != "$new_commit" ]; then
    sudo /usr/bin/python3 -m pip install -U .
    sudo systemctl restart expensebot
fi
