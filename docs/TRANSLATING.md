# Translate YT-DLP Studio

YT-DLP Studio speaks English and Hebrew today. You can help add your language. You do not need to write code.

There are two ways to help:

- [Way A: a spreadsheet, no code](#way-a-a-spreadsheet-no-code). For everyone.
- [Way B: with the scripts](#way-b-with-the-scripts-developers). For people who know Git and Python.

## Before you start

Read these rules. They keep the app working.

1. **Keep every `{placeholder}`.** A text such as `Added {count} videos to the queue.` has a part in curly braces. Copy that part as it is, and do not translate the word inside the braces. The app puts a number or a name there.
2. **Keep technical names.** Leave YouTube, FFmpeg, yt-dlp, MP4, MP3, URL and key names such as Ctrl as they are.
3. **Use short, clear words.** A button has little space. Use the word people already know from other apps in your language.
4. **Keep line breaks and bullets.** A cell can have several lines. Keep the same number of lines.
5. **Rows with `_one` at the end of the key** are for exactly one item ("1 video"). If your language has no special form for one, write the same sentence as the row without `_one`.
6. **Do not change the `key` and `en` columns.** Write only in your language column.
7. **Keep the file as UTF-8 CSV.** See the tips in Way A.

If you do not know what a text means, leave the cell empty. The app then shows the English text.

## Way A: a spreadsheet, no code

### 1. Get the file

1. Open the folder [`translations`](https://github.com/NX1X/yt-dlp-studio/tree/main/translations) in the repository.
2. For a **new language**, open `template.csv`. To improve an **existing language**, open its file, for example `he.csv` for Hebrew.
3. Click the download button on the right (the icon with the arrow pointing down, "Download raw file"). Save the file on your computer.

The file has four columns:

| Column | What it is |
|---|---|
| `key` | The name of the text inside the app. Do not change it. |
| `en` | The English text. Translate this. |
| `translation` (or your language code) | Write your translation here. |
| `status` | `missing` means there is no translation yet. Ignore this column. |

### 2. Fill in the column

Open the file in Excel, LibreOffice Calc or Google Sheets, and write your translation in the third column.

- **Excel:** use **Data > From Text/CSV** and choose **UTF-8** as the file origin. Then your letters show correctly. Save with **File > Save As > CSV UTF-8 (Comma delimited)**.
- **LibreOffice Calc:** when you open the file, choose **Unicode (UTF-8)** and the separator **comma**. Save with **File > Save As > Text CSV** and keep the character set on **Unicode (UTF-8)**.
- **Google Sheets:** use **File > Import > Upload**, then **File > Download > Comma Separated Values (.csv)**. Google Sheets saves UTF-8.

Do not delete or move rows, and do not add columns.

### 3. Send the file

1. Open a new issue with the [Translation template](https://github.com/NX1X/yt-dlp-studio/issues/new?template=translation.yml).
2. Write the name of your language and say if you are a native speaker.
3. Drag the file into the box "CSV file". GitHub may not accept `.csv` files in some browsers. If so, zip the file first, and attach the `.zip`.

A maintainer adds your language to the app and tells you in the issue. The language then shows in **Settings > Language** in the next release.

## Way B: with the scripts (developers)

You need the project set up for development. See [DEVELOPMENT.md](DEVELOPMENT.md).

1. Export the texts. For a new language use its code (for example `es`, `pt`, `ar`):

   ```
   python scripts/i18n_export.py --lang es
   ```

   This writes `translations.csv` (not committed) with the columns key, en, es and status. Add `--only-missing` to get only the rows that still need a translation.

2. Edit the `es` column in a spreadsheet. Keep UTF-8.
3. Check the import without writing:

   ```
   python scripts/i18n_import.py --lang es --new --dry-run
   ```

   `--new` adds a new language. Leave it out to update a language that is already in the app. For a code that the app does not list (see `LANGUAGE_INFO` in `src/utils/translations.py`), add `--native-name "Español" --english-name Spanish`, and `--rtl` if the language is written right to left.

4. Run it for real, then run the tests:

   ```
   python scripts/i18n_import.py --lang es --new
   python scripts/i18n_export.py --repo-files
   pytest tests/test_i18n_languages.py tests/test_i18n_tools.py tests/test_translation_keys_used.py tests/test_translations.py
   ```

   `--repo-files` refreshes the files in the `translations` folder. A test fails when they are out of date.

5. Start the app, open **Settings > Language**, choose your language, save and restart. Check every tab and the dialogs.
6. Open a pull request. See [CONTRIBUTING.md](../CONTRIBUTING.md).

The import stops and changes nothing when a key does not exist, a key is repeated, a text is empty or a text has other `{placeholders}` than the English text.

Notes:

- A text that you leave empty gets the English text, and the app shows English for it. You can send a partly translated file.
- Right-to-left languages (Hebrew, Persian, Urdu, Yiddish) get the right-to-left layout on their own.
- Qt's own texts (the OK, Cancel and Yes buttons in message boxes) use Qt's translation file `qtbase_<code>.qm` when it exists for your language.

## How to test a translation in the app

1. Start the app and open **Settings > Language**.
2. Choose your language, click **Save settings** and restart the app.
3. Look at the Download, Queue, History, Settings and About tabs, and open a few dialogs. Click **Info** with a link, add a playlist link, and start a download that fails (for example a wrong link) to see the error texts.
4. Look for cut-off words, English words that are left, and texts that sound strange. Fix the cell and import again.

## Questions

Open an [issue](https://github.com/NX1X/yt-dlp-studio/issues/new/choose) and say which language you work on.
