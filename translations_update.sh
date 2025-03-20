#!/bin/bash

# This script updates .po translation files.

# Generate the .pot file.
shopt -s globstar
xgettext -d messages -o messages.pot **/*.py

# Merge the .pot file into existing .po file for each language in locales directory (if exists):
for lang in locales/*; do
    if [ -f "$lang/LC_MESSAGES/messages.po" ]; then
        msgmerge --no-fuzzy-matching -U $lang/LC_MESSAGES/messages.po messages.pot
    else
        msginit --no-translator -i messages.pot -o $lang/LC_MESSAGES/messages.po -l $lang
    fi
done

# Cleanup
rm messages.pot