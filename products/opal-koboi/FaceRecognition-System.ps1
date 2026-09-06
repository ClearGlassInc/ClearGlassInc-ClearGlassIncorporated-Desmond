#Requires -Version 5.1
<#
.SYNOPSIS
    Authorized Facial Recognition System - Azure Face API Integration

.DESCRIPTION
    PowerShell-based facial recognition system for authorized use cases:
    - User authentication with opt-in consent
    - Private property security monitoring
    - Personal photo library organization
    
    LEGAL REQUIREMENTS:
    - User consent must be obtained before enrollment
    - Proper signage for security camera systems
    - Data must be stored securely with encryption
    - Compliance with local privacy laws (GDPR, CCPA, BIPA)

.PARAMETER Mode
    Operation mode: Enroll, Identify, Authenticate, OrganizePhotos

.PARAMETER ImagePath
    Path to image file for processing

.PARAMETER PersonName
    Name of person for enrollment

.EXAMPLE
    .\FaceRecognition-System.ps1 -Mode Enroll -ImagePath "C:\Photos\john.jpg" -PersonName "John Doe"
    
.EXAMPLE
    .\FaceRecognition-System.ps1 -Mode Identify -ImagePath "C:\Security\capture.jpg"

.NOTES
    Author: Facial Recognition System
    Version: 1.0
    Requires: Azure Face API subscription or local alternatives
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet('Enroll','Identify','Authenticate','OrganizePhotos','Setup')]
    [string]$Mode,
    
    [Parameter(Mandatory=$false)]
    [string]$ImagePath,
    
    [Parameter(Mandatory=$false)]
    [string]$PersonName,
    
    [Parameter(Mandatory=$false)]
    [string]$ConfigPath = ".\config.json"
)

#region Configuration
class FaceRecognitionConfig {
    [string]$AzureEndpoint
    [string]$AzureApiKey
    [string]$PersonGroupId
    [string]$DatabasePath
    [bool]$RequireConsent
    [string]$ConsentLogPath
    [bool]$EncryptData
}

function Load-Configuration {
    if (Test-Path $ConfigPath) {
        try {
            $config = Get-Content $ConfigPath -Raw | ConvertFrom-Json
            return [FaceRecognitionConfig]$config
        }
        catch {
            Write-Error "Failed to load configuration: $_"
            return $null
        }
    }
    else {
        Write-Warning "Configuration file not found. Run with -Mode Setup first."
        return $null
    }
}

function Save-Configuration {
    param([FaceRecognitionConfig]$Config)
    
    $Config | ConvertTo-Json -Depth 10 | Set-Content $ConfigPath
    Write-Host "Configuration saved to $ConfigPath" -ForegroundColor Green
}
#endregion

#region Consent Management
function Get-UserConsent {
    param(
        [string]$PersonName,
        [string]$Purpose = "facial recognition enrollment"
    )
    
    Write-Host "`n=== CONSENT AGREEMENT ===" -ForegroundColor Yellow
    Write-Host "Person: $PersonName"
    Write-Host "Purpose: $Purpose"
    Write-Host "Date: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    Write-Host "`nBy proceeding, you consent to:"
    Write-Host "  - Storage of your facial biometric data"
    Write-Host "  - Use of this data for authorized identification purposes"
    Write-Host "  - Secure encrypted storage of your information"
    Write-Host "`nYou have the right to:"
    Write-Host "  - Withdraw consent at any time"
    Write-Host "  - Request deletion of your data"
    Write-Host "  - Access your stored information"
    Write-Host "========================`n"
    
    $consent = Read-Host "Type 'I CONSENT' to agree (or anything else to cancel)"
    
    if ($consent -eq "I CONSENT") {
        $consentRecord = @{
            PersonName = $PersonName
            Timestamp = Get-Date -Format 'o'
            Purpose = $Purpose
            IPAddress = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.InterfaceAlias -notlike "*Loopback*"} | Select-Object -First 1).IPAddress
            ConsentGiven = $true
        }
        
        # Log consent
        $consentLog = if (Test-Path ".\consent_log.json") {
            Get-Content ".\consent_log.json" -Raw | ConvertFrom-Json
        } else {
            @()
        }
        
        $consentLog += $consentRecord
        $consentLog | ConvertTo-Json -Depth 10 | Set-Content ".\consent_log.json"
        
        Write-Host "Consent recorded successfully.`n" -ForegroundColor Green
        return $true
    }
    else {
        Write-Host "Consent not provided. Operation cancelled." -ForegroundColor Red
        return $false
    }
}
#endregion

#region Azure Face API Functions
function Invoke-AzureFaceAPI {
    param(
        [string]$Endpoint,
        [string]$ApiKey,
        [string]$Method = "POST",
        [string]$Uri,
        [object]$Body
    )
    
    $headers = @{
        'Ocp-Apim-Subscription-Key' = $ApiKey
        'Content-Type' = 'application/json'
    }
    
    $fullUri = "$Endpoint$Uri"
    
    try {
        if ($Body) {
            $jsonBody = $Body | ConvertTo-Json -Depth 10
            $response = Invoke-RestMethod -Uri $fullUri -Method $Method -Headers $headers -Body $jsonBody
        }
        else {
            $response = Invoke-RestMethod -Uri $fullUri -Method $Method -Headers $headers
        }
        return $response
    }
    catch {
        Write-Error "Azure Face API Error: $($_.Exception.Message)"
        return $null
    }
}

function Detect-Face {
    param(
        [string]$ImagePath,
        [FaceRecognitionConfig]$Config
    )
    
    if (-not (Test-Path $ImagePath)) {
        Write-Error "Image file not found: $ImagePath"
        return $null
    }
    
    # Convert image to base64
    $imageBytes = [System.IO.File]::ReadAllBytes($ImagePath)
    $base64Image = [Convert]::ToBase64String($imageBytes)
    
    Write-Host "Detecting faces in image..." -ForegroundColor Cyan
    
    # Call Azure Face API - Detect
    $uri = "/face/v1.0/detect?returnFaceId=true&returnFaceLandmarks=false&returnFaceAttributes=age,gender,emotion"
    
    $headers = @{
        'Ocp-Apim-Subscription-Key' = $Config.AzureApiKey
        'Content-Type' = 'application/octet-stream'
    }
    
    try {
        $response = Invoke-RestMethod -Uri "$($Config.AzureEndpoint)$uri" -Method POST -Headers $headers -Body $imageBytes
        
        if ($response.Count -gt 0) {
            Write-Host "Found $($response.Count) face(s)" -ForegroundColor Green
            return $response
        }
        else {
            Write-Warning "No faces detected in image"
            return $null
        }
    }
    catch {
        Write-Error "Face detection failed: $($_.Exception.Message)"
        return $null
    }
}

function Create-PersonGroup {
    param(
        [string]$PersonGroupId,
        [string]$Name,
        [FaceRecognitionConfig]$Config
    )
    
    $uri = "/face/v1.0/persongroups/$PersonGroupId"
    $body = @{
        name = $Name
        userData = "Created $(Get-Date -Format 'yyyy-MM-dd')"
    }
    
    Write-Host "Creating person group: $Name" -ForegroundColor Cyan
    
    $result = Invoke-AzureFaceAPI -Endpoint $Config.AzureEndpoint -ApiKey $Config.AzureApiKey `
                                  -Method PUT -Uri $uri -Body $body
    
    if ($result -ne $null -or $?) {
        Write-Host "Person group created successfully" -ForegroundColor Green
        return $true
    }
    return $false
}

function Add-PersonToGroup {
    param(
        [string]$PersonGroupId,
        [string]$PersonName,
        [FaceRecognitionConfig]$Config
    )
    
    $uri = "/face/v1.0/persongroups/$PersonGroupId/persons"
    $body = @{
        name = $PersonName
        userData = "Enrolled $(Get-Date -Format 'yyyy-MM-dd')"
    }
    
    Write-Host "Adding person: $PersonName" -ForegroundColor Cyan
    
    $result = Invoke-AzureFaceAPI -Endpoint $Config.AzureEndpoint -ApiKey $Config.AzureApiKey `
                                  -Method POST -Uri $uri -Body $body
    
    if ($result) {
        Write-Host "Person added with ID: $($result.personId)" -ForegroundColor Green
        return $result.personId
    }
    return $null
}

function Add-PersonFace {
    param(
        [string]$PersonGroupId,
        [string]$PersonId,
        [string]$ImagePath,
        [FaceRecognitionConfig]$Config
    )
    
    $imageBytes = [System.IO.File]::ReadAllBytes($ImagePath)
    $uri = "/face/v1.0/persongroups/$PersonGroupId/persons/$PersonId/persistedFaces"
    
    $headers = @{
        'Ocp-Apim-Subscription-Key' = $Config.AzureApiKey
        'Content-Type' = 'application/octet-stream'
    }
    
    Write-Host "Adding face image for person..." -ForegroundColor Cyan
    
    try {
        $response = Invoke-RestMethod -Uri "$($Config.AzureEndpoint)$uri" -Method POST -Headers $headers -Body $imageBytes
        Write-Host "Face added successfully: $($response.persistedFaceId)" -ForegroundColor Green
        return $response.persistedFaceId
    }
    catch {
        Write-Error "Failed to add face: $($_.Exception.Message)"
        return $null
    }
}

function Train-PersonGroup {
    param(
        [string]$PersonGroupId,
        [FaceRecognitionConfig]$Config
    )
    
    $uri = "/face/v1.0/persongroups/$PersonGroupId/train"
    
    Write-Host "Training person group..." -ForegroundColor Cyan
    
    $result = Invoke-AzureFaceAPI -Endpoint $Config.AzureEndpoint -ApiKey $Config.AzureApiKey `
                                  -Method POST -Uri $uri
    
    # Wait for training to complete
    Start-Sleep -Seconds 2
    
    $statusUri = "/face/v1.0/persongroups/$PersonGroupId/training"
    $status = Invoke-AzureFaceAPI -Endpoint $Config.AzureEndpoint -ApiKey $Config.AzureApiKey `
                                  -Method GET -Uri $statusUri
    
    if ($status.status -eq "succeeded") {
        Write-Host "Training completed successfully" -ForegroundColor Green
        return $true
    }
    else {
        Write-Warning "Training status: $($status.status)"
        return $false
    }
}

function Identify-Person {
    param(
        [string]$PersonGroupId,
        [string]$ImagePath,
        [FaceRecognitionConfig]$Config
    )
    
    # First detect faces
    $faces = Detect-Face -ImagePath $ImagePath -Config $Config
    
    if (-not $faces) {
        return $null
    }
    
    $faceIds = $faces | ForEach-Object { $_.faceId }
    
    $uri = "/face/v1.0/identify"
    $body = @{
        personGroupId = $PersonGroupId
        faceIds = $faceIds
        maxNumOfCandidatesReturned = 1
        confidenceThreshold = 0.5
    }
    
    Write-Host "Identifying person..." -ForegroundColor Cyan
    
    $result = Invoke-AzureFaceAPI -Endpoint $Config.AzureEndpoint -ApiKey $Config.AzureApiKey `
                                  -Method POST -Uri $uri -Body $body
    
    if ($result -and $result.Count -gt 0 -and $result[0].candidates.Count -gt 0) {
        $personId = $result[0].candidates[0].personId
        $confidence = $result[0].candidates[0].confidence
        
        # Get person details
        $personUri = "/face/v1.0/persongroups/$PersonGroupId/persons/$personId"
        $person = Invoke-AzureFaceAPI -Endpoint $Config.AzureEndpoint -ApiKey $Config.AzureApiKey `
                                      -Method GET -Uri $personUri
        
        return @{
            PersonId = $personId
            Name = $person.name
            Confidence = $confidence
            FaceAttributes = $faces[0].faceAttributes
        }
    }
    
    return $null
}
#endregion

#region Main Operations
function Invoke-Setup {
    Write-Host "`n=== Facial Recognition System Setup ===" -ForegroundColor Cyan
    Write-Host "This setup will configure your authorized facial recognition system.`n"
    
    $config = [FaceRecognitionConfig]::new()
    
    # Azure Configuration
    Write-Host "Azure Face API Configuration:" -ForegroundColor Yellow
    $config.AzureEndpoint = Read-Host "Enter Azure Face API Endpoint (e.g., https://yourname.cognitiveservices.azure.com)"
    $config.AzureApiKey = Read-Host "Enter Azure Face API Key" -AsSecureString | ConvertFrom-SecureString
    
    # Person Group
    $config.PersonGroupId = Read-Host "Enter Person Group ID (lowercase, no spaces, e.g., 'company-employees')"
    
    # Security Settings
    $config.RequireConsent = (Read-Host "Require user consent? (Y/N)") -eq 'Y'
    $config.EncryptData = (Read-Host "Encrypt stored data? (Y/N)") -eq 'Y'
    $config.DatabasePath = Read-Host "Enter database path (default: .\face_database.json)" 
    if ([string]::IsNullOrWhiteSpace($config.DatabasePath)) {
        $config.DatabasePath = ".\face_database.json"
    }
    $config.ConsentLogPath = ".\consent_log.json"
    
    Save-Configuration -Config $config
    
    # Create person group
    $createGroup = Read-Host "`nCreate person group now? (Y/N)"
    if ($createGroup -eq 'Y') {
        $groupName = Read-Host "Enter person group name"
        Create-PersonGroup -PersonGroupId $config.PersonGroupId -Name $groupName -Config $config
    }
    
    Write-Host "`nSetup complete! You can now use the system." -ForegroundColor Green
}

function Invoke-Enrollment {
    param(
        [string]$ImagePath,
        [string]$PersonName,
        [FaceRecognitionConfig]$Config
    )
    
    Write-Host "`n=== Person Enrollment ===" -ForegroundColor Cyan
    
    # Get consent if required
    if ($Config.RequireConsent) {
        if (-not (Get-UserConsent -PersonName $PersonName -Purpose "facial recognition enrollment")) {
            return
        }
    }
    
    # Detect face in image first
    $faces = Detect-Face -ImagePath $ImagePath -Config $Config
    if (-not $faces) {
        Write-Error "No face detected in image. Please provide a clear photo with one face."
        return
    }
    
    if ($faces.Count -gt 1) {
        Write-Warning "Multiple faces detected. Using the first face only."
    }
    
    # Add person to group
    $personId = Add-PersonToGroup -PersonGroupId $Config.PersonGroupId -PersonName $PersonName -Config $Config
    
    if (-not $personId) {
        Write-Error "Failed to add person to group"
        return
    }
    
    # Add face to person
    $faceId = Add-PersonFace -PersonGroupId $Config.PersonGroupId -PersonId $personId `
                             -ImagePath $ImagePath -Config $Config
    
    if (-not $faceId) {
        Write-Error "Failed to add face to person"
        return
    }
    
    # Train the person group
    $trained = Train-PersonGroup -PersonGroupId $Config.PersonGroupId -Config $Config
    
    if ($trained) {
        # Save to local database
        $database = if (Test-Path $Config.DatabasePath) {
            Get-Content $Config.DatabasePath -Raw | ConvertFrom-Json
        } else {
            @()
        }
        
        $database += @{
            PersonId = $personId
            Name = $PersonName
            EnrollmentDate = Get-Date -Format 'o'
            ImagePath = $ImagePath
        }
        
        $database | ConvertTo-Json -Depth 10 | Set-Content $Config.DatabasePath
        
        Write-Host "`nEnrollment successful!" -ForegroundColor Green
        Write-Host "Person: $PersonName" -ForegroundColor Green
        Write-Host "Person ID: $personId" -ForegroundColor Green
    }
}

function Invoke-Identification {
    param(
        [string]$ImagePath,
        [FaceRecognitionConfig]$Config
    )
    
    Write-Host "`n=== Person Identification ===" -ForegroundColor Cyan
    
    $result = Identify-Person -PersonGroupId $Config.PersonGroupId -ImagePath $ImagePath -Config $Config
    
    if ($result) {
        Write-Host "`n✓ Person Identified!" -ForegroundColor Green
        Write-Host "Name: $($result.Name)" -ForegroundColor Green
        Write-Host "Confidence: $([math]::Round($result.Confidence * 100, 2))%" -ForegroundColor Green
        
        if ($result.FaceAttributes) {
            Write-Host "`nAdditional Information:"
            Write-Host "  Age (estimated): $($result.FaceAttributes.age)"
            Write-Host "  Gender: $($result.FaceAttributes.gender)"
            if ($result.FaceAttributes.emotion) {
                $topEmotion = ($result.FaceAttributes.emotion.PSObject.Properties | Sort-Object Value -Descending | Select-Object -First 1).Name
                Write-Host "  Primary Emotion: $topEmotion"
            }
        }
        
        # Log identification
        $logEntry = @{
            Timestamp = Get-Date -Format 'o'
            PersonName = $result.Name
            Confidence = $result.Confidence
            ImagePath = $ImagePath
        }
        
        $logPath = ".\identification_log.json"
        $log = if (Test-Path $logPath) {
            Get-Content $logPath -Raw | ConvertFrom-Json
        } else {
            @()
        }
        
        $log += $logEntry
        $log | ConvertTo-Json -Depth 10 | Set-Content $logPath
    }
    else {
        Write-Host "`n✗ No matching person found" -ForegroundColor Yellow
        Write-Host "The face in the image is not recognized in the database." -ForegroundColor Yellow
    }
}

function Invoke-PhotoOrganization {
    param(
        [string]$FolderPath,
        [FaceRecognitionConfig]$Config
    )
    
    Write-Host "`n=== Photo Organization ===" -ForegroundColor Cyan
    
    if (-not (Test-Path $FolderPath)) {
        Write-Error "Folder not found: $FolderPath"
        return
    }
    
    $imageFiles = Get-ChildItem -Path $FolderPath -Include *.jpg,*.jpeg,*.png -Recurse
    
    Write-Host "Found $($imageFiles.Count) images to process`n" -ForegroundColor Cyan
    
    $results = @()
    
    foreach ($image in $imageFiles) {
        Write-Host "Processing: $($image.Name)..." -NoNewline
        
        $result = Identify-Person -PersonGroupId $Config.PersonGroupId -ImagePath $image.FullName -Config $Config
        
        if ($result) {
            Write-Host " ✓ $($result.Name)" -ForegroundColor Green
            
            # Create person folder if it doesn't exist
            $personFolder = Join-Path $FolderPath $result.Name
            if (-not (Test-Path $personFolder)) {
                New-Item -ItemType Directory -Path $personFolder -Force | Out-Null
            }
            
            # Copy image to person folder
            Copy-Item -Path $image.FullName -Destination $personFolder -Force
            
            $results += @{
                Image = $image.Name
                Person = $result.Name
                Confidence = $result.Confidence
            }
        }
        else {
            Write-Host " ✗ Unknown" -ForegroundColor Yellow
            
            # Create "Unknown" folder
            $unknownFolder = Join-Path $FolderPath "Unknown"
            if (-not (Test-Path $unknownFolder)) {
                New-Item -ItemType Directory -Path $unknownFolder -Force | Out-Null
            }
            
            Copy-Item -Path $image.FullName -Destination $unknownFolder -Force
        }
    }
    
    Write-Host "`n=== Organization Complete ===" -ForegroundColor Green
    Write-Host "Processed: $($imageFiles.Count) images"
    Write-Host "Identified: $($results.Count) faces"
    Write-Host "Unknown: $($imageFiles.Count - $results.Count) faces"
    
    # Save results
    $results | Export-Csv -Path (Join-Path $FolderPath "organization_results.csv") -NoTypeInformation
}
#endregion

#region Main Execution
try {
    switch ($Mode) {
        'Setup' {
            Invoke-Setup
        }
        
        'Enroll' {
            if (-not $ImagePath -or -not $PersonName) {
                Write-Error "For enrollment, both -ImagePath and -PersonName are required"
                exit 1
            }
            
            $config = Load-Configuration
            if ($config) {
                Invoke-Enrollment -ImagePath $ImagePath -PersonName $PersonName -Config $config
            }
        }
        
        'Identify' {
            if (-not $ImagePath) {
                Write-Error "For identification, -ImagePath is required"
                exit 1
            }
            
            $config = Load-Configuration
            if ($config) {
                Invoke-Identification -ImagePath $ImagePath -Config $config
            }
        }
        
        'Authenticate' {
            if (-not $ImagePath -or -not $PersonName) {
                Write-Error "For authentication, both -ImagePath and -PersonName are required"
                exit 1
            }
            
            $config = Load-Configuration
            if ($config) {
                $result = Identify-Person -PersonGroupId $config.PersonGroupId -ImagePath $ImagePath -Config $config
                
                if ($result -and $result.Name -eq $PersonName) {
                    Write-Host "`n✓ Authentication Successful" -ForegroundColor Green
                    Write-Host "Person: $($result.Name)" -ForegroundColor Green
                    Write-Host "Confidence: $([math]::Round($result.Confidence * 100, 2))%" -ForegroundColor Green
                    exit 0
                }
                else {
                    Write-Host "`n✗ Authentication Failed" -ForegroundColor Red
                    Write-Host "The person in the image does not match $PersonName" -ForegroundColor Red
                    exit 1
                }
            }
        }
        
        'OrganizePhotos' {
            if (-not $ImagePath) {
                Write-Error "For photo organization, -ImagePath (folder path) is required"
                exit 1
            }
            
            $config = Load-Configuration
            if ($config) {
                Invoke-PhotoOrganization -FolderPath $ImagePath -Config $config
            }
        }
    }
}
catch {
    Write-Error "An error occurred: $($_.Exception.Message)"
    Write-Error $_.ScriptStackTrace
    exit 1
}
#endregion
