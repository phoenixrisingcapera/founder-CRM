from __future__ import annotations

from app.services.upload_readiness_service import get_upload_persistence_readiness

EXPECTED_CHECKS = {
    "databaseUrl",
    "authSecretKey",
    "authSecretKeyId",
    "workspaceAiFernetKey",
    "workspaceAiFernetKeyVersion",
    "corsOrigin",
    "uploadSecurityScanCommand",
    "storageBackend",
    "s3Bucket",
    "s3Endpoint",
    "s3Region",
    "s3AccessKey",
    "s3SecretKey",
}


def main() -> int:
    readiness = get_upload_persistence_readiness()
    checks = readiness.get("checks", {})
    missing_contract_keys = sorted(EXPECTED_CHECKS - set(checks))

    if readiness.get("failureCategory") != "deck_upload_save":
        print("Upload readiness contract checks FAILED:")
        print(f"- Expected failureCategory deck_upload_save, got {readiness.get('failureCategory')!r}")
        return 1

    if missing_contract_keys:
        print("Upload readiness contract checks FAILED:")
        print(f"- Missing readiness keys: {missing_contract_keys}")
        return 1

    print("Upload readiness contract checks PASSED")
    print(f"Failure category: {readiness.get('failureCategory')}")
    print(f"Status: {readiness.get('status')}")
    print(f"Storage backend: {readiness.get('storageBackend')}")
    print(f"Missing required checks: {readiness.get('missingRequiredChecks')}")
    print(f"Warning checks: {readiness.get('warningChecks')}")
    print("Accepted variable groups:")
    for key in sorted(EXPECTED_CHECKS):
        env_names = checks[key].get("envNames", [])
        ok = checks[key].get("ok")
        required = checks[key].get("required")
        print(f"- {key}: ok={ok} required={required} env={','.join(env_names)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
