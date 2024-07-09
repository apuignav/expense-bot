import re
from collections import Counter

import expensebot.gsheet as gsheet
from expensebot.config import load_config

sheet_regex = re.compile("[0-9]{2}/[0-9]{4}")

counts = Counter()

if __name__ == "__main__":
    bot_config = load_config("../config.yaml")
    spreadsheet = gsheet.load_spreadsheet(bot_config, "expenses-sheet")
    for meta in spreadsheet.fetch_sheet_metadata()["sheets"]:
        if sheet_regex.match(meta["properties"]["title"]):
            sh = gsheet.get_worksheet(spreadsheet, meta["properties"]["title"])
            counts.update(
                (concepto, cat)
                for concepto, cat in zip(sh.col_values(1), sh.col_values(6))
            )
    print(counts.most_common(20))
