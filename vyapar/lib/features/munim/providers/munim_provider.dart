import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:vyapar/app/providers.dart';
import 'package:vyapar/features/munim/data/munim_repository.dart';

final munimRepositoryProvider = Provider<MunimRepository>(
  (ref) => MunimRepository(ref.watch(dioProvider)),
);

class MunimChatState {
  const MunimChatState({
    this.messages = const [],
    this.isLoading = false,
    this.error,
  });

  final List<MunimChatMessage> messages;
  final bool isLoading;
  final Object? error;

  MunimChatState copyWith({
    List<MunimChatMessage>? messages,
    bool? isLoading,
    Object? error,
  }) => MunimChatState(
    messages: messages ?? this.messages,
    isLoading: isLoading ?? this.isLoading,
    error: error,
  );
}

class MunimChatController extends Notifier<MunimChatState> {
  @override
  MunimChatState build() => const MunimChatState(
    messages: [
      MunimChatMessage(
        role: 'assistant',
        content:
            'Namaste! Main aapka AI Munim hoon. Dukaan ka stock, aaj ki bikri, bank settlement ya suppliers ke baare mein kuch bhi poochiye.',
      ),
    ],
  );

  Future<void> send(String userText) async {
    if (userText.trim().isEmpty) return;
    final userMsg = MunimChatMessage(
      role: 'user',
      content: userText.trim(),
      timestamp: DateTime.now(),
    );
    final updatedList = [...state.messages, userMsg];
    state = state.copyWith(messages: updatedList, isLoading: true, error: null);

    try {
      final reply = await ref.read(munimRepositoryProvider).sendMessage(
        message: userMsg.content,
        history: updatedList,
      );
      final assistantMsg = MunimChatMessage(
        role: 'assistant',
        content: reply,
        timestamp: DateTime.now(),
      );
      state = state.copyWith(
        messages: [...updatedList, assistantMsg],
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e);
    }
  }

  void clear() {
    state = build();
  }
}

final munimChatProvider =
    NotifierProvider<MunimChatController, MunimChatState>(
      MunimChatController.new,
    );
