#!/bin/bash
cd /home/osmc/src/expense-bot/
git pull
sudo systemctl restart expensebot
