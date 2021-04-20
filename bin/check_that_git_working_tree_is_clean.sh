#!/usr/bin/env sh
#
# Exit with 0 if the current working directory's git working tree is clean,
# exit with 1 if it's unclean (for example if it contains any untracked files,
# or any uncommitted changes to tracked files).
#
# Usage:
#
#     bin/check_that_git_working_tree_is_clean.sh

if [ -n "$(git status --porcelain)" ]; then
    echo -n "It looks like your git working tree is unclean. "
    echo -n "Commit or restore any changes, and commit or delete any "
    echo "untracked files, then try again."
    exit 1
fi
