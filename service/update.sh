#!/bin/bash
cd /home/osmc/src/expense-bot/
git pull --quiet
sudo systemctl restart expensebot
