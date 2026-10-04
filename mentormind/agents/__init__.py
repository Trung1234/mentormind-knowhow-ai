"""Work Assistant and RCA Agent (spec 06).

``work_assistant/`` and ``rca/`` (one agent each, with its own ``prompts/``); shared by both:
``ports`` (what they need from spec 05/07), ``trace`` (FR-04), ``prompting``, ``experts``;
``factory`` wires the real components, ``cli/`` the ``knowhow agent`` commands, ``api`` (with
``supervisor.ask`` and ``rca.investigate``) the REST routers of spec 08.
"""
