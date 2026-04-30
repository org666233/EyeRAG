import 'dart:async';
import 'package:flutter/material.dart';
import '../../core/constants/app_constants.dart';
import 'markdown_view.dart';

class TypingAnimation extends StatefulWidget {
  final String text;
  final VoidCallback? onComplete;

  const TypingAnimation({super.key, required this.text, this.onComplete});

  @override
  State<TypingAnimation> createState() => _TypingAnimationState();
}

class _TypingAnimationState extends State<TypingAnimation> {
  String _displayed = '';
  int _index = 0;
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _startTyping();
  }

  void _startTyping() {
    _timer = Timer.periodic(
      Duration(milliseconds: AppConstants.typingSpeedMs),
      (timer) {
        if (_index >= widget.text.length) {
          timer.cancel();
          widget.onComplete?.call();
          return;
        }
        setState(() {
          _displayed += widget.text[_index];
          _index++;
        });
      },
    );
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return MarkdownView(data: _displayed.isEmpty ? '…' : _displayed);
  }
}
