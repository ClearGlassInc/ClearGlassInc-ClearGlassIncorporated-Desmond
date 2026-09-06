#!/usr/bin/env python3
"""
Local Facial Recognition System - Python Implementation
Offline alternative to Azure Face API

LEGAL REQUIREMENTS:
- User consent required before enrollment (enforced, not advisory)
- Secure data storage (encrypted at rest via opal_security.EncryptedVault)
- Compliance with privacy laws (GDPR, CCPA, BIPA)
- Only for authorized use cases

Security hardening (see opal_security.py):
- Encryption-at-rest for the biometric template store
- Non-bypassable consent enforcement
- Tamper-evident, hash-chained audit ledger
- Configurable retention / auto-purge
- Liveness / anti-spoofing gate on the authentication path

Author: Facial Recognition System
Version: 2.0
Requires: face_recognition, opencv-python, pillow, numpy, cryptography
"""

import os
import json
import face_recognition
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
import argparse
import sys

import opal_security as sec

class FaceRecognitionLocal:
    """Local facial recognition system using face_recognition library"""

    def __init__(self, database_path: Optional[str] = None, key_path: Optional[str] = None,
                 retention_days: int = 0):
        base = Path(__file__).resolve().parent
        self.database_path = str(database_path or base / "face_database_local.enc")
        self.key_path = str(key_path or base / "face_vault.key")
        # Encryption-at-rest: biometric templates are never written in plaintext.
        self.vault = sec.EncryptedVault(self.key_path)
        # Tamper-evident audit trail for every consent/enroll/identify/auth event.
        self.audit = sec.AuditLedger(base / "audit_ledger_local.json")
        self.consent = sec.ConsentRegistry(ledger=self.audit)
        self.retention = sec.RetentionPolicy(retention_days)
        self.encodings_db = self._load_database()

    def _load_database(self) -> Dict:
        """Load face encodings from the encrypted vault."""
        data = self.vault.load(self.database_path)
        if not data:
            return {"encodings": [], "names": [], "metadata": []}
        # Encodings are stored as plain lists inside the vault; restore as arrays.
        data["encodings"] = [np.array(e) for e in data.get("encodings", [])]
        data.setdefault("names", [])
        data.setdefault("metadata", [])
        return data

    def _save_database(self):
        """Persist face encodings to the encrypted vault (JSON-safe form)."""
        serializable = {
            "encodings": [np.asarray(e).tolist() for e in self.encodings_db["encodings"]],
            "names": list(self.encodings_db["names"]),
            "metadata": list(self.encodings_db["metadata"]),
        }
        self.vault.save(self.database_path, serializable)

    def _log_identification(self, person_name: str, confidence: float, image_path: str):
        """Record an identification event in the tamper-evident audit ledger."""
        self.audit.append(
            "identification",
            person_name=person_name,
            confidence=round(float(confidence), 4),
            image=os.path.basename(image_path),
        )

    def get_user_consent(self, person_name: str) -> bool:
        """Display consent form and get user agreement"""
        print("\n" + "="*50)
        print("CONSENT AGREEMENT")
        print("="*50)
        print(f"Person: {person_name}")
        print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("\nBy proceeding, you consent to:")
        print("  - Storage of your facial biometric data")
        print("  - Use of this data for authorized identification")
        print("  - Secure encrypted storage of your information")
        print("\nYou have the right to:")
        print("  - Withdraw consent at any time")
        print("  - Request deletion of your data")
        print("  - Access your stored information")
        print("="*50 + "\n")

        consent = input("Type 'I CONSENT' to agree (or anything else to cancel): ")

        if consent == "I CONSENT":
            # Recorded into the tamper-evident ledger via the consent registry.
            self.consent.record(person_name)
            print("\n✓ Consent recorded successfully.\n")
            return True
        else:
            print("\n✗ Consent not provided. Operation cancelled.\n")
            return False

    def enroll_person(self, image_path: str, person_name: str, require_consent: bool = True) -> bool:
        """
        Enroll a person into the facial recognition database

        Args:
            image_path: Path to image file
            person_name: Name of the person
            require_consent: Whether to require consent (default: True)

        Returns:
            bool: True if successful, False otherwise
        """
        print(f"\n{'='*50}")
        print("PERSON ENROLLMENT")
        print(f"{'='*50}\n")

        # Consent gate. Consent is non-bypassable by default; skipping it requires
        # an explicit, audited environment override (intended for testing only).
        if require_consent:
            if not self.get_user_consent(person_name):
                return False
        else:
            if os.environ.get("OPAL_ALLOW_NO_CONSENT") != "1":
                print("✗ Refusing to skip consent. Set OPAL_ALLOW_NO_CONSENT=1 to override "
                      "(testing only).")
                return False
            self.audit.append("consent_waived", person_name=person_name,
                              reason="explicit --no-consent override")
            print("⚠ Consent explicitly waived via OPAL_ALLOW_NO_CONSENT (testing only).")

        # Load and verify image
        if not os.path.exists(image_path):
            print(f"✗ Error: Image file not found: {image_path}")
            return False

        print(f"Loading image: {image_path}")
        image = face_recognition.load_image_file(image_path)

        # Detect faces
        print("Detecting faces...")
        face_locations = face_recognition.face_locations(image, model="hog")

        if len(face_locations) == 0:
            print("✗ Error: No face detected in image")
            return False

        if len(face_locations) > 1:
            print(f"⚠ Warning: Multiple faces detected ({len(face_locations)}). "
                  "Using the first face only.")

        # Generate face encoding
        print("Generating face encoding...")
        face_encodings = face_recognition.face_encodings(image, face_locations)

        if len(face_encodings) == 0:
            print("✗ Error: Could not generate face encoding")
            return False

        encoding = face_encodings[0]

        # Belt-and-suspenders: never persist a template without recorded consent.
        if require_consent:
            self.consent.require(person_name)

        # Add to database
        self.encodings_db["encodings"].append(encoding)
        self.encodings_db["names"].append(person_name)
        self.encodings_db["metadata"].append({
            "enrollment_date": datetime.now().isoformat(),
            "image_path": image_path,
            "face_location": face_locations[0]
        })

        self._save_database()
        self.audit.append("enroll", person_name=person_name,
                          faces=len(self.encodings_db["names"]))

        print("\n✓ Enrollment successful!")
        print(f"  Person: {person_name}")
        print(f"  Faces in database: {len(self.encodings_db['names'])}")
        print(f"{'='*50}\n")

        return True

    def identify_person(self, image_path: str, tolerance: float = 0.6) -> Optional[Dict]:
        """
        Identify a person from an image

        Args:
            image_path: Path to image file
            tolerance: Face comparison tolerance (lower = more strict)

        Returns:
            Dict with identification results or None
        """
        print(f"\n{'='*50}")
        print("PERSON IDENTIFICATION")
        print(f"{'='*50}\n")

        if len(self.encodings_db["encodings"]) == 0:
            print("✗ Error: No enrolled persons in database")
            return None

        # Load image
        if not os.path.exists(image_path):
            print(f"✗ Error: Image file not found: {image_path}")
            return None

        print(f"Loading image: {image_path}")
        image = face_recognition.load_image_file(image_path)

        # Detect faces
        print("Detecting faces...")
        face_locations = face_recognition.face_locations(image, model="hog")

        if len(face_locations) == 0:
            print("✗ Error: No face detected in image")
            return None

        # Get face encodings
        face_encodings = face_recognition.face_encodings(image, face_locations)

        if len(face_encodings) == 0:
            print("✗ Error: Could not generate face encoding")
            return None

        # Compare with database
        print("Comparing with database...")
        unknown_encoding = face_encodings[0]

        # Calculate distances to all known faces
        face_distances = face_recognition.face_distance(
            self.encodings_db["encodings"],
            unknown_encoding
        )

        # Find best match
        best_match_index = np.argmin(face_distances)
        best_distance = face_distances[best_match_index]

        if best_distance > tolerance:
            print("\n✗ No matching person found")
            print(f"  Best match distance: {best_distance:.3f} (threshold: {tolerance})")
            return None

        # Get person info
        person_name = self.encodings_db["names"][best_match_index]
        confidence = 1 - best_distance  # Convert distance to confidence
        metadata = self.encodings_db["metadata"][best_match_index]

        result = {
            "person_name": person_name,
            "confidence": confidence,
            "distance": best_distance,
            "enrollment_date": metadata["enrollment_date"],
            "face_location": face_locations[0]
        }

        # Log identification
        self._log_identification(person_name, confidence, image_path)

        print("\n✓ Person Identified!")
        print(f"  Name: {person_name}")
        print(f"  Confidence: {confidence*100:.2f}%")
        print(f"  Distance: {best_distance:.3f}")
        print(f"  Enrolled: {metadata['enrollment_date']}")
        print(f"{'='*50}\n")

        return result

    def authenticate_person(self, image_path: str, expected_name: str, tolerance: float = 0.6,
                            liveness_score: Optional[float] = None,
                            require_liveness: bool = False) -> bool:
        """
        Authenticate that a person in the image matches expected name

        Args:
            image_path: Path to image file
            expected_name: Expected person name
            tolerance: Face comparison tolerance
            liveness_score: Optional anti-spoofing score in [0, 1] from a liveness detector
            require_liveness: If True, a missing/low liveness score fails authentication

        Returns:
            bool: True if authenticated, False otherwise
        """
        # Anti-spoofing gate first: a photo-replay should never reach matching.
        policy = sec.LivenessPolicy(required=require_liveness)
        passed, reason = policy.evaluate(liveness_score)
        self.audit.append("liveness_check", expected=expected_name, passed=passed, reason=reason)
        if not passed:
            print(f"✗ Liveness check failed: {reason}")
            return False

        result = self.identify_person(image_path, tolerance)
        ok = bool(result and result["person_name"] == expected_name)
        self.audit.append("authenticate", expected=expected_name, success=ok)

        if ok:
            print("✓ Authentication Successful")
            print(f"  Person: {expected_name}")
            print(f"  Confidence: {result['confidence']*100:.2f}%")
            return True
        else:
            print("✗ Authentication Failed")
            if result:
                print(f"  Expected: {expected_name}")
                print(f"  Detected: {result['person_name']}")
            return False

    def organize_photos(self, folder_path: str, tolerance: float = 0.6):
        """
        Organize photos in a folder by person

        Args:
            folder_path: Path to folder containing photos
            tolerance: Face comparison tolerance
        """
        print(f"\n{'='*50}")
        print("PHOTO ORGANIZATION")
        print(f"{'='*50}\n")

        if not os.path.exists(folder_path):
            print(f"✗ Error: Folder not found: {folder_path}")
            return

        # Supported image formats
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp'}

        # Get all image files
        image_files = []
        for ext in image_extensions:
            image_files.extend(Path(folder_path).rglob(f"*{ext}"))
            image_files.extend(Path(folder_path).rglob(f"*{ext.upper()}"))

        print(f"Found {len(image_files)} images to process\n")

        results = []

        for image_file in image_files:
            print(f"Processing: {image_file.name}...", end=" ")

            try:
                result = self.identify_person(str(image_file), tolerance)

                if result:
                    person_name = result["person_name"]
                    print(f"✓ {person_name}")

                    # Create person folder
                    person_folder = Path(folder_path) / person_name
                    person_folder.mkdir(exist_ok=True)

                    # Copy image
                    import shutil
                    shutil.copy2(image_file, person_folder / image_file.name)

                    results.append({
                        "image": image_file.name,
                        "person": person_name,
                        "confidence": result["confidence"]
                    })
                else:
                    print("✗ Unknown")

                    # Create Unknown folder
                    unknown_folder = Path(folder_path) / "Unknown"
                    unknown_folder.mkdir(exist_ok=True)

                    # Copy image
                    import shutil
                    shutil.copy2(image_file, unknown_folder / image_file.name)

            except Exception as e:
                print(f"✗ Error: {e}")

        # Save results
        results_file = Path(folder_path) / "organization_results.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)

        print(f"\n{'='*50}")
        print("ORGANIZATION COMPLETE")
        print(f"{'='*50}")
        print(f"  Total images: {len(image_files)}")
        print(f"  Identified: {len(results)}")
        print(f"  Unknown: {len(image_files) - len(results)}")
        print(f"  Results saved: {results_file}")
        print(f"{'='*50}\n")

    def list_enrolled_persons(self):
        """List all enrolled persons"""
        print(f"\n{'='*50}")
        print("ENROLLED PERSONS")
        print(f"{'='*50}\n")

        if len(self.encodings_db["names"]) == 0:
            print("No persons enrolled yet.")
        else:
            for idx, (name, metadata) in enumerate(zip(
                self.encodings_db["names"],
                self.encodings_db["metadata"]
            ), 1):
                print(f"{idx}. {name}")
                print(f"   Enrolled: {metadata['enrollment_date']}")
                print(f"   Image: {metadata['image_path']}")
                print()

        print(f"Total: {len(self.encodings_db['names'])} person(s)")
        print(f"{'='*50}\n")

    def delete_person(self, person_name: str) -> bool:
        """
        Delete a person from the database

        Args:
            person_name: Name of person to delete

        Returns:
            bool: True if successful
        """
        indices_to_remove = [
            i for i, name in enumerate(self.encodings_db["names"])
            if name == person_name
        ]

        if not indices_to_remove:
            print(f"✗ Person not found: {person_name}")
            return False

        # Remove all entries for this person (in reverse to maintain indices)
        for idx in sorted(indices_to_remove, reverse=True):
            del self.encodings_db["encodings"][idx]
            del self.encodings_db["names"][idx]
            del self.encodings_db["metadata"][idx]

        self._save_database()
        # Honour the data-subject's right to erasure: drop consent + record it.
        self.consent.revoke(person_name)
        self.audit.append("delete", person_name=person_name, faces=len(indices_to_remove))

        print(f"✓ Deleted {len(indices_to_remove)} face(s) for {person_name}")
        return True

    def purge_expired(self, retention_days: Optional[int] = None) -> int:
        """Drop enrollments older than the retention window (data-minimization)."""
        days = self.retention.ttl_days if retention_days is None else retention_days
        policy = sec.RetentionPolicy(days)
        meta = self.encodings_db["metadata"]
        keep_idx = [
            i for i, m in enumerate(meta)
            if not policy.is_expired(m.get("enrollment_date", ""))
        ]
        removed = len(meta) - len(keep_idx)
        if removed:
            self.encodings_db = {
                "encodings": [self.encodings_db["encodings"][i] for i in keep_idx],
                "names": [self.encodings_db["names"][i] for i in keep_idx],
                "metadata": [meta[i] for i in keep_idx],
            }
            self._save_database()
            self.audit.append("purge_expired", removed=removed, ttl_days=days)
        print(f"✓ Purge complete: removed {removed} expired record(s) (ttl_days={days}).")
        return removed

    def migrate_legacy(self, source_path: str) -> bool:
        """One-time import of a legacy plaintext pickle DB into the encrypted vault."""
        import pickle  # local import: legacy migration path only
        if not os.path.exists(source_path):
            print(f"✗ Legacy database not found: {source_path}")
            return False
        # The source is the operator's own local file; migration is explicit.
        with open(source_path, "rb") as f:
            legacy = pickle.load(f)
        self.encodings_db = {
            "encodings": [np.asarray(e) for e in legacy.get("encodings", [])],
            "names": list(legacy.get("names", [])),
            "metadata": list(legacy.get("metadata", [])),
        }
        self._save_database()
        self.audit.append("migrate_legacy", source=os.path.basename(source_path),
                          count=len(self.encodings_db["names"]))
        print(f"✓ Migrated {len(self.encodings_db['names'])} record(s) into the encrypted vault.")
        return True


def main():
    parser = argparse.ArgumentParser(
        description="Local Facial Recognition System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Enroll a person
  python FaceRecognition-Local.py enroll --image john.jpg --name "John Doe"

  # Identify person from photo
  python FaceRecognition-Local.py identify --image unknown.jpg

  # Authenticate specific person (with anti-spoofing enforced)
  python FaceRecognition-Local.py authenticate --image webcam.jpg --name "John Doe" \\
      --require-liveness --liveness-score 0.93

  # Organize photos by person
  python FaceRecognition-Local.py organize --folder ./Photos

  # List enrolled persons
  python FaceRecognition-Local.py list

  # Purge enrollments older than 365 days
  python FaceRecognition-Local.py purge --retention-days 365

  # Migrate a legacy plaintext database into the encrypted vault
  python FaceRecognition-Local.py migrate --source face_database_local.pkl
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Enroll command
    enroll_parser = subparsers.add_parser('enroll', help='Enroll a new person')
    enroll_parser.add_argument('--image', required=True, help='Path to image file')
    enroll_parser.add_argument('--name', required=True, help='Person name')
    enroll_parser.add_argument('--no-consent', action='store_true',
                               help='Skip consent (requires OPAL_ALLOW_NO_CONSENT=1; testing only)')

    # Identify command
    identify_parser = subparsers.add_parser('identify', help='Identify person from image')
    identify_parser.add_argument('--image', required=True, help='Path to image file')
    identify_parser.add_argument('--tolerance', type=float, default=0.6,
                                 help='Recognition tolerance (default: 0.6)')

    # Authenticate command
    auth_parser = subparsers.add_parser('authenticate', help='Authenticate specific person')
    auth_parser.add_argument('--image', required=True, help='Path to image file')
    auth_parser.add_argument('--name', required=True, help='Expected person name')
    auth_parser.add_argument('--tolerance', type=float, default=0.6, help='Recognition tolerance')
    auth_parser.add_argument('--require-liveness', action='store_true',
                             help='Fail authentication if liveness is not satisfied')
    auth_parser.add_argument('--liveness-score', type=float, default=None,
                             help='Anti-spoofing score in [0,1] from a liveness detector')

    # Organize command
    organize_parser = subparsers.add_parser('organize', help='Organize photos by person')
    organize_parser.add_argument('--folder', required=True, help='Path to folder with photos')
    organize_parser.add_argument('--tolerance', type=float, default=0.6,
                                 help='Recognition tolerance')

    # List command
    subparsers.add_parser('list', help='List enrolled persons')

    # Delete command
    delete_parser = subparsers.add_parser('delete', help='Delete person from database')
    delete_parser.add_argument('--name', required=True, help='Person name to delete')

    # Purge command (retention / data-minimization)
    purge_parser = subparsers.add_parser('purge', help='Purge enrollments older than the window')
    purge_parser.add_argument('--retention-days', type=int, required=True,
                              help='Maximum age in days; older enrollments are deleted')

    # Migrate command (legacy plaintext pickle -> encrypted vault)
    migrate_parser = subparsers.add_parser('migrate', help='Import a legacy pickle DB into the vault')
    migrate_parser.add_argument('--source', required=True, help='Path to legacy .pkl database')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Initialize system
    fr = FaceRecognitionLocal()

    # Execute command
    if args.command == 'enroll':
        success = fr.enroll_person(
            args.image,
            args.name,
            require_consent=not args.no_consent
        )
        sys.exit(0 if success else 1)

    elif args.command == 'identify':
        result = fr.identify_person(args.image, args.tolerance)
        sys.exit(0 if result else 1)

    elif args.command == 'authenticate':
        success = fr.authenticate_person(
            args.image, args.name, args.tolerance,
            liveness_score=args.liveness_score,
            require_liveness=args.require_liveness,
        )
        sys.exit(0 if success else 1)

    elif args.command == 'organize':
        fr.organize_photos(args.folder, args.tolerance)

    elif args.command == 'list':
        fr.list_enrolled_persons()

    elif args.command == 'delete':
        success = fr.delete_person(args.name)
        sys.exit(0 if success else 1)

    elif args.command == 'purge':
        fr.purge_expired(args.retention_days)

    elif args.command == 'migrate':
        success = fr.migrate_legacy(args.source)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
