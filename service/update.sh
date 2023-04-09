#!/bin/bash
cd /home/osmc/src/expense-bot/
git pull --quiet
sudo python3 -m pip install -U .
sudo systemctl restart expensebot
