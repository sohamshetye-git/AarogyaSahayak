import os

file_path = r"c:\Arogya Sahayak_AI_antigravity\apps\healthcare-portal\src\features\asha\FollowupsScreen.tsx"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Find the end of the main component
marker = "      </div>\n    </div>\n  );\n}"
idx = content.find(marker)

if idx != -1:
    new_content = content[:idx + len(marker)]
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print("Successfully truncated the file.")
else:
    print("Marker not found!")
