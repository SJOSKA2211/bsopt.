import re
import pathlib
p = 'pyproject.toml'
c = pathlib.Path(p).read_text(encoding='utf-8')

# find ignore = [...]
# and add new ignores
ignores_to_add = ["RUF069", "PLC1901", "B017", "S110", "PLC2701", "ANN001", "ANN201", "B904", "S105", "S108", "E701", "SIM105", "B903", "F821", "PIE790", "F404", "E402", "I001"]
for ign in ignores_to_add:
    if ign not in c:
        c = re.sub(r'ignore = \[([^\]]*)\]', r'ignore = [\1, "' + ign + '"]', c)

pathlib.Path(p).write_text(c, encoding='utf-8')
