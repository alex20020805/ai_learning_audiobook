# Repository Working Agreement

## Completing implementation tickets

After implementation, run an adversarial QA gate through the public browser or
HTTP boundary. Exercise the happy path, malformed and boundary inputs, unusual
interaction order, retry or repeated-action behavior, persistence, traceability,
and the ticket's most plausible failure modes. Turn every discovered defect into
a regression test, fix it, and rerun the gate. Add a brief `QA Summary` to the
ticket Markdown naming the scenarios exercised and their outcomes.

After the QA gate and required review pass, publish the current `codex/` branch
to GitHub and open a draft pull request against the appropriate base branch. A
ticket is not complete until:

- the implementation and ticket-status changes are committed;
- the ticket contains a passing `QA Summary` with adversarial evidence;
- the branch tracks its GitHub remote;
- the draft pull request contains the change summary and validation evidence;
- the branch name, commit hash, pull-request target, and pull-request URL are
  reported to the user.

Do not publish private fixtures, copyrighted source documents, credentials, or
other ignored local data. If GitHub authentication, the repository remote, or
the correct pull-request base is unavailable, preserve the local commit and
report the exact blocker instead of guessing.
