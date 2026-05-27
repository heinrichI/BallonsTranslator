# Implementation Plan

[Overview]
Add focused debugging and instrumentation to discover why ModuleManager.textdetector is None at pipeline runtime and produce actionable fixes; the plan limits changes to non-invasive logging + small guards, then runs targeted tests.

This change is needed because the imgtrans pipeline calls self.textdetector.detect(...) while self.textdetector is None, causing AttributeError. The goal is to (1) gather precise runtime data (registration state, module init failures, thread lifecycle), (2) produce a reproducible minimal fix (either guard/wait or ensure proper initialization), and (3) provide tests and developer-facing diagnostics so future regressions are obvious. The approach: add structured debug logs and exception captures in module registration and ModuleThread._set_module, add a short guard/report in ModuleManager before calling detect, and add smoke tests/scripts to reproduce and validate.

[Types]
Add no public API type system changes; internal diagnostic data structures: a short dataclass-like dict format for module init diagnostics.

Define "ModuleInitReport" (dict):
- module_key: str (one of 'textdetector','ocr','translator','inpainter')
- requested_name: str | None (the name requested from config)
- resolved_class: str | None (module class name found in registry.module_dict)
- params: dict (the params dict passed to module constructor — redact secrets)
- success: bool
- exception: str | None (traceback string if failed)
- timestamp: ISO-8601 string

Validation rules:
- module_key must be one of allowed keys.
- params must be serializable (use repr for non-serializable).
- exception length capped to 10k chars.

[Files]
Single sentence: create implementation_plan.md (this file), add logging edits to modules/base.py and utils/registry.py, add debug guards and reporting to ui/module_manager.py, and add/update developer scripts.

Detailed breakdown:
- New files to be created
  - implementation_plan.md (root) — this plan (created).
  - scripts/diagnose_module_init.py — developer script to print registry contents and attempt to instantiate modules from config for quick reproduction.
- Existing files to be modified
  - modules/base.py
    - Add ModuleInitReport helper functions (serialize_params, make_report) near register_hooks/patch_module_params.
  - utils/registry.py
    - Add defensive logging in get() and expose a helper to list registered keys with scopes.
  - ui/module_manager.py
    - Add detailed logging in ModuleThread._set_module (log attempted module_name, registry keys, params, and any exception trace with ModuleInitReport emission).
    - Emit ModuleInitReport to logger and (optionally) save last reports to ModuleManager._last_init_reports dict.
    - Add lightweight guard in ImgtransThread._imgtrans_pipeline (or ModuleManager._imgtrans_pipeline) to detect None and raise a clearer Exception with diagnostic info instead of AttributeError.
    - Optionally add a retry/wait-for-finish mechanism before starting pipeline when load_model_on_demand is true (non-invasive; disabled by default).
  - launch.py (or application entry)
    - Add a startup debug log that dumps GET_VALID_TEXTDETECTORS(), GET_VALID_OCR(), GET_VALID_TRANSLATORS(), GET_VALID_INPAINTERS() so developer sees available registrations at startup.
  - scripts/debug_run_detector.py (existing)
    - Update to allow printing registry keys and running setTextDetector flow manually and display ModuleInitReport results.
- Files to be deleted or moved: none.
- Configuration file updates
  - None required. Consider adding a runtime flag in utils/shared (DEBUG_MODULE_INIT=True) to gate verbose instrumentation.

[Functions]
Single sentence: add diagnostic helpers and instrument ModuleThread._set_module and ModuleManager pipeline call sites.

Detailed breakdown:
- New functions
  - make_module_init_report(module_key: str, requested_name: str, params: dict, exc: Exception|None) -> dict
    - File: modules/base.py (near helper utilities)
    - Purpose: Build ModuleInitReport dict (see Types).
  - serialize_params_for_report(params: dict) -> dict
    - File: modules/base.py
    - Purpose: Safely convert params into JSON-serializable form (repr fallback).
  - dump_registry_state(registry_name: str) -> dict
    - File: utils/registry.py
    - Purpose: Return available keys and scopes for a registry.
  - scripts/diagnose_module_init.py: main() to run diagnostic flow.
- Modified functions
  - ModuleThread._set_module (exact: ui/module_manager.py, ModuleThread._set_module)
    - Add logging at start (module_key, requested module_name, registry.module_dict keys)
    - Wrap existing try/except to generate ModuleInitReport and log full traceback and registry state on exception, then re-raise or set module to old_module (current behavior) but retain diagnostic info.
    - Emit finish_set_module as before.
  - ModuleManager._imgtrans_pipeline or ImgtransThread._imgtrans_pipeline (ui/module_manager.py)
    - Before calling self.textdetector.detect(img,...), add an explicit check:
      - if self.textdetector is None: log error with diagnostic context (last ModuleInitReport if present), create_error_dialog with informative message "Text detector not initialized" and skip to next page rather than throw AttributeError.
    - Alternatively, if cfg_module.load_model_on_demand is False and textdetector is None — treat as fatal and present dialog with diagnostic info.
- Removed functions: none.

[Classes]
Single sentence: no new domain classes; small additions to record diagnostics stored on ModuleManager instance.

Detailed breakdown:
- New classes
  - None (use dict for ModuleInitReport).
- Modified classes
  - ModuleThread (ui/module_manager.py)
    - _set_module: instrument to capture ModuleInitReport and store it to self.module_init_report (attribute) and emit via logger.
  - ModuleManager (ui/module_manager.py)
    - Add attribute _last_init_reports: Dict[str, dict] to hold latest ModuleInitReport for each module_key; populate when finish_set_module signals arrive.
    - Update _imgtrans_pipeline error handling to consult _last_init_reports and present diagnostics in create_error_dialog call.
- Removed classes
  - None.

[Dependencies]
Single sentence: no runtime dependency changes; only developer-only scripts added.

Details:
- No new pip packages required.
- Use existing utils.logger; if structured logging desired later, add or upgrade python-json-logger (not part of this minimal plan).
- Ensure existing imports (traceback, datetime) are used; add them if missing.

[Testing]
Single sentence: add smoke diagnostic script and run existing debug_run_detector to validate module registration and initialization flows.

Test file requirements and modifications:
- scripts/diagnose_module_init.py (new)
  - Steps:
    - Import modules package and utils/registry and call dump_registry_state for TEXTDETECTORS, OCR.
    - Attempt to instantiate configured module names from pcfg.module (pcfg.module.textdetector etc.) using the ModuleThread._set_module logic (or by constructing the class directly with params).
    - Print ModuleInitReport JSON to stdout.
- Update scripts/debug_run_detector.py
  - Add a --dump-registry flag to print registry contents.
- Manual test procedure:
  1. Run launch.py with DEBUG logging enabled (or run scripts/diagnose_module_init.py) and capture output.
  2. Observe whether TEXTDETECTORS contains expected detectors (e.g., 'ctd' or 'stariver').
  3. If registry lacks the expected key, inspect modules/textdetector/ for registration decorators; if keys differ (e.g. 'ctd' vs 'ctd_detector'), adjust pcfg.module.textdetector or registration.
  4. Run the GUI pipeline in dev mode: with the added guard, the app should show a build-time dialog describing diagnostic info instead of crashing.
- Unit tests:
  - Not required for initial debug; add later if needed.

[Implementation Order]
Single sentence: implement diagnostics first (safe, reversible), run smoke diagnostics, then add minimal guard and retry behavior, and finally refine or implement permanent fix based on root cause.

Numbered steps:
1. Add helper functions in modules/base.py: serialize_params_for_report and make_module_init_report. (small, isolated)
2. Add dump_registry_state in utils/registry.py and log registry contents at startup (launch.py). (non-invasive)
3. Instrument ModuleThread._set_module (ui/module_manager.py) to create ModuleInitReport on both success and failure, logging full details and saving to self.module_init_report; ensure finish_set_module still emitted. (targeted)
4. Add storage in ModuleManager to collect per-module last init reports (self._last_init_reports) and hook finish_set_module signals in setupThread to populate them. (minimal)
5. Add guard in ImgtransThread._imgtrans_pipeline (ui/module_manager.py) before calling self.textdetector.detect: if None, call create_error_dialog with diagnostic summary and skip detection for that page; log and continue. (non-fatal)
6. Add scripts/diagnose_module_init.py that reproduces module instantiation attempts and prints ModuleInitReport for each module_key in pcfg.module. (developer-facing)
7. Run diagnose_module_init.py and/or start app in debug mode; inspect logs and reports to determine root cause (e.g., registry key mismatch, exception during module init due to missing model files or incorrect params).
8. Based on findings: either fix registration/name mismatch or add robust initialization (e.g., ensure default module exists in registry, or make ModuleThread fall back to default implementation). Implement final fix as a follow-up task.
9. Remove or gate verbose debug logs behind utils.shared.DEBUG_MODULE_INIT flag before merging.