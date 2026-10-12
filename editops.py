import sys
with open('aetheros_security/secops/ops.py', 'r', encoding='utf-8') as f:
    content = f.read()
import re
new_content = re.sub(r'(?m)^# Global SecOps orchestrator$',
                     '    @property\n    def forensics(self) -> Forensics:\n        return self._forensics\n\n# Global SecOps orchestrator',
                     content)
with open('aetheros_security/secops/ops.py', 'w', encoding='utf-8') as f:
    f.write(new_content)
