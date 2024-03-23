#!/bin/bash

if ! command -v python3 &> /dev/null
then
    echo "Python wurde nicht gefunden"
    exit 1
fi

if python3 check_python_version.py &> /dev/null
then
    echo "Python Version ist nicht unterstützt"
    exit 1
fi

if [ -z "$1" ] 
then
    python3 setup.py
else
    python3 setup.py -f "$1"
fi
