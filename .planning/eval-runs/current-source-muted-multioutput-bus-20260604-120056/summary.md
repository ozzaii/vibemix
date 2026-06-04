# Current-source muted multi-output bus proof

Current source launched muted with `VIBEMIX_LOCAL_TTS=0`, `VIBEMIX_ENABLE_MIC=0`, and `VIBEMIX_INPUT_DEVICE=BlackHole 2ch`. Console observed `listening to BlackHole 2ch @ 48000Hz (2ch) -> audio_buf + clean_audio_buf`, FLX4 MIDI connected, music RMS around `0.018-0.034`, and voice RMS `0.000`. Result: engine hears Rekordbox Multi-Output through BlackHole 2ch while voice output remains muted.
