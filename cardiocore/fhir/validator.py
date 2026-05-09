# OWNER: Binula
# DAY:   3
# PURPOSE: Structural validation for FHIR bundles before returning to Prompt Opinion
#
# Does NOT use an external FHIR validator â€” just checks required fields.
#
# Expected interface:
#
#   from fhir.validator import validate_bundle
#
#   is_valid, errors = validate_bundle(bundle_dict)
#   # is_valid: True if bundle passes all checks
#   # errors: list of error strings if invalid

def validate_bundle(bundle: dict) -> tuple:
    errors = []
    if bundle.get('resourceType') != 'Bundle':
        errors.append('resourceType must be Bundle')
    entries = bundle.get('entry', [])
    if not entries:
        errors.append('entry must be non-empty')
    types = [e.get('resource',{}).get('resourceType') for e in entries]
    if 'DiagnosticReport' not in types:
        errors.append('Bundle must contain a DiagnosticReport')
    for e in entries:
        r = e.get('resource',{})
        if r.get('resourceType')=='DiagnosticReport':
            if not r.get('conclusion') or len(r['conclusion'])<20:
                errors.append('DiagnosticReport.conclusion too short')
    return len(errors)==0, errors


