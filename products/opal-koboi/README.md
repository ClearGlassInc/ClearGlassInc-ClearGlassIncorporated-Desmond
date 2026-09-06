# Facial Recognition System - Complete Documentation

## ⚠️ LEGAL & ETHICAL REQUIREMENTS

### **CRITICAL: READ BEFORE USE**

This system is designed ONLY for authorized, legal use cases. You are responsible for compliance with all applicable laws.

### Required Legal Compliance:
- ✅ **GDPR** (EU): Biometric data is "special category" data requiring explicit consent
- ✅ **CCPA** (California): Biometric information must be disclosed in privacy policy
- ✅ **BIPA** (Illinois): Requires written consent and data retention policies
- ✅ **Local Privacy Laws**: Check your jurisdiction's specific requirements

### Authorized Use Cases ONLY:
1. **User Authentication** - Users opt-in to use face recognition for login
2. **Private Property Security** - Your own property with proper signage
3. **Personal Photo Organization** - Your own photos/family photos with consent

### ❌ PROHIBITED Uses:
- Public surveillance without consent
- Scraping internet for faces
- Identifying people without authorization
- Any form of stalking or harassment
- Unauthorized workplace surveillance

---

## System Overview

### Architecture
```
┌─────────────────────────────────────────────────┐
│         PowerShell Main Script                  │
│     (FaceRecognition-System.ps1)                │
└───────────────┬─────────────────────────────────┘
                │
    ┌───────────┴────────────┐
    │                        │
┌───▼────────┐      ┌────────▼─────┐
│ Azure Face │      │ Local Python │
│   API      │      │  Alternative │
│ (Cloud)    │      │  (Offline)   │
└───┬────────┘      └────────┬─────┘
    │                        │
    └───────────┬────────────┘
                │
    ┌───────────▼────────────┐
    │   Local Database       │
    │ + Consent Logs         │
    │ + Identification Logs  │
    └────────────────────────┘
```

### Features
- ✅ **Consent Management** - Built-in consent workflow with audit trail
- ✅ **Multiple Modes** - Enrollment, Identification, Authentication, Photo Organization
- ✅ **Secure Storage** - Encrypted local database with consent logs
- ✅ **Audit Trail** - All identifications and consents are logged
- ✅ **Privacy Controls** - Data deletion, consent withdrawal support
- ✅ **Cloud + Local** - Azure API or local Python fallback

---

## Installation & Setup

### Prerequisites

#### Option 1: Azure Face API (Recommended)
```powershell
# 1. Azure Account
Sign up: https://portal.azure.com

# 2. Create Face API Resource
- Search "Cognitive Services"
- Create "Face" resource
- Note: Endpoint URL & API Key

# 3. Install PowerShell 5.1+
$PSVersionTable.PSVersion
```

#### Option 2: Local Python Alternative
```powershell
# 1. Install Python 3.8+
python --version

# 2. Install Required Libraries
pip install face_recognition opencv-python pillow numpy

# 3. Use Local Script (provided separately)
```

### Initial Setup

#### Step 1: Run Setup Mode
```powershell
.\FaceRecognition-System.ps1 -Mode Setup
```

**You'll be prompted for:**
- Azure Face API Endpoint (e.g., `https://yourname.cognitiveservices.azure.com`)
- Azure Face API Key
- Person Group ID (e.g., `company-employees` or `family-members`)
- Consent requirement (recommended: Yes)
- Data encryption (recommended: Yes)
- Database path (default: `.\face_database.json`)

#### Step 2: Verify Configuration
```powershell
# Check config.json was created
Get-Content .\config.json | ConvertFrom-Json
```

---

## Usage Guide

### 1️⃣ Enrolling New People

**Scenario: Adding an employee to authentication system**

```powershell
# Enroll with single photo
.\FaceRecognition-System.ps1 -Mode Enroll `
    -ImagePath "C:\Photos\john_doe.jpg" `
    -PersonName "John Doe"
```

**What Happens:**
1. Consent screen appears (if enabled)
2. User types "I CONSENT" to agree
3. Face is detected in image
4. Person added to person group
5. Face template stored (not the actual image)
6. System trains on new data
7. Consent logged with timestamp

**Best Practices:**
- Use clear, front-facing photos
- Good lighting, no sunglasses
- Only one face per image
- Multiple photos per person improves accuracy

**Enrolling Multiple Photos:**
```powershell
# Enroll 3-5 photos for better accuracy
$photos = @(
    "C:\Photos\john_1.jpg",
    "C:\Photos\john_2.jpg",
    "C:\Photos\john_3.jpg"
)

foreach ($photo in $photos) {
    .\FaceRecognition-System.ps1 -Mode Enroll `
        -ImagePath $photo `
        -PersonName "John Doe"
}
```

---

### 2️⃣ Identifying People

**Scenario: Security camera captured an image, who is it?**

```powershell
# Identify person from photo
.\FaceRecognition-System.ps1 -Mode Identify `
    -ImagePath "C:\SecurityCamera\capture_20260204_1430.jpg"
```

**Output Example:**
```
=== Person Identification ===
Detecting faces in image...
Found 1 face(s)
Identifying person...

✓ Person Identified!
Name: John Doe
Confidence: 87.34%

Additional Information:
  Age (estimated): 42
  Gender: male
  Primary Emotion: neutral
```

**Confidence Scores:**
- `90-100%` - Very high confidence
- `70-90%` - High confidence (typical)
- `50-70%` - Medium confidence (review recommended)
- `<50%` - Low confidence (not returned)

---

### 3️⃣ Authentication

**Scenario: Verify someone is who they claim to be**

```powershell
# Authenticate John Doe
.\FaceRecognition-System.ps1 -Mode Authenticate `
    -ImagePath "C:\Login\webcam_capture.jpg" `
    -PersonName "John Doe"

# Exit code 0 = Success, 1 = Failed
if ($LASTEXITCODE -eq 0) {
    Write-Host "Access Granted"
} else {
    Write-Host "Access Denied"
}
```

**Use Cases:**
- Building access control
- Computer login verification
- Secure area authentication
- Time clock verification

---

### 4️⃣ Organizing Photos

**Scenario: Sort vacation photos by person**

```powershell
# Organize all photos in a folder
.\FaceRecognition-System.ps1 -Mode OrganizePhotos `
    -ImagePath "C:\Photos\VacationPhotos2026"
```

**What Happens:**
```
VacationPhotos2026/
├── IMG_001.jpg  →  John Doe/IMG_001.jpg
├── IMG_002.jpg  →  Jane Smith/IMG_002.jpg
├── IMG_003.jpg  →  Unknown/IMG_003.jpg
└── ...

Results:
- John Doe/ (45 photos)
- Jane Smith/ (38 photos)
- Bob Johnson/ (22 photos)
- Unknown/ (12 photos)
- organization_results.csv
```

**CSV Output:**
```csv
Image,Person,Confidence
IMG_001.jpg,John Doe,0.8945
IMG_002.jpg,Jane Smith,0.9123
IMG_003.jpg,Unknown,0
```

---

## 🔐 Security Hardening (v2.0)

These primitives live in [`opal_security.py`](opal_security.py) and are unit-tested in
[`tests/test_opal_security.py`](../../tests/test_opal_security.py). They strengthen the
**consent-based** product — none of them add surveillance or mass-identification capability.

| Capability | What it does | Class |
|---|---|---|
| **Encryption-at-rest** | Biometric templates are stored via `EncryptedVault` (Fernet / AES-128-CBC + HMAC). The key lives in `face_vault.key` with `0600` permissions; nothing is written in plaintext. | `EncryptedVault` |
| **Non-bypassable consent** | Enrollment refuses to persist a template without recorded consent. Skipping requires an explicit, audited `OPAL_ALLOW_NO_CONSENT=1` override (testing only). | `ConsentRegistry` |
| **Tamper-evident audit** | Every consent / enroll / identify / authenticate / delete / purge event is appended to a hash-chained ledger (`audit_ledger_local.json`); `verify()` detects any retroactive edit. | `AuditLedger` |
| **Retention / auto-purge** | Drop enrollments older than a configurable window (BIPA/GDPR data-minimization). | `RetentionPolicy` |
| **Liveness / anti-spoofing** | The authentication path can require a liveness score in `[0,1]`, failing closed against photo-replay. | `LivenessPolicy` |

### New CLI commands

```bash
# Require anti-spoofing on authentication (score from your liveness detector)
python FaceRecognition-Local.py authenticate --image webcam.jpg --name "John Doe" \
    --require-liveness --liveness-score 0.93

# Purge enrollments older than 365 days (data-minimization)
python FaceRecognition-Local.py purge --retention-days 365

# Migrate a legacy plaintext pickle database into the encrypted vault
python FaceRecognition-Local.py migrate --source face_database_local.pkl
```

> Requires `cryptography` (added to `requirements.txt`). The encrypted store now lives at
> `face_database_local.enc`; run `migrate` once to import any pre-v2.0 `.pkl` database.

## Privacy & Data Management

### Viewing Consent Records
```powershell
# View all consent records
Get-Content .\consent_log.json | ConvertFrom-Json | Format-Table

# Search specific person
Get-Content .\consent_log.json | ConvertFrom-Json | 
    Where-Object {$_.PersonName -eq "John Doe"}
```

### Viewing Identification Log
```powershell
# View all identifications
Get-Content .\identification_log.json | ConvertFrom-Json | Format-Table

# Recent identifications
Get-Content .\identification_log.json | ConvertFrom-Json | 
    Select-Object -Last 10
```

### Deleting Person Data (GDPR Right to Erasure)
```powershell
# Script to delete person data
$personName = "John Doe"

# 1. Get person ID from database
$db = Get-Content .\face_database.json | ConvertFrom-Json
$person = $db | Where-Object {$_.Name -eq $personName}

if ($person) {
    # 2. Delete from Azure (requires manual API call or separate script)
    Write-Host "Person ID to delete: $($person.PersonId)"
    Write-Host "Use Azure Portal or API to delete person: $($person.PersonId)"
    
    # 3. Remove from local database
    $db | Where-Object {$_.Name -ne $personName} | 
        ConvertTo-Json | Set-Content .\face_database.json
    
    Write-Host "Local data removed for $personName"
}
```

### Data Retention Policy
```powershell
# Example: Delete identifications older than 90 days
$retentionDays = 90
$cutoffDate = (Get-Date).AddDays(-$retentionDays)

$log = Get-Content .\identification_log.json | ConvertFrom-Json
$filtered = $log | Where-Object {
    [datetime]$_.Timestamp -gt $cutoffDate
}

$filtered | ConvertTo-Json | Set-Content .\identification_log.json
Write-Host "Deleted records older than $retentionDays days"
```

---

## Security Best Practices

### 1. Protect API Keys
```powershell
# Store API key in secure credential manager (Windows)
$apiKey = Read-Host "Enter API Key" -AsSecureString
$credential = New-Object PSCredential("AzureKey", $apiKey)
$credential | Export-Clixml -Path ".\secure_key.xml"

# Load securely
$credential = Import-Clixml -Path ".\secure_key.xml"
$apiKey = $credential.GetNetworkCredential().Password
```

### 2. Encrypt Database
```powershell
# Use Windows Data Protection API (DPAPI)
function Encrypt-DatabaseFile {
    param([string]$FilePath)
    
    $data = Get-Content $FilePath -Raw
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($data)
    $encrypted = [System.Security.Cryptography.ProtectedData]::Protect(
        $bytes, 
        $null, 
        [System.Security.Cryptography.DataProtectionScope]::CurrentUser
    )
    
    [System.IO.File]::WriteAllBytes("$FilePath.encrypted", $encrypted)
    Remove-Item $FilePath
}

Encrypt-DatabaseFile -FilePath ".\face_database.json"
```

### 3. Network Security
```powershell
# Use HTTPS only, verify certificates
$PSDefaultParameterValues['Invoke-RestMethod:SkipCertificateCheck'] = $false

# Monitor API calls
Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action {
    Write-Host "API calls made: $global:ApiCallCount"
}
```

### 4. Access Control
```powershell
# Set file permissions (Windows)
$acl = Get-Acl ".\config.json"
$acl.SetAccessRuleProtection($true, $false)
$rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
    $env:USERNAME, "FullControl", "Allow"
)
$acl.SetAccessRule($rule)
Set-Acl ".\config.json" $acl
```

---

## Compliance Templates

### Privacy Notice Template
```text
FACIAL RECOGNITION PRIVACY NOTICE

We use facial recognition technology for [PURPOSE: employee authentication/photo organization/security].

Information We Collect:
- Facial biometric templates (mathematical representations)
- Enrollment date and images used
- Identification timestamps and results

How We Use It:
- [Authenticate users/Organize photos/Monitor security]
- Templates are stored securely and encrypted
- Not shared with third parties

Your Rights:
- Access your biometric data
- Request deletion at any time
- Withdraw consent
- Receive copy of consent records

Contact: [Your Contact Information]
Retention Period: [X days/months]
Last Updated: [Date]
```

### Consent Form Template
```text
FACIAL RECOGNITION CONSENT FORM

I, [NAME], consent to the collection and use of my facial biometric data for:
☐ Employee authentication
☐ Photo organization
☐ Security monitoring
☐ Other: _______________

I understand:
- My facial template will be stored securely
- I can withdraw consent at any time
- I can request deletion of my data
- This data will not be sold or shared

Signature: ________________  Date: ________
```

### Signage Template (for security cameras)
```text
┌─────────────────────────────────────┐
│   FACIAL RECOGNITION IN USE         │
│                                     │
│   This area is monitored using      │
│   facial recognition technology     │
│                                     │
│   Data is stored for [X days]       │
│   and processed in accordance       │
│   with our privacy policy.          │
│                                     │
│   For questions or to opt-out:      │
│   Contact: [Phone/Email]            │
└─────────────────────────────────────┘
```

---

## Troubleshooting

### Common Issues

#### "No faces detected in image"
```powershell
# Solutions:
# 1. Check image quality
Invoke-Item $ImagePath  # View the image

# 2. Verify face is front-facing and well-lit
# 3. Check file format (JPG, PNG supported)
# 4. Resize if too large
$img = [System.Drawing.Image]::FromFile($ImagePath)
if ($img.Width -gt 4096) {
    Write-Host "Image too large, resize to max 4096px"
}
```

#### "Person not identified" (low confidence)
```powershell
# Solutions:
# 1. Enroll more photos (3-5 recommended)
# 2. Use varied angles and lighting
# 3. Retrain person group
# 4. Check photo quality of identification image

# Force retrain
$config = Get-Content .\config.json | ConvertFrom-Json
# [Call Train-PersonGroup function]
```

#### "Azure API Error: 401 Unauthorized"
```powershell
# Check API key is valid
$config = Get-Content .\config.json | ConvertFrom-Json
Write-Host "Endpoint: $($config.AzureEndpoint)"
Write-Host "API Key (first 10 chars): $($config.AzureApiKey.Substring(0,10))..."

# Test connection
Invoke-RestMethod -Uri "$($config.AzureEndpoint)/face/v1.0/" `
    -Headers @{'Ocp-Apim-Subscription-Key'=$config.AzureApiKey}
```

#### "Rate limit exceeded"
```powershell
# Azure Face API Free Tier Limits:
# - 20 calls per minute
# - 30,000 calls per month

# Solution: Add delays between calls
Start-Sleep -Seconds 3  # Wait 3 seconds between calls
```

---

## Advanced Usage

### Batch Enrollment Script
```powershell
# Enroll multiple people from CSV
$people = Import-Csv ".\employees.csv"
# CSV format: Name,PhotoPath

foreach ($person in $people) {
    Write-Host "Enrolling: $($person.Name)"
    .\FaceRecognition-System.ps1 -Mode Enroll `
        -ImagePath $person.PhotoPath `
        -PersonName $person.Name
    
    Start-Sleep -Seconds 3  # Rate limiting
}
```

### Integration with Security Camera
```powershell
# Monitor folder for new captures
$watcher = New-Object System.IO.FileSystemWatcher
$watcher.Path = "C:\SecurityCamera\Captures"
$watcher.Filter = "*.jpg"
$watcher.EnableRaisingEvents = $true

$action = {
    $path = $Event.SourceEventArgs.FullPath
    Write-Host "New capture: $path"
    
    # Identify person
    .\FaceRecognition-System.ps1 -Mode Identify -ImagePath $path
}

Register-ObjectEvent -InputObject $watcher -EventName Created -Action $action

Write-Host "Monitoring for new captures... Press Ctrl+C to stop"
while ($true) { Start-Sleep -Seconds 1 }
```

### Scheduled Photo Organization
```powershell
# Windows Task Scheduler - Run weekly
$action = New-ScheduledTaskAction -Execute "PowerShell.exe" `
    -Argument "-File C:\Scripts\FaceRecognition-System.ps1 -Mode OrganizePhotos -ImagePath C:\Photos"

$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 3am

Register-ScheduledTask -TaskName "OrganizePhotos" `
    -Action $action -Trigger $trigger `
    -Description "Organize photos by person weekly"
```

### Custom Reporting
```powershell
# Generate weekly identification report
$startDate = (Get-Date).AddDays(-7)
$log = Get-Content .\identification_log.json | ConvertFrom-Json

$report = $log | Where-Object {
    [datetime]$_.Timestamp -gt $startDate
} | Group-Object PersonName | Select-Object @{
    Name='Person'; Expression={$_.Name}
}, @{
    Name='Identifications'; Expression={$_.Count}
}, @{
    Name='AvgConfidence'; Expression={
        ($_.Group.Confidence | Measure-Object -Average).Average
    }
}

$report | Export-Csv ".\weekly_report.csv" -NoTypeInformation
$report | Format-Table -AutoSize
```

---

## API Reference

### Azure Face API Endpoints Used

| Endpoint | Purpose | Method |
|----------|---------|--------|
| `/face/v1.0/detect` | Detect faces in image | POST |
| `/face/v1.0/persongroups/{id}` | Create person group | PUT |
| `/face/v1.0/persongroups/{id}/persons` | Add person | POST |
| `/face/v1.0/persongroups/{id}/persons/{pid}/persistedFaces` | Add face | POST |
| `/face/v1.0/persongroups/{id}/train` | Train group | POST |
| `/face/v1.0/identify` | Identify person | POST |

### PowerShell Functions

| Function | Description |
|----------|-------------|
| `Detect-Face` | Detect faces in image file |
| `Create-PersonGroup` | Create new person group |
| `Add-PersonToGroup` | Add person to group |
| `Add-PersonFace` | Add face image to person |
| `Train-PersonGroup` | Train the recognition model |
| `Identify-Person` | Identify person from image |
| `Get-UserConsent` | Display consent workflow |

---

## File Structure

```
FacialRecognitionSystem/
│
├── FaceRecognition-System.ps1      # Main script
├── FaceRecognition-Local.py        # Local Python alternative
├── config.json                     # Configuration (encrypted)
├── face_database.json              # Person database
├── consent_log.json                # Consent records
├── identification_log.json         # Identification history
│
├── Documentation/
│   ├── README.md                   # This file
│   ├── COMPLIANCE_GUIDE.md         # Legal compliance
│   └── API_REFERENCE.md            # Technical reference
│
└── Templates/
    ├── privacy_notice.txt          # Privacy notice template
    ├── consent_form.txt            # Consent form
    └── signage.txt                 # Camera signage
```

---

## Version History

### v1.0 (Current)
- ✅ Azure Face API integration
- ✅ Consent management system
- ✅ Multi-mode operation
- ✅ Comprehensive logging
- ✅ Photo organization
- ✅ Security best practices

### Planned Features (v2.0)
- 🔄 Local Python fallback (offline mode)
- 🔄 Web dashboard for management
- 🔄 Automated data retention enforcement
- 🔄 Multi-camera support
- 🔄 Real-time video stream processing
- 🔄 Mobile app integration

---

## Support & Resources

### Official Documentation
- **Azure Face API**: https://learn.microsoft.com/azure/cognitive-services/face/
- **Privacy Laws**: 
  - GDPR: https://gdpr.eu/
  - CCPA: https://oag.ca.gov/privacy/ccpa
  - BIPA: https://www.ilga.gov/legislation/ilcs/ilcs3.asp?ActID=3004

### Getting Help
1. Check this documentation
2. Review error messages in logs
3. Test with Azure Portal directly
4. Contact Azure Support for API issues

### Best Practice Resources
- NIST Face Recognition Vendor Test
- ISO/IEC 30107 Biometric Presentation Attack Detection
- IEEE Standards for Biometric Privacy

---

## Legal Disclaimer

This software is provided as-is for authorized use only. Users are responsible for:
- Obtaining proper legal authorization
- Compliance with all applicable laws
- Proper consent management
- Secure data handling
- Appropriate use limitations

The authors assume no liability for misuse or legal violations.

---

**Last Updated**: February 2026  
**Version**: 1.0  
**License**: Use at your own legal risk - ensure compliance with local laws
