#!/bin/bash

# This script compiles messages.po translation files to messages.mo.

# Compile the .po files into .mo files.
for lang in locales/*; do
    if [ -f "$lang/LC_MESSAGES/messages.po" ]; then
        msgfmt $lang/LC_MESSAGES/messages.po -o $lang/LC_MESSAGES/messages.mo
    fi
done