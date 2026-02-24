import os, glob

def replace_in_files():
    files = glob.glob('templates/**/*.html', recursive=True)
    files += glob.glob('core/**/*.py', recursive=True)
    files += glob.glob('beneficiary_system/**/*.py', recursive=True)
    
    replacements = {
        'BenefitBridge': 'Smart Beneficiary Mapping System',
        'BenefitBridge |': 'Smart Beneficiary Mapping System |',
        '— BenefitBridge': '— Smart Beneficiary Mapping System',
        'Access Dashboard': 'Go to Dashboard'
    }

    for f in files:
        with open(f, 'r', encoding='utf-8') as file:
            content = file.read()
        
        new_content = content
        for k, v in replacements.items():
            new_content = new_content.replace(k, v)
        
        if new_content != content:
            with open(f, 'w', encoding='utf-8') as file:
                file.write(new_content)
                print(f"Updated {f}")

if __name__ == '__main__':
    replace_in_files()
