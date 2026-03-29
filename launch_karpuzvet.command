#!/bin/bash
cd "$(dirname "$0")"
export TK_SILENCE_DEPRECATION=1
/usr/bin/python3 app.py
