# Open the file with utf-8-sig to handle the BOM
with open('data.json', 'r', encoding='utf-8-sig') as file:
    data = file.read()

# Save it back as a normal UTF-8 encoded file (without BOM)
with open('data.json', 'w', encoding='utf-8') as file:
    file.write(data)
