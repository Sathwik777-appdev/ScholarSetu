import 'package:flutter/material.dart';
import '../theme/app_theme.dart';
import '../services/api_service.dart';
import '../models/models.dart';

class JAGOChatScreen extends StatefulWidget {
  const JAGOChatScreen({Key? key}) : super(key: key);

  @override
  State<JAGOChatScreen> createState() => _JAGOChatScreenState();
}

class _JAGOChatScreenState extends State<JAGOChatScreen> {
  final TextEditingController _ctrl = TextEditingController();
  final ScrollController _scrollCtrl = ScrollController();
  bool _isSending = false;
  bool _isRecordingVoice = false;
  String _selectedLanguage = "hi";

  final List<ChatMessage> _messages = [
    ChatMessage(
      text: "नमस्ते सुनीता! मैं जागो (JAGO) छात्रवृत्ति सहायक हूँ। मैं आपकी छात्रवृत्ति स्थिति, दस्तावेज़ों, पात्रता और भुगतान में सहायता कर सकता हूँ। आप बोलकर या लिखकर पूछ सकते हैं।",
      isUser: false,
      timestamp: DateTime.now().subtract(const Duration(minutes: 5)),
    )
  ];

  Future<void> _sendMessage(String text) async {
    if (text.trim().isEmpty) return;
    _ctrl.clear();

    setState(() {
      _messages.add(ChatMessage(text: text, isUser: true, timestamp: DateTime.now()));
      _isSending = true;
    });

    _scrollToBottom();

    final response = await ApiService.chatWithJAGO(text, _selectedLanguage);

    setState(() {
      _messages.add(ChatMessage(
        text: response,
        isUser: false,
        timestamp: DateTime.now(),
        toolCalls: ["get_payments(student_id)", "get_pending_actions(student_id)"],
      ));
      _isSending = false;
    });

    _scrollToBottom();
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollCtrl.hasClients) {
        _scrollCtrl.animateTo(
          _scrollCtrl.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Column(
        children: [
          // Header Banner
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            color: Colors.indigo.shade50,
            child: Row(
              children: [
                const Icon(Icons.psychology, color: AppTheme.primaryBlue, size: 22),
                const SizedBox(width: 8),
                const Expanded(
                  child: Text(
                    "JAGO AI: Tool-grounded, money-safe assistant. Amounts only from verified ledger.",
                    style: TextStyle(fontSize: 11.5, color: AppTheme.primaryBlue, fontWeight: FontWeight.w600),
                  ),
                ),
                DropdownButton<String>(
                  value: _selectedLanguage,
                  isDense: true,
                  underline: const SizedBox(),
                  items: const [
                    DropdownMenuItem(value: "hi", child: Text("हिंदी", style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold))),
                    DropdownMenuItem(value: "en", child: Text("English", style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold))),
                  ],
                  onChanged: (val) {
                    setState(() => _selectedLanguage = val!);
                  },
                )
              ],
            ),
          ),

          // Messages List
          Expanded(
            child: ListView.builder(
              controller: _scrollCtrl,
              padding: const EdgeInsets.all(12),
              itemCount: _messages.length,
              itemBuilder: (ctx, idx) {
                final msg = _messages[idx];
                final isUser = msg.isUser;
                return Align(
                  alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
                  child: Container(
                    margin: const EdgeInsets.symmetric(vertical: 6),
                    padding: const EdgeInsets.all(12),
                    constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.82),
                    decoration: BoxDecoration(
                      color: isUser ? AppTheme.primaryBlue : Colors.white,
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: isUser ? AppTheme.primaryBlue : Colors.grey.shade200),
                      boxShadow: [
                        BoxShadow(color: Colors.black.withOpacity(0.04), blurRadius: 4, offset: const Offset(0, 2)),
                      ],
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          msg.text,
                          style: TextStyle(
                            color: isUser ? Colors.white : Colors.black87,
                            fontSize: 13.5,
                            height: 1.35,
                          ),
                        ),
                        if (msg.toolCalls != null && msg.toolCalls!.isNotEmpty) ...[
                          const SizedBox(height: 8),
                          Container(
                            padding: const EdgeInsets.all(6),
                            decoration: BoxDecoration(
                              color: Colors.grey.shade100,
                              borderRadius: BorderRadius.circular(6),
                            ),
                            child: Row(
                              children: [
                                const Icon(Icons.build_circle_outlined, size: 12, color: AppTheme.tribalTeal),
                                const SizedBox(width: 4),
                                Expanded(
                                  child: Text(
                                    "Verified via: ${msg.toolCalls!.join(', ')}",
                                    style: const TextStyle(fontSize: 10, color: AppTheme.tribalTeal, fontWeight: FontWeight.bold),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ]
                      ],
                    ),
                  ),
                );
              },
            ),
          ),

          if (_isSending)
            const Padding(
              padding: EdgeInsets.all(8),
              child: Row(
                children: [
                  SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2)),
                  SizedBox(width: 8),
                  Text("JAGO verifying ledger records...", style: TextStyle(fontSize: 12, color: Colors.grey)),
                ],
              ),
            ),

          // Quick Prompt Chips (Scene 5)
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            child: Row(
              children: [
                ActionChip(
                  avatar: const Icon(Icons.record_voice_over, size: 16, color: AppTheme.primaryBlue),
                  label: const Text("Mera paisa kab aayega?", style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                  backgroundColor: Colors.blue.shade50,
                  onPressed: () => _sendMessage("Mera paisa kab aayega?"),
                ),
                const SizedBox(width: 8),
                ActionChip(
                  label: const Text("Status check", style: TextStyle(fontSize: 12)),
                  onPressed: () => _sendMessage("Application status check karein"),
                ),
                const SizedBox(width: 8),
                ActionChip(
                  label: const Text("Documents required", style: TextStyle(fontSize: 12)),
                  onPressed: () => _sendMessage("Post-Matric ke liye kya documents chahiye?"),
                ),
              ],
            ),
          ),

          // Input Bar + Push-to-Talk Voice button
          Container(
            padding: const EdgeInsets.fromLTRB(10, 6, 10, 10),
            color: Colors.white,
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _ctrl,
                    decoration: const InputDecoration(
                      hintText: "Type or use microphone...",
                      hintStyle: TextStyle(fontSize: 13),
                      border: OutlineInputBorder(borderRadius: BorderRadius.all(Radius.circular(24))),
                      contentPadding: EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                    ),
                    onSubmitted: _sendMessage,
                  ),
                ),
                const SizedBox(width: 6),
                // Push-to-talk Voice Button (Scene 5)
                GestureDetector(
                  onLongPressStart: (_) {
                    setState(() => _isRecordingVoice = true);
                  },
                  onLongPressEnd: (_) {
                    setState(() => _isRecordingVoice = false);
                    _sendMessage("Mera paisa kab aayega?");
                  },
                  child: CircleAvatar(
                    backgroundColor: _isRecordingVoice ? AppTheme.errorRed : AppTheme.accentSaffron,
                    child: Icon(_isRecordingVoice ? Icons.mic : Icons.mic_none, color: Colors.white),
                  ),
                ),
                const SizedBox(width: 4),
                IconButton(
                  icon: const Icon(Icons.send, color: AppTheme.primaryBlue),
                  onPressed: () => _sendMessage(_ctrl.text),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
