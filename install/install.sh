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

python3 setup.py