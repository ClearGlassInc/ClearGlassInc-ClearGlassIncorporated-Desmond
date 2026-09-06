# Example Integration Scripts

This file contains practical examples of how to integrate the facial recognition system into real-world applications.

## Example 1: Door Access Control System

### PowerShell Implementation
```powershell
<#
.SYNOPSIS
    Smart door lock with facial recognition authentication
    
.DESCRIPTION
    Captures webcam image and authenticates user for door access
    
.EXAMPLE
    .\DoorAccessControl.ps1 -ExpectedPerson "John Doe"
#>

param(
    [string]$ExpectedPerson,
    [string]$WebcamIndex = 0,
    [int]$UnlockDurationSeconds = 5
)

# Function to capture webcam image
function Capture-WebcamImage {
    param([int]$CameraIndex = 0)
    
    Add-Type -AssemblyName System.Drawing
    
    # PowerShell OpenCV capture (requires OpenCVSharp)
    # Or use external tool like ffmpeg
    $outputPath = ".\temp_capture.jpg"
    
    # Using ffmpeg (install separately)
    & ffmpeg -f dshow -i video="Integrated Camera" -frames:v 1 -y $outputPath 2>$null
    
    return $outputPath
}

# Function to unlock door (replace with actual hardware control)
function Unlock-Door {
    param([int]$DurationSeconds)
    
    Write-Host "🔓 DOOR UNLOCKED" -ForegroundColor Green
    
    # Example: Send signal to Arduino/Raspberry Pi
    # Invoke-RestMethod -Uri "http://192.168.1.100/unlock" -Method POST
    
    # Or control relay via GPIO/COM port
    # $port = New-Object System.IO.Ports.SerialPort("COM3", 9600)
    # $port.Open()
    # $port.WriteLine("UNLOCK")
    # $port.Close()
    
    Start-Sleep -Seconds $DurationSeconds
    
    Write-Host "🔒 Door locked" -ForegroundColor Yellow
}

# Main logic
Write-Host "=== Door Access Control ===" -ForegroundColor Cyan
Write-Host "Stand in front of camera...`n"

# Capture image
$imagePath = Capture-WebcamImage

# Authenticate
.\FaceRecognition-System.ps1 -Mode Authenticate `
    -ImagePath $imagePath `
    -PersonName $ExpectedPerson

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✓ Authentication successful!" -ForegroundColor Green
    Write-Host "Welcome, $ExpectedPerson" -ForegroundColor Green
    
    Unlock-Door -DurationSeconds $UnlockDurationSeconds
    
    # Log access
    $logEntry = @{
        Timestamp = Get-Date -Format 'o'
        Person = $ExpectedPerson
        Action = "Door unlocked"
        Success = $true
    } | ConvertTo-Json
    
    Add-Content -Path ".\access_log.json" -Value $logEntry
}
else {
    Write-Host "`n✗ Authentication failed!" -ForegroundColor Red
    Write-Host "Access denied." -ForegroundColor Red
    
    # Log failed attempt
    $logEntry = @{
        Timestamp = Get-Date -Format 'o'
        ExpectedPerson = $ExpectedPerson
        Action = "Door access denied"
        Success = $false
    } | ConvertTo-Json
    
    Add-Content -Path ".\access_log.json" -Value $logEntry
    
    # Optional: Take photo of unauthorized person
    Copy-Item $imagePath ".\security_alerts\unauthorized_$(Get-Date -Format 'yyyyMMdd_HHmmss').jpg"
}

# Cleanup
Remove-Item $imagePath -ErrorAction SilentlyContinue
```

---

## Example 2: Employee Time Clock

### Python Implementation
```python
#!/usr/bin/env python3
"""
Facial Recognition Time Clock
Employees clock in/out using facial recognition
"""

import os
import json
import cv2
from datetime import datetime
from FaceRecognition_Local import FaceRecognitionLocal

class FaceTimeClock:
    def __init__(self):
        self.fr = FaceRecognitionLocal()
        self.timesheet_file = "timesheet.json"
        
    def load_timesheet(self):
        """Load existing timesheet"""
        if os.path.exists(self.timesheet_file):
            with open(self.timesheet_file, 'r') as f:
                return json.load(f)
        return {}
    
    def save_timesheet(self, timesheet):
        """Save timesheet"""
        with open(self.timesheet_file, 'w') as f:
            json.dump(timesheet, f, indent=2)
    
    def capture_webcam(self):
        """Capture image from webcam"""
        cap = cv2.VideoCapture(0)
        
        print("\nPosition yourself in front of camera...")
        print("Press SPACE to capture, ESC to cancel")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Error accessing webcam")
                return None
            
            # Display preview
            cv2.imshow('Time Clock - Press SPACE to capture', frame)
            
            key = cv2.waitKey(1)
            if key == 32:  # SPACE
                image_path = f"temp_capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                cv2.imwrite(image_path, frame)
                break
            elif key == 27:  # ESC
                cap.release()
                cv2.destroyAllWindows()
                return None
        
        cap.release()
        cv2.destroyAllWindows()
        return image_path
    
    def clock_in_out(self):
        """Main clock in/out process"""
        print("\n" + "="*50)
        print("EMPLOYEE TIME CLOCK")
        print("="*50)
        
        # Capture image
        image_path = self.capture_webcam()
        if not image_path:
            print("Capture cancelled")
            return
        
        # Identify employee
        result = self.fr.identify_person(image_path, tolerance=0.6)
        
        if not result:
            print("\n✗ Employee not recognized")
            print("Please contact HR to enroll in the system")
            os.remove(image_path)
            return
        
        employee_name = result['person_name']
        confidence = result['confidence']
        
        # Load timesheet
        timesheet = self.load_timesheet()
        
        if employee_name not in timesheet:
            timesheet[employee_name] = []
        
        # Determine if clocking in or out
        employee_records = timesheet[employee_name]
        
        if len(employee_records) == 0 or employee_records[-1].get('clock_out'):
            # Clock in
            action = "CLOCK IN"
            record = {
                'clock_in': datetime.now().isoformat(),
                'confidence': confidence
            }
            employee_records.append(record)
        else:
            # Clock out
            action = "CLOCK OUT"
            employee_records[-1]['clock_out'] = datetime.now().isoformat()
            
            # Calculate hours worked
            clock_in = datetime.fromisoformat(employee_records[-1]['clock_in'])
            clock_out = datetime.now()
            duration = clock_out - clock_in
            hours = duration.total_seconds() / 3600
            employee_records[-1]['hours_worked'] = round(hours, 2)
        
        # Save timesheet
        self.save_timesheet(timesheet)
        
        print(f"\n✓ {action} SUCCESSFUL")
        print(f"  Employee: {employee_name}")
        print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Confidence: {confidence*100:.1f}%")
        
        if action == "CLOCK OUT":
            print(f"  Hours worked: {employee_records[-1]['hours_worked']:.2f}")
        
        print("="*50 + "\n")
        
        # Cleanup
        os.remove(image_path)
    
    def generate_report(self, employee_name=None):
        """Generate timesheet report"""
        timesheet = self.load_timesheet()
        
        print("\n" + "="*60)
        print("TIMESHEET REPORT")
        print("="*60 + "\n")
        
        employees = [employee_name] if employee_name else timesheet.keys()
        
        for emp in employees:
            if emp not in timesheet:
                continue
            
            print(f"Employee: {emp}")
            print("-" * 60)
            
            total_hours = 0
            
            for record in timesheet[emp]:
                clock_in = record['clock_in']
                clock_out = record.get('clock_out', 'Still clocked in')
                hours = record.get('hours_worked', 0)
                
                print(f"  In:  {clock_in}")
                print(f"  Out: {clock_out}")
                if hours:
                    print(f"  Hours: {hours:.2f}")
                    total_hours += hours
                print()
            
            print(f"Total Hours: {total_hours:.2f}")
            print("="*60 + "\n")

if __name__ == "__main__":
    import sys
    
    clock = FaceTimeClock()
    
    if len(sys.argv) > 1 and sys.argv[1] == "report":
        employee = sys.argv[2] if len(sys.argv) > 2 else None
        clock.generate_report(employee)
    else:
        clock.clock_in_out()
```

**Usage**:
```bash
# Clock in/out
python time_clock.py

# Generate report for all employees
python time_clock.py report

# Generate report for specific employee
python time_clock.py report "John Doe"
```

---

## Example 3: Automated Photo Library Organizer

### PowerShell Scheduled Task
```powershell
<#
.SYNOPSIS
    Automatically organize photos weekly
    
.DESCRIPTION
    Runs weekly to organize new photos by person
    Set up as Windows Task Scheduler job
#>

# Configuration
$photoFolder = "C:\Users\$env:USERNAME\Pictures"
$processedLog = ".\processed_photos.json"

# Load already processed photos
$processed = if (Test-Path $processedLog) {
    Get-Content $processedLog | ConvertFrom-Json
} else {
    @()
}

# Find new photos
$newPhotos = Get-ChildItem -Path $photoFolder -Include *.jpg,*.jpeg,*.png -Recurse |
    Where-Object { $_.FullName -notin $processed }

if ($newPhotos.Count -eq 0) {
    Write-Host "No new photos to process"
    exit
}

Write-Host "Found $($newPhotos.Count) new photos to organize"

# Create organized folder structure
$organizedFolder = Join-Path $photoFolder "OrganizedByPerson"
if (-not (Test-Path $organizedFolder)) {
    New-Item -ItemType Directory -Path $organizedFolder | Out-Null
}

# Process each photo
foreach ($photo in $newPhotos) {
    Write-Host "Processing: $($photo.Name)..." -NoNewline
    
    # Identify person
    .\FaceRecognition-System.ps1 -Mode Identify -ImagePath $photo.FullName
    
    if ($LASTEXITCODE -eq 0) {
        # Get person name from last identification log entry
        $log = Get-Content .\identification_log.json | ConvertFrom-Json
        $lastEntry = $log[-1]
        $personName = $lastEntry.PersonName
        
        # Create person folder
        $personFolder = Join-Path $organizedFolder $personName
        if (-not (Test-Path $personFolder)) {
            New-Item -ItemType Directory -Path $personFolder | Out-Null
        }
        
        # Copy photo
        Copy-Item -Path $photo.FullName -Destination $personFolder
        Write-Host " ✓ → $personName"
    }
    else {
        # Unknown person
        $unknownFolder = Join-Path $organizedFolder "Unknown"
        if (-not (Test-Path $unknownFolder)) {
            New-Item -ItemType Directory -Path $unknownFolder | Out-Null
        }
        
        Copy-Item -Path $photo.FullName -Destination $unknownFolder
        Write-Host " → Unknown"
    }
    
    # Mark as processed
    $processed += $photo.FullName
}

# Save processed log
$processed | ConvertTo-Json | Set-Content $processedLog

# Email summary (optional)
$summary = @"
Photo Organization Complete

Total photos processed: $($newPhotos.Count)
Organized folder: $organizedFolder

Report generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
"@

Send-MailMessage -To "user@example.com" `
    -From "photos@example.com" `
    -Subject "Weekly Photo Organization Complete" `
    -Body $summary `
    -SmtpServer "smtp.example.com"
```

**Schedule with Task Scheduler**:
```powershell
# Create scheduled task to run every Sunday at 3 AM
$action = New-ScheduledTaskAction -Execute "PowerShell.exe" `
    -Argument "-File C:\Scripts\OrganizePhotos.ps1"

$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 3am

Register-ScheduledTask -TaskName "OrganizePhotosWeekly" `
    -Action $action `
    -Trigger $trigger `
    -Description "Automatically organize photos by person"
```

---

## Example 4: Security Camera Alert System

### Python with Email Notifications
```python
#!/usr/bin/env python3
"""
Security Camera Alert System
Monitors security camera folder for unknown faces and sends alerts
"""

import os
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from FaceRecognition_Local import FaceRecognitionLocal

class SecurityMonitor(FileSystemEventHandler):
    def __init__(self, email_config):
        self.fr = FaceRecognitionLocal()
        self.email_config = email_config
        self.processed = set()
    
    def send_alert(self, image_path, person_name=None):
        """Send email alert with image"""
        msg = MIMEMultipart()
        msg['From'] = self.email_config['from']
        msg['To'] = self.email_config['to']
        
        if person_name:
            msg['Subject'] = f"Security Alert: {person_name} detected"
            body = f"""
            Security Camera Alert
            
            Person identified: {person_name}
            Time: {time.strftime('%Y-%m-%d %H:%M:%S')}
            Location: Front Door Camera
            
            See attached image.
            """
        else:
            msg['Subject'] = "Security Alert: Unknown person detected"
            body = f"""
            Security Camera Alert
            
            UNKNOWN PERSON DETECTED
            Time: {time.strftime('%Y-%m-%d %H:%M:%S')}
            Location: Front Door Camera
            
            This person is not in the authorized database.
            See attached image.
            
            Action required: Review and identify.
            """
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Attach image
        with open(image_path, 'rb') as f:
            img = MIMEImage(f.read())
            img.add_header('Content-Disposition', 'attachment', 
                          filename=os.path.basename(image_path))
            msg.attach(img)
        
        # Send email
        with smtplib.SMTP(self.email_config['smtp_server'], 
                         self.email_config['smtp_port']) as server:
            server.starttls()
            server.login(self.email_config['username'], 
                        self.email_config['password'])
            server.send_message(msg)
        
        print(f"Alert sent for {person_name or 'unknown person'}")
    
    def on_created(self, event):
        """Handle new file in camera folder"""
        if event.is_directory:
            return
        
        # Only process image files
        if not event.src_path.lower().endswith(('.jpg', '.jpeg', '.png')):
            return
        
        # Avoid processing same file multiple times
        if event.src_path in self.processed:
            return
        
        self.processed.add(event.src_path)
        
        # Wait for file to be fully written
        time.sleep(2)
        
        print(f"\nNew capture detected: {event.src_path}")
        
        # Identify person
        result = self.fr.identify_person(event.src_path, tolerance=0.6)
        
        if result:
            person_name = result['person_name']
            confidence = result['confidence']
            
            print(f"Identified: {person_name} ({confidence*100:.1f}%)")
            
            # Send alert for known person (optional - for monitoring)
            # self.send_alert(event.src_path, person_name)
        else:
            print("UNKNOWN PERSON DETECTED - Sending alert!")
            self.send_alert(event.src_path, None)

def main():
    # Email configuration
    email_config = {
        'from': 'security@example.com',
        'to': 'admin@example.com',
        'smtp_server': 'smtp.gmail.com',
        'smtp_port': 587,
        'username': 'security@example.com',
        'password': 'your_app_password'  # Use app-specific password
    }
    
    # Camera folder to monitor
    camera_folder = "/path/to/security/camera/captures"
    
    print("Security Camera Monitor Starting...")
    print(f"Monitoring: {camera_folder}")
    print("Press Ctrl+C to stop\n")
    
    # Create and start observer
    event_handler = SecurityMonitor(email_config)
    observer = Observer()
    observer.schedule(event_handler, camera_folder, recursive=False)
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\nMonitoring stopped")
    
    observer.join()

if __name__ == "__main__":
    main()
```

**Installation**:
```bash
pip install watchdog

# Run as service
python security_monitor.py
```

---

## Example 5: Visitor Management System

### Combined PowerShell + Web Interface
```powershell
<#
.SYNOPSIS
    Visitor check-in/check-out system
    
.DESCRIPTION
    Visitors check in using facial recognition
    Generates visitor badges and tracks entry/exit
#>

function Register-Visitor {
    param(
        [string]$VisitorName,
        [string]$Company,
        [string]$HostEmployee,
        [string]$PhotoPath
    )
    
    Write-Host "=== Visitor Registration ===" -ForegroundColor Cyan
    
    # Enroll visitor (temporary)
    .\FaceRecognition-System.ps1 -Mode Enroll `
        -ImagePath $PhotoPath `
        -PersonName "VISITOR_$VisitorName"
    
    # Create visitor record
    $visitorRecord = @{
        VisitorName = $VisitorName
        Company = $Company
        HostEmployee = $HostEmployee
        CheckInTime = Get-Date -Format 'o'
        PhotoPath = $PhotoPath
        BadgeNumber = Get-Random -Minimum 1000 -Maximum 9999
        Status = "Checked In"
    }
    
    # Save to visitor log
    $visitorLog = if (Test-Path ".\visitor_log.json") {
        Get-Content ".\visitor_log.json" | ConvertFrom-Json
    } else {
        @()
    }
    
    $visitorLog += $visitorRecord
    $visitorLog | ConvertTo-Json | Set-Content ".\visitor_log.json"
    
    # Generate visitor badge (PDF)
    & .\Generate-VisitorBadge.ps1 -VisitorRecord $visitorRecord
    
    Write-Host "`n✓ Visitor registered!" -ForegroundColor Green
    Write-Host "  Name: $VisitorName"
    Write-Host "  Badge #: $($visitorRecord.BadgeNumber)"
    Write-Host "  Host: $HostEmployee"
}

function CheckOut-Visitor {
    param([string]$PhotoPath)
    
    Write-Host "=== Visitor Check-Out ===" -ForegroundColor Cyan
    
    # Identify visitor
    .\FaceRecognition-System.ps1 -Mode Identify -ImagePath $PhotoPath
    
    # Find in visitor log
    $visitorLog = Get-Content ".\visitor_log.json" | ConvertFrom-Json
    $lastIdent = Get-Content ".\identification_log.json" | ConvertFrom-Json | Select-Object -Last 1
    
    $visitor = $visitorLog | Where-Object {
        $_.VisitorName -eq $lastIdent.PersonName.Replace("VISITOR_", "") -and
        $_.Status -eq "Checked In"
    }
    
    if ($visitor) {
        $visitor.Status = "Checked Out"
        $visitor.CheckOutTime = Get-Date -Format 'o'
        
        # Calculate visit duration
        $checkIn = [datetime]$visitor.CheckInTime
        $checkOut = Get-Date
        $duration = $checkOut - $checkIn
        $visitor.VisitDuration = "$([math]::Floor($duration.TotalHours))h $($duration.Minutes)m"
        
        # Save updated log
        $visitorLog | ConvertTo-Json | Set-Content ".\visitor_log.json"
        
        Write-Host "`n✓ Visitor checked out!" -ForegroundColor Green
        Write-Host "  Name: $($visitor.VisitorName)"
        Write-Host "  Visit duration: $($visitor.VisitDuration)"
        
        # Delete visitor from face database (privacy)
        # [Add deletion code here]
    }
    else {
        Write-Host "`n✗ Visitor not found or already checked out" -ForegroundColor Red
    }
}

# Usage
# Register-Visitor -VisitorName "Jane Smith" -Company "ABC Corp" `
#     -HostEmployee "John Doe" -PhotoPath ".\visitor.jpg"
```

---

## Example 6: Multi-Camera Integration

### Python with Multiple Camera Support
```python
"""
Multi-Camera Facial Recognition System
Processes feeds from multiple cameras simultaneously
"""

import cv2
import threading
import queue
from FaceRecognition_Local import FaceRecognitionLocal

class CameraProcessor:
    def __init__(self, camera_id, location_name):
        self.camera_id = camera_id
        self.location_name = location_name
        self.fr = FaceRecognitionLocal()
        self.frame_queue = queue.Queue(maxsize=10)
        self.running = False
    
    def capture_frames(self):
        """Capture frames from camera"""
        cap = cv2.VideoCapture(self.camera_id)
        
        while self.running:
            ret, frame = cap.read()
            if ret:
                if not self.frame_queue.full():
                    self.frame_queue.put(frame)
        
        cap.release()
    
    def process_frames(self):
        """Process frames for facial recognition"""
        while self.running:
            if not self.frame_queue.empty():
                frame = self.frame_queue.get()
                
                # Save frame temporarily
                temp_path = f"temp_{self.camera_id}.jpg"
                cv2.imwrite(temp_path, frame)
                
                # Identify person
                result = self.fr.identify_person(temp_path, tolerance=0.6)
                
                if result:
                    print(f"[{self.location_name}] Detected: {result['person_name']}")
                    
                    # Log detection with location
                    # ... logging code ...
    
    def start(self):
        """Start camera processing"""
        self.running = True
        
        # Start capture thread
        capture_thread = threading.Thread(target=self.capture_frames)
        capture_thread.start()
        
        # Start processing thread
        process_thread = threading.Thread(target=self.process_frames)
        process_thread.start()
    
    def stop(self):
        """Stop camera processing"""
        self.running = False

# Usage
cameras = [
    CameraProcessor(0, "Front Door"),
    CameraProcessor(1, "Back Entrance"),
    CameraProcessor(2, "Lobby"),
]

for cam in cameras:
    cam.start()

print("Multi-camera system running...")
```

---

## Installation Notes

All examples require the main facial recognition system to be set up first.

**PowerShell Examples**:
- Require Windows PowerShell 5.1+
- Some require additional modules (install as needed)

**Python Examples**:
- Require Python 3.8+
- Install dependencies:
  ```bash
  pip install opencv-python watchdog
  ```

---

## Security Considerations

1. **Webcam Access**: Ensure only authorized applications can access cameras
2. **Network Security**: If using network cameras, use encrypted connections
3. **Temporary Files**: Always clean up captured images
4. **Access Logs**: Regularly review and secure access logs
5. **Alert Fatigue**: Configure thresholds to avoid too many false alerts

---

**Last Updated**: February 2026  
**Examples Version**: 1.0
