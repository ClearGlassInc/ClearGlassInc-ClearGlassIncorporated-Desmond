# Quick Start Guide - Facial Recognition System

## 🚀 Choose Your Implementation

### Option 1: PowerShell + Azure (Cloud-Based)
**Best for:** Production systems, enterprise use, unlimited scalability  
**Requires:** Azure account, internet connection  
**Cost:** Azure Face API (free tier: 30,000 calls/month)

### Option 2: Python (Local/Offline)
**Best for:** Testing, privacy-focused, no cloud dependency  
**Requires:** Python 3.8+, local processing power  
**Cost:** Free

---

## Option 1: PowerShell + Azure Setup (5 minutes)

### Step 1: Get Azure Face API Key
```
1. Go to: https://portal.azure.com
2. Search "Cognitive Services"
3. Create "Face" resource
4. Select free tier (F0)
5. Copy:
   - Endpoint URL (e.g., https://yourname.cognitiveservices.azure.com)
   - API Key (from "Keys and Endpoint" section)
```

### Step 2: Run Setup
```powershell
# Navigate to script folder
cd C:\FacialRecognition

# Run setup
.\FaceRecognition-System.ps1 -Mode Setup

# Enter when prompted:
# - Azure Endpoint: https://yourname.cognitiveservices.azure.com
# - API Key: [paste your key]
# - Person Group ID: my-company  (lowercase, no spaces)
# - Require consent: Y
# - Encrypt data: Y
```

### Step 3: Enroll Your First Person
```powershell
# Take/select a clear photo (front-facing, good lighting)
.\FaceRecognition-System.ps1 -Mode Enroll `
    -ImagePath "C:\Photos\john_doe.jpg" `
    -PersonName "John Doe"

# Type: I CONSENT (when prompted)
```

### Step 4: Test Identification
```powershell
# Use a different photo of the same person
.\FaceRecognition-System.ps1 -Mode Identify `
    -ImagePath "C:\Photos\john_test.jpg"
```

**✓ Done! You now have a working facial recognition system.**

---

## Option 2: Python Local Setup (5 minutes)

### Step 1: Install Python Dependencies
```bash
# Windows
pip install face_recognition opencv-python pillow numpy

# Linux/Mac
pip3 install face_recognition opencv-python pillow numpy

# If face_recognition fails, install cmake first:
pip install cmake
pip install dlib
pip install face_recognition
```

### Step 2: Verify Installation
```bash
# Test if libraries are working
python -c "import face_recognition; print('✓ Ready!')"
```

### Step 3: Enroll Your First Person
```bash
# Navigate to script folder
cd /path/to/FacialRecognition

# Enroll a person
python FaceRecognition-Local.py enroll \
    --image john_doe.jpg \
    --name "John Doe"

# Type: I CONSENT (when prompted)
```

### Step 4: Test Identification
```bash
# Identify person from photo
python FaceRecognition-Local.py identify \
    --image john_test.jpg
```

**✓ Done! You now have a local facial recognition system.**

---

## Common First Tasks

### Enroll Multiple People
```powershell
# PowerShell
.\FaceRecognition-System.ps1 -Mode Enroll -ImagePath "alice.jpg" -PersonName "Alice Smith"
.\FaceRecognition-System.ps1 -Mode Enroll -ImagePath "bob.jpg" -PersonName "Bob Johnson"

# Python
python FaceRecognition-Local.py enroll --image alice.jpg --name "Alice Smith"
python FaceRecognition-Local.py enroll --image bob.jpg --name "Bob Johnson"
```

### Organize Your Photo Library
```powershell
# PowerShell
.\FaceRecognition-System.ps1 -Mode OrganizePhotos -ImagePath "C:\Photos\Vacation2026"

# Python
python FaceRecognition-Local.py organize --folder ./Vacation2026
```

### List Enrolled People
```powershell
# PowerShell - check database
Get-Content .\face_database.json | ConvertFrom-Json | Select Name

# Python
python FaceRecognition-Local.py list
```

### Authenticate for Access Control
```powershell
# PowerShell - returns exit code 0 (success) or 1 (fail)
.\FaceRecognition-System.ps1 -Mode Authenticate `
    -ImagePath "webcam_capture.jpg" `
    -PersonName "John Doe"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Access Granted"
} else {
    Write-Host "✗ Access Denied"
}

# Python
python FaceRecognition-Local.py authenticate \
    --image webcam_capture.jpg \
    --name "John Doe"
```

---

## Best Practices for Photos

### ✅ GOOD Photos
- Front-facing, direct to camera
- Good, even lighting (no harsh shadows)
- Clear, sharp focus
- No sunglasses or face coverings
- Neutral expression or slight smile
- Resolution: 1024x1024 or higher recommended
- File formats: JPG, PNG

### ❌ BAD Photos
- Side profile or angled
- Too dark or backlit
- Blurry or low resolution
- Sunglasses, masks, hats
- Multiple people in frame
- Extreme expressions (mouth wide open, etc.)

### Pro Tips
- Enroll 3-5 different photos per person for better accuracy
- Use different lighting conditions (indoor, outdoor, office)
- Include slight variations in angle (±15 degrees)
- Update enrollments periodically (appearance changes over time)

---

## Troubleshooting Quick Fixes

### "No face detected"
```powershell
# Check if image is valid
Test-Path "C:\Photos\image.jpg"  # Should return True

# View the image manually
Invoke-Item "C:\Photos\image.jpg"

# Make sure it's a clear, front-facing photo
```

### "Person not identified" (but they're enrolled)
```bash
# Solution 1: Enroll more photos of the person (3-5 recommended)
# Solution 2: Lower the tolerance (makes matching less strict)

# PowerShell - can't adjust tolerance easily (uses Azure defaults)
# But enrolling more photos helps

# Python - adjust tolerance
python FaceRecognition-Local.py identify \
    --image photo.jpg \
    --tolerance 0.7  # Higher = less strict (0.6 is default)
```

### "Azure API error 401"
```powershell
# Your API key is wrong or expired
# Re-run setup:
.\FaceRecognition-System.ps1 -Mode Setup

# Get new key from Azure Portal if needed
```

### "Module not found" (Python)
```bash
# Install missing package
pip install face_recognition opencv-python pillow numpy

# Or create virtual environment:
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

---

## Performance Comparison

| Feature | PowerShell (Azure) | Python (Local) |
|---------|-------------------|----------------|
| **Setup Time** | 5 minutes | 10 minutes (dependencies) |
| **Accuracy** | 95-99% | 93-97% |
| **Speed (identify)** | 1-2 seconds | 2-5 seconds |
| **Offline Mode** | ❌ No | ✅ Yes |
| **Cost** | Free tier: 30k/month | ✅ Free unlimited |
| **Scalability** | ✅ Unlimited (cloud) | Limited by local CPU |
| **Privacy** | Cloud storage | ✅ Fully local |
| **Face Attributes** | Age, gender, emotion | Face only |

---

## Next Steps

1. ✅ Complete setup (you just did this!)
2. 📸 Enroll 3-5 people with multiple photos each
3. 🧪 Test identification with different photos
4. 📚 Read full documentation: `README.md`
5. 🔒 Review compliance guide for legal requirements
6. 🚀 Build your application!

---

## Integration Examples

### PowerShell: Door Access Control
```powershell
# Capture webcam image
Add-Type -AssemblyName System.Drawing
$camera = New-Object System.Windows.Forms.OpenFileDialog
# ... (webcam capture code)

# Authenticate
.\FaceRecognition-System.ps1 -Mode Authenticate `
    -ImagePath $capturedImage `
    -PersonName $expectedPerson

if ($LASTEXITCODE -eq 0) {
    # Unlock door
    Write-Host "Access Granted"
    # Add door unlock code here
}
```

### Python: Photo Library Organizer
```python
import os
from FaceRecognition_Local import FaceRecognitionLocal

fr = FaceRecognitionLocal()

# Auto-organize new photos daily
photo_folder = "/home/user/Photos/ToOrganize"
fr.organize_photos(photo_folder, tolerance=0.6)
print("Photos organized!")
```

---

## Getting Help

**Issue Found?**
1. Check this guide first
2. Review README.md for detailed docs
3. Check error messages in logs
4. Test with Azure Portal directly (for PowerShell)

**Common Resources:**
- Azure Face API Docs: https://learn.microsoft.com/azure/cognitive-services/face/
- face_recognition library: https://github.com/ageitgey/face_recognition
- OpenCV Docs: https://docs.opencv.org/

---

## Legal Reminder ⚖️

Before deploying to production:
- ✅ Obtain user consent (built-in, but review your specific needs)
- ✅ Create privacy policy
- ✅ Add proper signage (for security cameras)
- ✅ Check local laws (GDPR, CCPA, BIPA)
- ✅ Implement data retention policy
- ✅ Enable audit logging

**This system includes consent management, but you're responsible for legal compliance.**

---

**Last Updated**: February 2026  
**Quick Start Version**: 1.0
