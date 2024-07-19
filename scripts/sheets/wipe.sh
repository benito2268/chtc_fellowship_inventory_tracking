#!/bin/sh

read -p "Are you sure? Wiping the current sheet will LOSE HISTORY AND SHARING [y/n] " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]
then
	python3 drive_delete_auto.py
	python3 sheet_create.py $1
fi
