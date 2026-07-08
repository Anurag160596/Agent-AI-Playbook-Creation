"""
playbook_forge — turn contact-centre SOPs into structured, compliance-checked
agent-assist playbooks.

Pipeline:  SOP text  ->  extractor (AI)  ->  Playbook  ->  validator  ->  renderer
"""

from playbook_forge.schema import Playbook, Step, StepType, Branch  # noqa: F401
from playbook_forge.extractor import extract_playbook  # noqa: F401
from playbook_forge.validator import validate, summarize, Issue, Severity  # noqa: F401
from playbook_forge.renderer import to_markdown, to_mermaid  # noqa: F401

__version__ = "0.1.0"
