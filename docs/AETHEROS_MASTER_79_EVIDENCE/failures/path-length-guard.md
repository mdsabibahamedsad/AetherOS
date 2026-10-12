# check-packaging-path-lengths output (host, 2026-09-15) — W79-028 related

Command: `node scripts/release/check-packaging-path-lengths.mjs` in apps/desktop.

Result: FAIL — 6 path(s) exceed MAX_SAFE_LENGTH=240. Offenders (absolute,
checkout-rooted at D:\hermes-agent-main\aetheros):

- ...\win-unpacked\resources\py\Lib\site-packages\elevenlabs\text_to_speech\types\body_text_to_speech_streaming_with_timestamps_v_1_text_to_speech_voice_id_stream_with_timestamps_post_apply_text_normalization.py (262)
- ...\elevenlabs\pronunciation_dictionary\types\body_add_a_pronunciation_dictionary_v_1_pronunciation_dictionaries_add_from_rules_post_workspace_access.py (249)
- ...\build\bundled-python\py\Lib\site-packages\elevenlabs\text_to_speech\types\body_..._post_apply_text_normalization.py (246)
- ...\elevenlabs\text_to_speech\types\body_text_to_speech_with_timestamps_v_1_text_to_speech_voice_id_with_timestamps_post_apply_text_normalization.py (245)
- ...\elevenlabs\pronunciation_dictionary\types\body_add_a_pronunciation_dictionary_v_1_pronunciation_dictionaries_add_from_rules_post_rules_item.py (243)
- ...\mistralai\client\models\get_chat_completion_field_options_counts_v1_observability_chat_completion_fields_field_name_options_counts_postop.py (241)

Interpretation: guard measures ABSOLUTE paths including the long checkout
prefix (D:\hermes-agent-main\aetheros\apps\desktop\...), so part of the
excess is buildCheckoutorigin, not installer payload layout. The MSI DID
build successfully (Master 78A: MSI BUILD PASS, LGHT0103 RESOLVED), so
WiX staging handled these names. Runtime risk on short target paths
(C:\Program Files\AetherOS) is lower but UNVERIFIED without a clean-VM
launch importing elevenlabs/mistralai from the bundled interpreter.
Recorded as P1 long-path regression follow-up, not a build blocker.
