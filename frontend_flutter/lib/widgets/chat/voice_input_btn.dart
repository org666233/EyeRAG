import 'package:flutter/material.dart';
import 'package:speech_to_text/speech_to_text.dart';

class VoiceInputButton extends StatefulWidget {
  final ValueChanged<String> onResult;

  const VoiceInputButton({super.key, required this.onResult});

  @override
  State<VoiceInputButton> createState() => _VoiceInputButtonState();
}

class _VoiceInputButtonState extends State<VoiceInputButton> {
  final SpeechToText _stt = SpeechToText();
  bool _available = false;
  bool _listening = false;

  @override
  void initState() {
    super.initState();
    _init();
  }

  Future<void> _init() async {
    _available = await _stt.initialize(
      onError: (_) => setState(() => _listening = false),
    );
    setState(() {});
  }

  Future<void> _startListening() async {
    if (!_available) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('当前设备不支持语音输入')),
      );
      return;
    }
    setState(() => _listening = true);
    await _stt.listen(
      localeId: 'zh_CN',
      onResult: (result) {
        if (result.finalResult) {
          widget.onResult(result.recognizedWords);
          setState(() => _listening = false);
        }
      },
    );
  }

  Future<void> _stopListening() async {
    await _stt.stop();
    setState(() => _listening = false);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return GestureDetector(
      onLongPressStart: (_) => _startListening(),
      onLongPressEnd: (_) => _stopListening(),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: _listening
              ? theme.colorScheme.errorContainer
              : theme.colorScheme.surfaceContainerHigh,
        ),
        child: Icon(
          _listening ? Icons.mic : Icons.mic_none,
          color: _listening
              ? theme.colorScheme.error
              : theme.colorScheme.onSurfaceVariant,
          size: 24,
        ),
      ),
    );
  }
}
