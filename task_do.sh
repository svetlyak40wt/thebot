#!/bin/bash

set -e

executer -c "task status $1 dmoved"
executer -c "task do $1"
