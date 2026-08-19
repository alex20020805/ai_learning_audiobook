# Repository Working Agreement

## Completing implementation tickets

After an implementation ticket passes its required tests and review, publish its
current `codex/` branch to GitHub and open a draft pull request against the
appropriate base branch. A ticket is not complete until:

- the implementation and ticket-status changes are committed;
- the branch tracks its GitHub remote;
- the draft pull request contains the change summary and validation evidence;
- the branch name, commit hash, pull-request target, and pull-request URL are
  reported to the user.

Do not publish private fixtures, copyrighted source documents, credentials, or
other ignored local data. If GitHub authentication, the repository remote, or
the correct pull-request base is unavailable, preserve the local commit and
report the exact blocker instead of guessing.
