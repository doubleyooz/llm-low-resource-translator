from constants.bibles import ABK, BCC1923, BCNDA, KOAD21, NIV


OUTPUT_FOLDER = "output/bibles"
LOG_FILENAME = f'{KOAD21.get("text")}_{BCNDA.get("text")}_{ABK.get("text")}_{NIV.get("text")}_{BCC1923.get("text")}'
# OUTPUT_FOLDER = "output/translations"
# LOG_FILENAME = f'translation_{SL}2{TL}'