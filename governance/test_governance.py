# governance/test_governance.py
import hashlib
import sys

# === COPY THE CORE FUNCTIONS (no Kafka dependency needed) ===
PII_FIELDS = ["license_plates"]


def hash_pii(value):
    if isinstance(value, list):
        return [hashlib.sha256(v.encode()).hexdigest()[:12] for v in value]
    return hashlib.sha256(str(value).encode()).hexdigest()[:12]


def govern(record):
    clean = record.copy()
    pii_found = False
    for field in PII_FIELDS:
        if field in clean and clean[field]:
            clean[field] = hash_pii(clean[field])
            pii_found = True
    clean["pii_detected"] = pii_found
    return clean, pii_found


# === TESTS ===


class TestPIIDetection:
    """Tests for PII detection logic"""

    def test_detects_license_plates_as_pii(self):
        record = {
            "sensor_id": "CAM-101",
            "district": "Sector-1",
            "vehicle_count": 45,
            "license_plates": ["AB-1234-CD", "EF-5678-GH"],
        }
        _, had_pii = govern(record)
        assert had_pii is True

    def test_marks_pii_detected_true(self):
        record = {"sensor_id": "CAM-101", "license_plates": ["AB-1234-CD"]}
        governed, _ = govern(record)
        assert governed["pii_detected"] is True

    def test_no_pii_in_pollution_data(self):
        record = {
            "sensor_id": "AQ-101",
            "district": "Sector-1",
            "aqi": 150,
            "pm25": 65.3,
            "co2_ppm": 420.5,
        }
        governed, had_pii = govern(record)
        assert had_pii is False
        assert governed["pii_detected"] is False

    def test_empty_plates_list_no_pii(self):
        record = {"sensor_id": "CAM-101", "license_plates": []}
        _, had_pii = govern(record)
        assert had_pii is False

    def test_missing_plates_field_no_pii(self):
        record = {"sensor_id": "CAM-101", "district": "Sector-2", "vehicle_count": 30}
        _, had_pii = govern(record)
        assert had_pii is False


class TestHashing:
    """Tests for SHA-256 hashing mechanism"""

    def test_plates_are_hashed_not_original(self):
        record = {"license_plates": ["AB-1234-CD"]}
        governed, _ = govern(record)
        assert governed["license_plates"][0] != "AB-1234-CD"

    def test_hash_length_is_12(self):
        result = hash_pii("AB-1234-CD")
        assert len(result) == 12

    def test_hash_is_deterministic(self):
        hash1 = hash_pii("AB-1234-CD")
        hash2 = hash_pii("AB-1234-CD")
        assert hash1 == hash2

    def test_different_inputs_different_hashes(self):
        hash1 = hash_pii("AB-1234-CD")
        hash2 = hash_pii("XY-9999-ZZ")
        assert hash1 != hash2

    def test_list_hashing(self):
        plates = ["AB-1234-CD", "EF-5678-GH", "IJ-9012-KL"]
        hashed = hash_pii(plates)
        assert len(hashed) == 3
        assert all(len(h) == 12 for h in hashed)
        assert len(set(hashed)) == 3  # all unique

    def test_hash_matches_manual_sha256(self):
        plate = "AB-1234-CD"
        expected = hashlib.sha256(plate.encode()).hexdigest()[:12]
        result = hash_pii(plate)
        assert result == expected


class TestDataIntegrity:
    """Tests ensuring governance doesn't corrupt data"""

    def test_original_record_unchanged(self):
        record = {
            "sensor_id": "CAM-101",
            "district": "Sector-1",
            "vehicle_count": 45,
            "license_plates": ["AB-1234-CD"],
        }
        original_plate = record["license_plates"][0]
        govern(record)
        assert record["license_plates"][0] == original_plate

    def test_non_pii_fields_preserved(self):
        record = {
            "sensor_id": "CAM-101",
            "district": "Sector-3",
            "vehicle_count": 67,
            "avg_speed_kmh": 42.5,
            "license_plates": ["AB-1234-CD"],
        }
        governed, _ = govern(record)
        assert governed["sensor_id"] == "CAM-101"
        assert governed["district"] == "Sector-3"
        assert governed["vehicle_count"] == 67
        assert governed["avg_speed_kmh"] == 42.5

    def test_governed_record_has_pii_detected_field(self):
        record = {"sensor_id": "CAM-101", "license_plates": ["AB-1234-CD"]}
        governed, _ = govern(record)
        assert "pii_detected" in governed

    def test_multiple_plates_all_hashed(self):
        record = {"license_plates": ["AB-1234-CD", "EF-5678-GH", "IJ-9012-KL"]}
        governed, _ = govern(record)
        for plate in governed["license_plates"]:
            assert len(plate) == 12
            assert "-" not in plate  # hashes dont have dashes

    def test_governed_is_separate_object(self):
        record = {"sensor_id": "CAM-101", "license_plates": ["AB-1234-CD"]}
        governed, _ = govern(record)
        governed["sensor_id"] = "MODIFIED"
        assert record["sensor_id"] == "CAM-101"


class TestEdgeCases:
    """Edge case handling"""

    def test_single_plate(self):
        record = {"license_plates": ["AB-1234-CD"]}
        governed, had_pii = govern(record)
        assert had_pii is True
        assert len(governed["license_plates"]) == 1

    def test_many_plates(self):
        plates = [f"PLATE-{i}" for i in range(50)]
        record = {"license_plates": plates}
        governed, _ = govern(record)
        assert len(governed["license_plates"]) == 50

    def test_empty_record(self):
        record = {}
        governed, had_pii = govern(record)
        assert had_pii is False
        assert governed["pii_detected"] is False

    def test_record_with_extra_fields(self):
        record = {
            "sensor_id": "CAM-101",
            "license_plates": ["AB-1234-CD"],
            "weather": "sunny",
            "custom_field": 12345,
        }
        governed, _ = govern(record)
        assert governed["weather"] == "sunny"
        assert governed["custom_field"] == 12345


# === RUN WITHOUT PYTEST ===
if __name__ == "__main__":
    test_classes = [TestPIIDetection, TestHashing, TestDataIntegrity, TestEdgeCases]

    total = 0
    passed = 0
    failed = 0

    for cls in test_classes:
        print(f"\n{'=' * 60}")
        print(f"  {cls.__name__}: {cls.__doc__}")
        print(f"{'=' * 60}")

        instance = cls()
        methods = [m for m in dir(instance) if m.startswith("test_")]

        for method_name in methods:
            total += 1
            try:
                getattr(instance, method_name)()
                passed += 1
                print(f"  PASS  {method_name}")
            except AssertionError as e:
                failed += 1
                print(f"  FAIL  {method_name}: {e}")
            except Exception as e:
                failed += 1
                print(f"  ERROR {method_name}: {e}")

    print(f"\n{'=' * 60}")
    print(f"  RESULTS: {passed}/{total} passed, {failed} failed")
    print(f"{'=' * 60}")

    if failed == 0:
        print("\n  ALL TESTS PASSED\n")

    sys.exit(failed)
