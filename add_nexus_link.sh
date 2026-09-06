#!/bin/bash

# 1. Safety check: Are we in the clearglassinc.github.io repo?
if [ ! -d ".git" ]; then
    echo "ERROR: Not in a git repository. Please run from the root of clearglassinc.github.io"
    exit 1
fi

# 2. Check that the NEXUS file exists
if [ ! -f "ClearGlass-NEXUS-v12-FINAL.html" ]; then
    echo "ERROR: ClearGlass-NEXUS-v12-FINAL.html not found in current directory"
    exit 1
fi

# 3. Backup index.html
cp index.html index.html.backup
echo "Backup created: index.html.backup"

# 4. Add the new NEXUS link to the navigation bar in index.html
#    This looks for the line containing "/TACTICAL PAGE" and adds a new link right after it.
#    It uses a newline and the proper indentation to match your site's style.
sed -i '/TACTICAL PAGE/a\            <li><a href="ClearGlass-NEXUS-v12-FINAL.html">NEXUS V12 FINAL</a></li>' index.html

# 5. Check if the change was made
if grep -q "ClearGlass-NEXUS-v12-FINAL.html" index.html; then
    echo "SUCCESS: Link to ClearGlass-NEXUS-v12-FINAL.html added to navigation."
    echo "Here is the change (git diff):"
    git diff index.html
else
    echo "FAILED: Could not add the link. Restoring backup."
    mv index.html.backup index.html
    exit 1
fi

# 6. Stage and commit the change
git add index.html
git commit -m "Add NEXUS V12 FINAL page to main navigation"
git push origin main

echo "DONE! Your main website is updated and live."
echo "The new page is accessible at: https://www.clearglassinc.com/ClearGlass-NEXUS-v12-FINAL.html"
echo "And linked from the main navigation bar."
