# fix indent script
with open('gui/main_window.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix lines around eventFilter
# The eventFilter should be a proper method of the class
# All lines inside eventFilter should have +4 spaces relative to 'def'

changes = {
    # line index -> (old, new) content
}

# Find the eventFilter lines
for i, line in enumerate(lines):
    if 'def eventFilter' in line:
        # The def line itself - should have 4 spaces (class method)
        if line.startswith('        def eventFilter'):
            lines[i] = line  # keep as is - 8 spaces is wrong but let's check what's around
        
        # Fix docstring (next line)
        if i+1 < len(lines) and lines[i+1].strip().startswith('"""'):
            lines[i+1] = '        ' + lines[i+1].lstrip()  # was probably 8 spaces, should be 8 (same as def)
        
        # Fix if isinstance line
        if i+2 < len(lines) and 'if isinstance' in lines[i+2]:
            lines[i+2] = '        ' + lines[i+2].lstrip()
        
        # Fix self.log_button_click
        if i+3 < len(lines) and 'self.log_button_click' in lines[i+3]:
            lines[i+3] = '            ' + lines[i+3].lstrip()
        
        # find empty line and fix subsequent lines
        for j in range(i+1, min(i+20, len(lines))):
            if 'return super().eventFilter' in lines[j]:
                lines[j] = '        ' + lines[j].lstrip()
                break
            if '# ' in lines[j] and 'IP-' in lines[j]:
                # skip comment line
                lines[j] = ''
                continue
            if 'device_combo' in lines[j] and lines[j].strip() and not lines[j].startswith('        '):
                lines[j] = '        ' + lines[j].lstrip()
            if lines[j].strip() and not lines[j].startswith('            ') and not lines[j].startswith('        '):
                if 'if obj is' in lines[j] or 'if event.key' in lines[j]:
                    lines[j] = '        ' + lines[j].lstrip()
                elif 'self.trigger_' in lines[j] or 'return True' in lines[j]:
                    lines[j] = '            ' + lines[j].lstrip()
        
        break

with open('gui/main_window.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Done fixing')
