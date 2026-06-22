"""Read-only inspection helpers for guiding an Ubuntu/Kubuntu release upgrade.

Every helper is read-only: it never mutates system state, never calls sudo, and
never makes network changes. Subcommands print JSON findings to stdout; the
runbook generator renders a stateful Markdown document. The agent runs these and
hands all sudo/destructive commands to the user.
"""

__version__ = "0.1.0"
