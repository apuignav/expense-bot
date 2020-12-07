#!/bin/bash
cd /home/osmc/src/expense-bot/
git pull --quiet
sudo pip install -U .
sudo systemctl restart expensebot
