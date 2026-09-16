import re, sys
p = sys.argv[1]
content = open(p, encoding="utf-8").read()
for m in re.finditer(r'<Group>(.*?)</Group>', content, re.DOTALL):
    grp = m.group(1)
    name = re.search(r'<GroupName>(.*?)</GroupName>', grp)
    paths = re.findall(r'<FilePath>(.*?)</FilePath>', grp)
    if not name: continue
    print(f"Group: {name.group(1)}")
    for fp in paths:
        print(f"  -> {fp}")
    print()
